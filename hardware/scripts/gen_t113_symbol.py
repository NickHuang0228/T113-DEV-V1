#!/usr/bin/env python3
"""從 T113-S3_pinmap.csv 產生 KiCad 符號。

單一真實來源是 CSV —— 符號一律由此生成，不手改 .kicad_sym。
CSV 的 datasheet 欄位由 extract_pins.py 從 Table 4-2 機器抽出（可隨時重抽對帳），
設計欄位（bank / type / note）是人工判斷，來自 Figure 7-1 Pin Map (p.77) 逐腳目視
核對，並與 §4.1 Pin Quantity (p.23) 的五項分類交叉驗證通過。

兩種欄位的一致性在 self_check() 裡驗 —— 人工標的電氣型別必須對得上
datasheet 的 Type 欄，標錯會被擋下來。

用法：python hardware/scripts/gen_t113_symbol.py
"""
import csv
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV = os.path.join(ROOT, "data", "T113-S3_pinmap.csv")
OUT = os.path.join(ROOT, "symbols", "T113-DEV-V1.kicad_sym")

# datasheet Table 4-2 的 Type 欄 → 允許的 KiCad 電氣型別。
#   P/AI/AO 一對多是有理由的：P 涵蓋電源輸入、內建 LDO 輸出與參考電壓腳，
#   AI/AO 涵蓋類比輸入與外掛被動元件的腳。一對一收得太緊會誤殺。
#   真正要擋的是把訊號腳標成電源腳（rules_t113.py 會據此去驗電源軌）。
TYPE_OK = {
    "I/O":   {"bidirectional"},
    "A I/O": {"bidirectional"},
    "I":     {"input"},
    "I, OD": {"input"},
    "O":     {"output"},
    "AI":    {"input", "passive"},
    "AO":    {"output", "power_out"},
    "G":     {"power_in"},
    "P":     {"power_in", "power_out", "passive"},
    "NA":    {"no_connect"},
    "":      {"power_in"},          # EPAD：不在 Table 4-2 裡
}

EPAD_PIN = "129"

PITCH = 2.54
PIN_LEN = 5.08

# (單元編號, 標題, 判定函式) —— 依 bank 切單元，理由見 docs/design/007-pinmap.md §2
UNITS = [
    ("A_電源", lambda r: r["type"].startswith("power") or r["bank"] == "DDR" and r["type"] == "power_in"),
    ("B_PB_PC_PF", lambda r: r["bank"] in ("PB", "PC", "PF")),
    ("C_PD_顯示", lambda r: r["bank"] == "PD"),
    ("D_PE_網路", lambda r: r["bank"] == "PE"),
    ("E_PG_排針", lambda r: r["bank"] == "PG"),
    ("F_類比音訊", lambda r: r["bank"] in ("AUD", "AV")),
    ("G_系統_USB", lambda r: r["bank"] in ("SYS", "USB") or (r["bank"] == "DDR" and r["type"] == "passive")),
]


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def sort_key(r):
    """同 bank 內按訊號索引排序，其餘按腳號。"""
    m = re.match(r"^P([A-G])(\d+)$", r["name"])
    if m:
        return (0, m.group(1), int(m.group(2)))
    return (1, r["name"], int(r["pin"]))


def pin_sexp(r, x, y, rot):
    return f"""      (pin {r['type']} line
        (at {x:g} {y:g} {rot})
        (length {PIN_LEN:g})
        (name "{esc(r['name'])}" (effects (font (size 1.27 1.27))))
        (number "{esc(r['pin'])}" (effects (font (size 1.27 1.27))))
      )"""


def build_unit(idx, title, rows):
    """左右各半，左側輸入/雙向，右側輸出/電源輸出。"""
    left = [r for r in rows if r["type"] in ("input", "power_in", "bidirectional", "passive", "no_connect")]
    right = [r for r in rows if r not in left]
    # 平衡兩側，避免單元過高
    while len(left) - len(right) > 1:
        right.insert(0, left.pop())
    left.sort(key=sort_key)
    right.sort(key=sort_key)

    n = max(len(left), len(right))
    half_h = (n - 1) * PITCH / 2
    width = 63.5
    top = half_h + PITCH * 1.5
    bot = -half_h - PITCH * 1.5

    body = [
        f'    (symbol "T113-S3_{idx}_1"',
        f'      (rectangle (start {-width/2:g} {top:g}) (end {width/2:g} {bot:g})',
        '        (stroke (width 0.254) (type default))',
        '        (fill (type background))',
        '      )',
    ]
    for i, r in enumerate(left):
        y = half_h - i * PITCH
        body.append(pin_sexp(r, -width / 2 - PIN_LEN, y, 0))
    for i, r in enumerate(right):
        y = half_h - i * PITCH
        body.append(pin_sexp(r, width / 2 + PIN_LEN, y, 180))
    body.append("    )")
    return "\n".join(body), title


