#!/usr/bin/env python3
"""從 T113-S3_pinmap.csv 產生 KiCad 符號。

單一真實來源是 CSV —— 符號一律由此生成，不手改 .kicad_sym。
CSV 的數字來自 datasheet Figure 7-1 Pin Map (p.77) 逐腳目視核對，
並與 §4.1 Pin Quantity (p.23) 的五項分類交叉驗證通過。

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


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8")))
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
