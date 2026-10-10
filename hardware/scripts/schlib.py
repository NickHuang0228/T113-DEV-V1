#!/usr/bin/env python3
"""KiCad 原理圖生成的共用積木。

為什麼要有這支：手畫 100 多支腳容易出錯（已經踩過六次命名坑），
而 .kicad_sch 是 S-expression，結構固定，用程式產生反而更可靠 ——
跟符號庫由 CSV 生成是同一個思路。

用法：由各頁的 gen_*_sheet.py 匯入，不直接執行。

⚠ 座標系：KiCad 原理圖的 Y 軸向下為正，單位 mm，格點 1.27mm（50mil）。
   所有座標都該落在 1.27 的倍數上，否則接點對不上。
"""
import io
import os
import re
import uuid as _uuid

GRID = 1.27


def uid():
    return str(_uuid.uuid4())


def snap(v):
    """吸附到 1.27mm 格點 —— 接點沒對齊格點是最常見的「看起來接了其實沒連」。"""
    return round(round(v / GRID) * GRID, 4)


def g(v):
    return f"{snap(v):g}"


def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


# ── 基本元素 ────────────────────────────────────────────

def wire(x1, y1, x2, y2):
    return f"""	(wire
		(pts
			(xy {g(x1)} {g(y1)}) (xy {g(x2)} {g(y2)})
		)
		(stroke
			(width 0)
			(type default)
		)
		(uuid "{uid()}")
	)
"""


def junction(x, y):
    return f"""	(junction
		(at {g(x)} {g(y)})
		(diameter 0)
		(color 0 0 0 0)
		(uuid "{uid()}")
	)
"""


def no_connect(x, y):
    """告訴 ERC「這支腳故意不接」—— 未使用的類比腳用這個，不是放測試點。"""
    return f"""	(no_connect
		(at {g(x)} {g(y)})
		(uuid "{uid()}")
	)
"""


def global_label(name, x, y, rot=0, shape="input", justify="right"):
    return f"""	(global_label "{esc(name)}"
		(shape {shape})
		(at {g(x)} {g(y)} {rot})
		(fields_autoplaced yes)
		(effects
			(font
				(size 1.27 1.27)
			)
			(justify {justify})
		)
		(uuid "{uid()}")
		(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
			(at {g(x)} {g(y)} 0)
			(hide yes)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
				(justify {justify})
			)
		)
	)
"""


def symbol(lib_id, ref, value, x, y, rot=0, footprint="", unit=1,
           sheet_path="", pins=("1", "2"), desc="", dnp=False,
           ref_dy=-7.62, val_dy=-5.08):
    """放一個元件實例。

    sheet_path 是該圖紙在階層中的 UUID 路徑，必須與目標 .kicad_sch 一致，
    否則 KiCad 會認為這個元件不屬於這張圖，reference 會變成 "?"。
    """
    pin_blk = "".join(f"""		(pin "{p}"
			(uuid "{uid()}")
		)
""" for p in pins)
    return f"""	(symbol
		(lib_id "{esc(lib_id)}")
		(at {g(x)} {g(y)} {rot})
		(unit {unit})
		(body_style 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(in_pos_files yes)
		(dnp {'yes' if dnp else 'no'})
		(fields_autoplaced yes)
		(uuid "{uid()}")
		(property "Reference" "{esc(ref)}"
			(at {g(x)} {g(y + ref_dy)} 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Value" "{esc(value)}"
			(at {g(x)} {g(y + val_dy)} 0)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Footprint" "{esc(footprint)}"
			(at {g(x)} {g(y)} 0)
			(hide yes)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Datasheet" ""
			(at {g(x)} {g(y)} 0)
			(hide yes)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
		(property "Description" "{esc(desc)}"
			(at {g(x)} {g(y)} 0)
			(hide yes)
			(show_name no)
			(do_not_autoplace no)
			(effects
				(font
					(size 1.27 1.27)
				)
			)
		)
{pin_blk}		(instances
			(project "T113-DEV-V1"
				(path "{sheet_path}"
					(reference "{esc(ref)}")
					(unit {unit})
				)
			)
		)
	)
"""


def power(kind, x, y, rot=0, sheet_path="", net=None):
    """電源符號。kind 例如 "GND"、"+3V3"、"Earth"。

    ⚠ 它的 Value 就是 net 名稱 —— 這是電源軌命名的唯一來源，
    寫錯就變成另一條 net（已踩過四次：+3.3V / +1V8_SoC / +5V / MDI0）。

    net 用來讓「符號長相」與「net 名稱」分開，例如機殼地要畫接地符號
    （power:Earth）但 net 要叫 GND_CHASSIS：power("Earth", ..., net="GND_CHASSIS")。
    所有電源符號的接點都在 (0,0)，所以 x/y 直接給連接點座標。
    """
    return symbol(f"power:{kind}", "#PWR", net or kind, x, y, rot,
                  footprint="", sheet_path=sheet_path, pins=("1",),
                  desc="Power symbol", ref_dy=-3.81, val_dy=3.81)