def self_check(rows):
    """CSV 自我一致性檢查。

    合併成單一來源之後，防線從「兩份表互比」換成兩道：
      ① 這裡 —— 驗表內部一致（腳號完整、人工欄位對得上 datasheet 欄位）
      ② extract_pins.py —— 重抽 Table 4-2，驗 datasheet 欄位沒被改歪
    """
    bad = []

    pins = [r["pin"] for r in rows]
    nums = sorted(int(p) for p in pins)
    gaps = sorted(set(range(1, 129)) - set(nums))
    dup = sorted({p for p in nums if nums.count(p) > 1})
    if gaps:
        bad.append(f"缺腳號：{gaps}")
    if dup:
        bad.append(f"重複腳號：{dup}")
    if EPAD_PIN not in pins:
        bad.append(f"缺 pin {EPAD_PIN} EPAD —— 它是唯一的數位地，不在 Table 4-2 裡")

    for r in rows:
        ds, kt = r["ds_type"], r["type"]
        if ds not in TYPE_OK:
            bad.append(f"pin {r['pin']} {r['name']}：未知的 datasheet Type {ds!r}")
        elif kt not in TYPE_OK[ds]:
            bad.append(f"pin {r['pin']} {r['name']}：datasheet Type={ds!r} "
                       f"但標成 KiCad {kt!r}（允許 {sorted(TYPE_OK[ds])}）")
        if not r["bank"]:
            bad.append(f"pin {r['pin']} {r['name']}：bank 空白")

    # 每支 I/O 腳的電源域，都要在表裡找得到同名的電源腳
    names = {r["name"] for r in rows}
    for r in rows:
        sup = r["supply"]
        if sup and sup != "NA" and sup not in names:
            bad.append(f"pin {r['pin']} {r['name']}：電源域 {sup} 在表裡沒有對應的電源腳")

    if bad:
        for b in bad:
            print(f"  ✗ {b}")
        sys.exit("腳位表自我檢查未過 —— 先修 CSV，不要直接生成")

    print(f"  ✓ 腳位表自我檢查通過（{len(rows)} 列，含 EPAD）")
    print(f"    · 型別：datasheet Type 與 KiCad 電氣型別逐腳相符")
    print(f"    · 電源域：{len({r['supply'] for r in rows if r['supply'] not in ('', 'NA')})} 組，"
          f"每組都有對應的電源腳")
    print(f"    · datasheet 欄位是否仍與 Table 4-2 相符 → python hardware/scripts/extract_pins.py")


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8")))
    self_check(rows)
    assigned = set()
    units = []
    for title, pred in UNITS:
        sel = [r for r in rows if r["pin"] not in assigned and pred(r)]
        assigned.update(r["pin"] for r in sel)
        units.append((title, sel))

    leftover = [r for r in rows if r["pin"] not in assigned]
    if leftover:
        sys.exit("未分配到單元的腳位: " + ", ".join(f"{r['pin']}:{r['name']}" for r in leftover))

    total = sum(len(s) for _, s in units)
    if total != len(rows):
        sys.exit(f"單元腳位合計 {total} != CSV {len(rows)}")

    parts = [
        '(kicad_symbol_lib',
        '  (version 20251024)',
        '  (generator "gen_t113_symbol.py")',
        '  (generator_version "10.0")',
        '  (symbol "T113-S3"',
        '    (pin_names (offset 1.016))',
        '    (exclude_from_sim no)',
        '    (in_bom yes)',
        '    (on_board yes)',
        '    (property "Reference" "U" (at 0 0 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        '    (property "Value" "T113-S3" (at 0 -2.54 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        '    (property "Footprint" "" (at 0 -5.08 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
        '    (property "Datasheet" "docs/reference/allwinner/T113-S3_Datasheet_v1.6_20220303.pdf" (at 0 -7.62 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
        '    (property "Description" "Allwinner T113-S3, 2x Cortex-A7 + HiFi4 DSP, SIP 128MB DDR3, eLQFP128" (at 0 -10.16 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
    ]
    for i, (title, sel) in enumerate(units, start=1):
        sexp, _ = build_unit(i, title, sel)
        parts.append(sexp)
    parts.append('  )')
    parts.append(')')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts) + "\n")

    print(f"已產生 {os.path.relpath(OUT, os.path.dirname(ROOT))}")
    print("  驗證：kicad-cli sym upgrade <檔> --force  然後 sym export svg")
    for i, (title, sel) in enumerate(units, start=1):
        print(f"  單元 {i}  {title:<14} {len(sel):3d} 腳")
    print(f"  {'合計':<18} {total:3d} 腳")


if __name__ == "__main__":
    main()
