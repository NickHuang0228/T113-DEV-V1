#!/usr/bin/env python3
"""修掉手畫圖紙上殘留的三個 ERC 問題。

這支和 rename_nets.py 一樣會動到手畫內容，所以用同樣的三道保險：
  ① KiCad 開著就中止
  ② 工作目錄不乾淨就中止
  ③ 每一項都要「剛好符合預期」才動，否則整支中止、一項都不改

修的是什麼（都是 ERC 在八張子頁補完之後剩下的最後三項）：

① mcu 頁　U6 pin 91 (AGND) 沒接到地　★ 這是真的錯
   pin 91 旁邊有一條畫好的線 (134.62,29.21) → (148.59,29.21)，
   但線尾沒有放接地符號 —— 線在、符號沒放。
   圖上看起來「有接」，netlist 裡是一條只有一支腳的孤立 net。
   做法：在線尾補一個 GND 電源符號（純附加，不動既有內容）。

② + ③ power 頁　兩段 1.27mm 的殘線
   U2 (AP2112K-1.8) 的 VIN 在 (50.8, 81.28)、EN 在 (50.8, 83.82)。
   這兩段線從腳位再往右多畫了 1.27mm 到 x=52.07，戳進符號本體裡，
   另一端懸空。電氣上沒影響（腳位的連線靠 43.18→50.8 那兩段加 junction），
   但它們就是「手畫時多拉了一格」的殘留。
   做法：把這兩段 wire 整個刪掉。

用法：python hardware/scripts/fix_legacy.py            # 預覽
      python hardware/scripts/fix_legacy.py --apply    # 真的改
"""
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import guard_kicad_closed, power, sheet_uuid_of, append_to_sheet

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJ = os.path.dirname(ROOT)

# 要刪掉的殘線：(檔名, 起點, 終點)
STUBS = [
    ("power.kicad_sch", ("50.8", "81.28"), ("52.07", "81.28")),
    ("power.kicad_sch", ("52.07", "83.82"), ("50.8", "83.82")),
]
# 要補的接地：(檔名, x, y, 說明)
GNDS = [
    ("mcu.kicad_sch", 148.59, 29.21, "U6 pin 91 AGND 的線尾"),
]
# 要補的 footprint：手畫時沒填，沒有它出不了 BOM / 轉不進 PCB。
# 只補「目前是空字串」的，已經填過的一律不碰。
FOOTPRINTS = [
    ("mcu.kicad_sch", [f"R{i}" for i in range(20, 37)],
     "Resistor_SMD:R_0603_1608Metric", "排針的串接電阻"),
    # U6 T113-S3：內建的 LQFP-128 沒有 EPAD，所以用本專案自建的那顆
    #（gen_t113_footprint.py 產生：內建件 + EPAD 5.72 + 5x5 thermal via）
    ("mcu.kicad_sch", ["U6"],
     "T113-DEV-V1:eLQFP-128_14x14mm_P0.4mm_EP5.72x5.72mm_ThermalVias",
     "T113-S3（EPAD 是它唯一的數位地）"),
    # U1 RY1303：QFN-20 3x3 pitch 0.40，EPAD D2/E2 = 1.65/1.80/1.90
    #（datasheet V1.9 p.10 Package Description 的尺寸表，008 原本記「封裝圖是圖片」）
    # 選 EP1.7 不選 1.65 / 1.85 —— 照 008 §5 對 RTL8201F 用過的同一條判準：
    # land 取「略小於封裝標稱值」。1.80 nom → 1.70 比 nom 小 0.1、又在 min 之上。
    ("power.kicad_sch", ["U1"],
     "Package_DFN_QFN:UQFN-20-1EP_3x3mm_P0.4mm_EP1.7x1.7mm_ThermalVias",
     "RY1303（QFN-20 3x3 P0.4，EP 1.7）"),
]


def git_clean():
    r = subprocess.run(["git", "status", "--porcelain", "-uno", "--", "hardware"],
                       cwd=PROJ, capture_output=True, text=True)
    return r.returncode == 0 and not r.stdout.strip()


