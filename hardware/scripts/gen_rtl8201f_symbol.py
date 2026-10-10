#!/usr/bin/env python3
"""產生 RTL8201F-VB-CG 符號 → symbols/T113-DEV-V1-rtl8201f.kicad_sym

KiCad 內建沒有這顆（Interface_Ethernet 只有 DP838xx / KSZ80xx / ENC 系列）。
腳位出處：RTL8201F/FL/FN Datasheet Rev 1.4，§5.1 Figure 3「RTL8201F QFN-32 Pin Assignments」(p.5)。

⚠ 這份 datasheet 涵蓋三種封裝，查腳位時極容易拿錯（008-footprint.md 記過）：
    §5.1 RTL8201F   QFN-32   ← 本板用這個
    §5.2 RTL8201FL  LQFP-48
    §5.3 RTL8201FN  QFN-48

⚠ 多支腳是一腳兩用的 strap（上電時的電平決定組態）：
    LED0/PHYAD[0]、LED1/PHYAD[1]   PHY 位址
    RXD[3]/CLK_CTL                 REF_CLK 方向（MAC 提供 or PHY 提供）
    RXD[2]/INTB                    中斷輸出
    RXER/FXEN                      光纖模式
  原理圖上要明確定義這些腳的上電電平 —— 不能當成一般訊號隨便接。

依功能分 3 個 unit：A 電源與類比 / B MII-RMII / C LED-strap

用法：python hardware/scripts/gen_rtl8201f_symbol.py
"""
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "symbols", "T113-DEV-V1-rtl8201f.kicad_sym")

PITCH = 2.54
PIN_LEN = 5.08
WIDTH = 45.72

UNITS = [
    ("A_電源與類比", [
        ("14", "DVDD33",    "power_in",  "L"),
        ("30", "AVDD33",    "power_in",  "L"),
        ("7",  "AVDD33",    "power_in",  "L"),
        ("29", "DVDD10OUT", "power_out", "R"),
        ("2",  "AVDD10OUT", "power_out", "R"),
        ("33", "GND",       "power_in",  "L"),   # E-Pad
        ("1",  "RSET",      "passive",   "L"),   # 參考電阻到地
        ("31", "CKXTAL1",   "input",     "L"),   # 25MHz 晶振
        ("32", "CKXTAL2",   "output",    "R"),
        ("3",  "MDI+[0]",   "bidirectional", "R"),
        ("4",  "MDI-[0]",   "bidirectional", "R"),
        ("5",  "MDI+[1]",   "bidirectional", "R"),
        ("6",  "MDI-[1]",   "bidirectional", "R"),
    ]),
    ("B_MII_RMII", [
        ("20", "TXEN",   "input",  "L"),
        ("19", "TXD[3]", "input",  "L"),
        ("18", "TXD[2]", "input",  "L"),
        ("17", "TXD[1]", "input",  "L"),
        ("16", "TXD[0]", "input",  "L"),
        ("15", "TXC",    "bidirectional", "L"),
        ("8",  "RXDV",          "output", "R"),
        ("9",  "RXD[0]",        "output", "R"),
        ("10", "RXD[1]",        "output", "R"),
        ("11", "RXD[2]/INTB",   "output", "R"),
        ("12", "RXD[3]/CLK_CTL","output", "R"),
        ("13", "RXC",           "output", "R"),
        ("22", "MDC",   "input",         "L"),
        ("23", "MDIO",  "bidirectional", "L"),
        ("21", "PHYRSTB", "input", "L"),
    ]),
    ("C_LED_strap", [
        ("24", "LED0/PHYAD[0]", "output", "R"),
        ("25", "LED1/PHYAD[1]", "output", "R"),
        ("26", "CRS/CRS_DV",    "output", "R"),
        ("27", "COL",           "output", "R"),
        ("28", "RXER/FXEN",     "output", "R"),
        ("23", None, None, None),   # 佔位，實際在 unit B
    ]),
]
# 移除佔位
UNITS[2] = (UNITS[2][0], [p for p in UNITS[2][1] if p[1]])