# ── 檔案層級 ────────────────────────────────────────────

TOP_SCH = "T113-DEV-V1.kicad_sch"


def sheet_uuid_of(path):
    """取出子頁在階層中的 instances 路徑 = /<根圖紙 uuid>/<該 sheet 的 uuid>。

    從「根圖紙」查，不從子頁自己的內容猜 —— 剛建立的空白子頁裡
    根本沒有這個資訊，猜錯的後果是這頁所有元件的 reference 變成 "?"。
    """
    d = os.path.dirname(os.path.abspath(path))
    base = os.path.basename(path)
    top = os.path.join(d, TOP_SCH)
    s = io.open(top, encoding="utf-8").read()
    root_uuid = re.search(r'\(uuid "([0-9a-f-]+)"\)', s).group(1)
    for m in re.finditer(r'\n\t\(sheet\n([\s\S]*?)\n\t\)', s):
        blk = m.group(1)
        f = re.search(r'\(property "Sheetfile" "([^"]*)"', blk)
        u = re.search(r'\(uuid "([0-9a-f-]+)"\)', blk)
        if f and u and f.group(1) == base:
            want = f"/{root_uuid}/{u.group(1)}"
            # 子頁已有元件的話，順手確認路徑一致（對不上就是階層壞了）
            cur = io.open(path, encoding="utf-8").read()
            got = re.search(r'\(path "(/[0-9a-f-]+/[0-9a-f-]+)"', cur)
            if got and got.group(1) != want:
                raise SystemExit(
                    f"✗ {base} 既有元件的 instances 路徑 {got.group(1)} "
                    f"與根圖紙的 {want} 不符 —— 階層壞了，先修再生成。")
            return want
    raise SystemExit(f"✗ {base} 沒有掛在 {TOP_SCH} 的階層上 —— 先跑 new_sheet.py")


def append_to_sheet(path, blocks):
    """把生成好的元素插進既有 .kicad_sch 的結尾（最後一個 ')' 之前）。

    不碰既有內容 —— 這是刻意的：手畫的部分不該被程式改寫。
    """
    s = io.open(path, encoding="utf-8").read()
    end = s.rstrip().rfind(")")
    out = s[:end] + "".join(blocks) + s[end:]
    io.open(path, "w", encoding="utf-8", newline="\n").write(out)


def guard_kicad_closed(root):
    """KiCad 開著時絕不寫檔 —— 它存檔會整頁覆蓋，把生成結果洗掉（012 §6.2）。"""
    import glob
    import sys
    lck = glob.glob(os.path.join(root, "*.lck"))
    if lck:
        sys.exit(f"✗ KiCad 開著（{[os.path.basename(x) for x in lck]}）—— "
                 f"中止，不碰檔案。關閉後再跑。")


# ── 一張子圖紙的生成器 ──────────────────────────────────
#
# 下面這些方法是五張子頁重複在做的同一件事：
# 「從某支腳拉一小段線，接到標籤 / 電源 / 電阻」。
# 寫成方法而不是每頁各抄一份，是因為偏移量算錯就是接不上，
# 而這種錯在原理圖上看不出來（線頭差 0.01mm 也是斷的）。

R_FP = "Resistor_SMD:R_0603_1608Metric"
C_FP = "Capacitor_SMD:C_0603_1608Metric"


