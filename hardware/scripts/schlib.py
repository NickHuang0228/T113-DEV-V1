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


def power(kind, x, y, rot=0, sheet_path=""):
    """電源符號。kind 例如 "GND"、"+3V3"。

    ⚠ 它的 Value 就是 net 名稱 —— 這是電源軌命名的唯一來源，
    寫錯就變成另一條 net（已踩過四次：+3.3V / +1V8_SoC / +5V / MDI0）。
    """
    return symbol(f"power:{kind}", "#PWR", kind, x, y, rot,
                  footprint="", sheet_path=sheet_path, pins=("1",),
                  desc="Power symbol", ref_dy=-3.81, val_dy=3.81)


# ── 檔案層級 ────────────────────────────────────────────

def sheet_uuid_of(path):
    """從既有 .kicad_sch 取出它在階層中的 UUID 路徑（給 instances 用）。"""
    s = io.open(path, encoding="utf-8").read()
    m = re.search(r'\(path "(/[0-9a-f-]+(?:/[0-9a-f-]+)*)"', s)
    return m.group(1) if m else None


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