EXPECT = {
    "12": "RXD[3]/CLK_CTL",   # ⚠ REF_CLK 方向的 strap
    "11": "RXD[2]/INTB",      # ⚠ 中斷也在這支
    "28": "RXER/FXEN",        # ⚠ 光纖模式 strap
    "33": "GND",              # E-Pad，必焊
    "1":  "RSET",             # 參考電阻，漏了 PHY 不動
}


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def g(v):
    return f"{round(v, 4):g}"


def self_check():
    seen = {}
    for _, pins in UNITS:
        for num, name, typ, side in pins:
            if num in seen:
                sys.exit(f"✗ 腳號 {num} 重複（{seen[num]} / {name}）")
            seen[num] = name
    miss = sorted(set(str(i) for i in range(1, 34)) - set(seen), key=int)
    if miss:
        sys.exit(f"✗ 缺腳號：{miss}（33 = E-Pad）")
    for num, want in EXPECT.items():
        if seen.get(num) != want:
            sys.exit(f"✗ pin {num} 應為 {want}，表裡是 {seen.get(num)}")
    print("  ✓ 33 腳齊全（含 E-Pad）、無重複，五處 strap/關鍵腳核對通過")


def build_unit(idx, pins):
    left = [p for p in pins if p[3] == "L"]
    right = [p for p in pins if p[3] == "R"]
    rows = max(len(left), len(right), 1)
    y0 = ((rows - 1) // 2 + (rows - 1) % 2) * PITCH
    top, bot = y0 + PITCH, y0 - (rows - 1) * PITCH - PITCH
    out = [f'    (symbol "RTL8201F_{idx}_1"',
           f'      (rectangle (start {g(-WIDTH/2)} {g(top)}) (end {g(WIDTH/2)} {g(bot)})',
           '        (stroke (width 0.254) (type default))',
           '        (fill (type background))',
           '      )']
    for i, (num, name, typ, _) in enumerate(left):
        out.append(f"""      (pin {typ} line
        (at {g(-WIDTH/2 - PIN_LEN)} {g(y0 - i*PITCH)} 0)
        (length {g(PIN_LEN)})
        (name "{esc(name)}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27))))
      )""")
    for i, (num, name, typ, _) in enumerate(right):
        out.append(f"""      (pin {typ} line
        (at {g(WIDTH/2 + PIN_LEN)} {g(y0 - i*PITCH)} 180)
        (length {g(PIN_LEN)})
        (name "{esc(name)}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27))))
      )""")
    out.append("    )")
    return "\n".join(out)


def main():
    self_check()
    parts = [
        '(kicad_symbol_lib',
        '  (version 20251024)',
        '  (generator "gen_rtl8201f_symbol.py")',
        '  (generator_version "10.0")',
        '  (symbol "RTL8201F"',
        '    (pin_names (offset 1.016))',
        '    (exclude_from_sim no)',
        '    (in_bom yes)',
        '    (on_board yes)',
        '    (property "Reference" "U" (at 0 0 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        '    (property "Value" "RTL8201F-VB-CG" (at 0 -2.54 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        '    (property "Footprint" "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias" (at 0 -5.08 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
        '    (property "Datasheet" "RTL8201F Rev1.4 §5.1 Figure 3 (p.5)" (at 0 -7.62 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
        '    (property "Description" "Realtek 10/100M Ethernet PHY, RMII/MII, Auto-MDIX, QFN-32 5x5 含 E-Pad" (at 0 -10.16 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
    ]
    for i, (title, pins) in enumerate(UNITS, start=1):
        parts.append(build_unit(i, pins))
        print(f"  unit {i}  {title:14s} {len(pins):2d} 腳")
    parts += ['  )', ')']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts) + "\n")
    print(f"\n已產生 {os.path.relpath(OUT, ROOT)}（{sum(len(p) for _, p in UNITS)} 腳）")


if __name__ == "__main__":
    main()