class Page:
    def __init__(self, path, project_root=None):
        guard_kicad_closed(project_root or os.path.dirname(os.path.abspath(path)))
        if not os.path.exists(path):
            raise SystemExit(f"✗ {os.path.basename(path)} 不存在 —— 先跑 new_sheet.py")
        self.path = path
        self.sheet = sheet_uuid_of(path)
        self.out = []
        self.stat = {}

    # —— 低階 ——
    def add(self, *blocks):
        self.out.extend(blocks)

    def w(self, x1, y1, x2, y2):
        self.out.append(wire(x1, y1, x2, y2))

    def j(self, x, y):
        self.out.append(junction(x, y))

    def nc(self, x, y):
        self.out.append(no_connect(x, y))

    def lab(self, name, x, y, left=False):
        """全域標籤。left=True 代表文字往左長（接在線段的左端）。"""
        self.out.append(global_label(name, x, y, 180 if left else 0,
                                     justify="right" if left else "left"))

    def rail(self, kind, x, y, net=None):
        self.out.append(power(kind, x, y, 0, self.sheet, net))

    def part(self, lib_id, ref, value, x, y, rot=0, fp="", unit=1,
             pins=("1", "2"), desc="", ref_dy=-7.62, val_dy=-5.08):
        self.out.append(symbol(lib_id, ref, value, x, y, rot, fp, unit,
                               self.sheet, pins, desc, False, ref_dy, val_dy))

    def res(self, ref, value, x, y, rot=90):
        """電阻。rot=90 為水平（接點在 x∓3.81），rot=0 為垂直（y∓3.81）。"""
        self.part("Device:R", ref, value, x, y, rot, R_FP,
                  desc="Resistor", ref_dy=-3.81, val_dy=3.81)

    def cap(self, ref, value, x, y, rot=0, fp=None):
        self.part("Device:C", ref, value, x, y, rot, fp or C_FP,
                  desc="Unpolarized capacitor", ref_dy=-3.81, val_dy=3.81)

    # —— 從腳位出發 ——
    def pin_label(self, x, y, side, name, stub=7.62):
        dx = -stub if side == "L" else stub
        self.w(x, y, x + dx, y)
        self.lab(name, x + dx, y, left=(side == "L"))

    def pin_rail(self, x, y, side, kind, stub=6.35, net=None):
        dx = -stub if side == "L" else stub
        self.w(x, y, x + dx, y)
        self.rail(kind, x + dx, y, net)

    def pin_res_rail(self, x, y, side, ref, value, kind, stub=7.62):
        """腳 →（水平電阻）→ 電源。RSET、strap 都是這個形狀。"""
        s = -1 if side == "L" else 1
        a = x + s * stub
        self.w(x, y, a, y)
        self.res(ref, value, a + s * 3.81, y, 90)
        self.w(a + s * 7.62, y, a + s * 12.7, y)
        self.rail(kind, a + s * 12.7, y)

    def pin_res_rail_v(self, x, y, side, ref, value, kind, stub=7.62, up=True):
        """腳 →（往上/下的垂直電阻）→ 電源。給右側腳用，避免跟相鄰腳的標籤撞在一起。"""
        s = -1 if side == "L" else 1
        a = x + s * stub
        d = -1 if up else 1
        self.w(x, y, a, y)
        self.w(a, y, a, y + d * 3.81)
        self.res(ref, value, a, y + d * 7.62, 0)
        self.w(a, y + d * 11.43, a, y + d * 13.97)
        self.rail(kind, a, y + d * 13.97)

    # —— 叢集 ——
    def strap_bank(self, x, y, rows, pitch=15.24):
        """一疊「全域標籤 →（電阻）→ 電源」。

        把掛在「已命名訊號」上的上下拉電阻集中畫，而不是硬塞在腳位旁邊 ——
        腳位旁邊的垂直走線會跟相鄰腳的標籤互相穿越，看圖的人分不清有沒有接。
        rows = [(net, ref, value, rail), ...]
        """
        for i, (net, ref, value, rk) in enumerate(rows):
            yy = y + i * pitch
            self.lab(net, x, yy, left=True)
            self.w(x, yy, x + 7.62, yy)
            self.res(ref, value, x + 11.43, yy, 90)
            self.w(x + 15.24, yy, x + 20.32, yy)
            self.rail(rk, x + 20.32, yy)

    def cap_bank(self, x, y, specs, top, bottom="GND", pitch=12.7,
                 top_label=False, bus=8.89):
        """一排去耦電容，共用上下兩條匯流排。

        specs = [(ref, value, footprint 或 None), ...]
        top_label=True 時上方掛全域標籤（給 LDO 內部輸出這種非板級電源軌用）。
        """
        ty, by = y - bus, y + bus
        xs = [x + i * pitch for i in range(len(specs))]
        for (ref, value, fp), cx in zip(specs, xs):
            self.cap(ref, value, cx, y, 0, fp)
            self.w(cx, y - 3.81, cx, ty)
            self.w(cx, y + 3.81, cx, by)
        if len(xs) > 1:
            self.w(xs[0], ty, xs[-1], ty)
            self.w(xs[0], by, xs[-1], by)
            for cx in xs[1:-1]:
                self.j(cx, ty)
                self.j(cx, by)
        mid = xs[len(xs) // 2]
        if top_label:
            self.w(xs[0], ty, xs[0] - 5.08, ty)
            self.lab(top, xs[0] - 5.08, ty, left=True)
        else:
            self.w(mid, ty, mid, ty - 2.54)
            self.rail(top, mid, ty - 2.54)
        self.w(mid, by, mid, by + 2.54)
        self.rail(bottom, mid, by + 2.54)

    # —— 收尾 ——
    def commit(self, note=None):
        append_to_sheet(self.path, self.out)
        for k, v in self.stat.items():
            print(f"  {k:18s} {v}")
        print(f"\n✓ 寫入 {os.path.basename(self.path)}　"
              f"（{sum(self.stat.values())} 個接點）")
        if note:
            print(f"  {note}")