def sym_block(txt, ref):
    """切出 reference 等於 ref 的那顆元件的完整 (symbol ...) 區塊。

    從 (reference "Rxx") 往前找最近的 "\\n\\t(symbol\\n"，再往後括號配對。
    不用正則一次抓：元件區塊裡有巢狀括號，正則很容易多吃或少吃。
    """
    m = re.search(r'\(reference "%s"\)' % re.escape(ref), txt)
    if not m:
        return None
    start = txt.rfind("\n\t(symbol\n", 0, m.start())
    if start < 0:
        return None
    start += 1
    d, i = 0, start
    while True:
        c = txt[i]
        if c == '"':
            i += 1
            while txt[i] != '"':
                i += 2 if txt[i] == "\\" else 1
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return txt[start:i + 1]
        i += 1


def wire_block(txt, a, b):
    """找出剛好連接 a→b 的那一段 wire 的完整 S-expression。"""
    pat = (r'\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\) \(xy %s %s\)\n\t\t\)\n'
           r'[\s\S]*?\n\t\)\n' % (a[0], a[1], b[0], b[1]))
    return re.search(pat, txt)


def main():
    apply = "--apply" in sys.argv
    if apply:                    # 預覽不寫檔，不必擋 KiCad
        guard_kicad_closed(ROOT)
    # run_all.py 會在第一步之前檢查一次，之後每一步都會把工作目錄弄髒，
    # 所以它用 --skip-git-check 把這裡關掉。單獨跑的時候仍然要檢查。
    if apply and "--skip-git-check" not in sys.argv and not git_clean():
        sys.exit("✗ hardware/ 有未提交的變更 —— 先 commit，改壞了才回得去。")

    ok = True
    plans = []

    for fname, a, b in STUBS:
        path = os.path.join(ROOT, fname)
        s = io.open(path, encoding="utf-8").read()
        m = wire_block(s, a, b)
        n = len(re.findall(re.escape(f"(xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})"), s))
        tag = "✓" if m and n == 1 else "✗"
        if tag == "✗":
            ok = False
        print(f"  {tag} {fname}  刪除殘線 ({a[0]},{a[1]}) -> ({b[0]},{b[1]})"
              f"　符合 {n} 段（要 1 段）")
        if m:
            plans.append(("del", path, m.group(0)))

    for fname, x, y, why in GNDS:
        path = os.path.join(ROOT, fname)
        s = io.open(path, encoding="utf-8").read()
        # 線尾確實存在、而且那裡還沒有任何符號
        has_wire = f"(xy {x:g} {y:g})" in s
        has_sym = re.search(r'\(at %g %g 0\)' % (x, y), s) is not None
        tag = "✓" if has_wire and not has_sym else "✗"
        if tag == "✗":
            ok = False
        print(f"  {tag} {fname}  在 ({x:g}, {y:g}) 補 GND —— {why}")
        print(f"      線尾存在 {has_wire}　該處已有符號 {has_sym}（要 False）")
        if tag == "✓":
            plans.append(("gnd", path, (x, y)))

    for fname, refs, fp, why in FOOTPRINTS:
        path = os.path.join(ROOT, fname)
        s = io.open(path, encoding="utf-8").read()
        todo = [r for r in refs
                if (sym_block(s, r) or "") .find('(property "Footprint" ""') >= 0]
        print(f"  ✓ {fname}  補 footprint {len(todo)}/{len(refs)} 顆 —— {why}")
        print(f"      {fp}（已填過的不碰）")
        if todo:
            plans.append(("fp", path, (todo, fp)))

    if not ok:
        sys.exit("\n✗ 有項目不符預期，一項都沒改。")
    if not apply:
        print("\n（預覽模式，沒有改檔。要真的改請加 --apply）")
        return

    for kind, path, arg in plans:
        if kind == "del":
            s = io.open(path, encoding="utf-8").read()
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                s.replace(arg, "", 1))
        elif kind == "gnd":
            x, y = arg
            append_to_sheet(path, [power("GND", x, y, 0, sheet_uuid_of(path))])
        else:
            refs, fp = arg
            s = io.open(path, encoding="utf-8").read()
            for ref in refs:
                blk = sym_block(s, ref)
                if not blk or '(property "Footprint" ""' not in blk:
                    continue
                new = blk.replace('(property "Footprint" ""',
                                  f'(property "Footprint" "{fp}"', 1)
                s = s.replace(blk, new, 1)
            io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print(f"\n✓ 已處理 {len(plans)} 項。接著重跑 ERC 確認。")


if __name__ == "__main__":
    main()
