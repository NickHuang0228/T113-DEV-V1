#!/usr/bin/env python3
"""產生 ADV7511KSTZ 符號 → symbols/T113-DEV-V1-adv7511.kicad_sym

KiCad 內建沒有這顆，100 腳 LQFP 自建。
腳位出處：ADV7511 datasheet Table 3 (p.19-20) + Figure 6 (p.18)，
已整理在 docs/reference/peripherals/ADV7511KSTZ_extracted.md §3。

⚠ ADV7511KSTZ **沒有** Exposed Pad（extracted.md 開頭特別更正過這點）。

依功能分 5 個 unit —— 100 腳擠在一個方塊裡沒辦法接線：
    A 電源與地      24 腳
    B 視訊輸入低位  D0~D17 + CLK/DE/HSYNC/VSYNC
    C 視訊輸入高位  D18~D35（本板全部不用，接 GND）
    D TMDS 與 HDMI  差分輸出、DDC、HPD、R_EXT
    E 控制與音訊    I2C、INT、PD/AD、CEC、I2S/SPDIF/DSD

用法：python hardware/scripts/gen_adv7511_symbol.py
"""
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "symbols", "T113-DEV-V1-adv7511.kicad_sym")

PITCH = 2.54
PIN_LEN = 5.08
WIDTH = 50.8

# (腳號, 名稱, 電氣型別, 左右)
UNITS = [
    # ⚠ 左側的排列順序是依「接哪一條軌」分組的，不是依腳號。
    #   011 §5 把五個 1.8V 域分成三組，同一組的腳相鄰，原理圖上才能
    #   走一條匯流排、只放一個電源符號。不分組的話十三個電源符號擠在
    #   2.54mm 的間距裡，Value 文字會疊成一團墨（ERC 不會報，但圖沒法看）。
    ("A_電源與地", [
        # 組1 +1V8_DVDD
        ("1",  "DVDD",  "power_in", "L"), ("19", "DVDD",  "power_in", "L"),
        ("49", "DVDD",  "power_in", "L"), ("76", "DVDD",  "power_in", "L"),
        ("77", "DVDD",  "power_in", "L"),
        # 組2 +1V8_AVDD（AVDD + PVDD）
        ("24", "PVDD",  "power_in", "L"), ("25", "PVDD",  "power_in", "L"),
        ("29", "AVDD",  "power_in", "L"), ("34", "AVDD",  "power_in", "L"),
        ("41", "AVDD",  "power_in", "L"),
        # 組3 +1V8_PLVDD（PLVDD + BGVDD）
        ("21", "PLVDD", "power_in", "L"), ("26", "BGVDD", "power_in", "L"),
        # 組4 +3V3
        ("47", "MVDD",  "power_in", "L"),
        ("18", "GND", "power_in", "R"), ("20", "GND", "power_in", "R"),
        ("22", "GND", "power_in", "R"), ("23", "GND", "power_in", "R"),
        ("27", "GND", "power_in", "R"), ("31", "GND", "power_in", "R"),
        ("37", "GND", "power_in", "R"), ("44", "GND", "power_in", "R"),
        ("75", "GND", "power_in", "R"), ("99", "GND", "power_in", "R"),
        ("100", "GND", "power_in", "R"),
    ]),
    ("B_視訊輸入", [
        # D0~D17：本板用 D2~D7、D10~D15、D18~D23（RGB666），其餘接 GND
        ("96", "D0",  "input", "L"), ("95", "D1",  "input", "L"),
        ("94", "D2",  "input", "L"), ("93", "D3",  "input", "L"),
        ("92", "D4",  "input", "L"), ("91", "D5",  "input", "L"),
        ("90", "D6",  "input", "L"), ("89", "D7",  "input", "L"),
        ("88", "D8",  "input", "L"), ("87", "D9",  "input", "L"),
        ("86", "D10", "input", "L"), ("85", "D11", "input", "L"),
        ("84", "D12", "input", "R"), ("83", "D13", "input", "R"),
        ("82", "D14", "input", "R"), ("81", "D15", "input", "R"),
        ("80", "D16", "input", "R"), ("78", "D17", "input", "R"),
        ("79", "CLK",   "input", "R"), ("97", "DE",    "input", "R"),
        ("98", "HSYNC", "input", "R"), ("2",  "VSYNC", "input", "R"),
    ]),
    ("C_視訊輸入高位", [
        ("74", "D18", "input", "L"), ("73", "D19", "input", "L"),
        ("72", "D20", "input", "L"), ("71", "D21", "input", "L"),
        ("70", "D22", "input", "L"), ("69", "D23", "input", "L"),
        ("68", "D24", "input", "L"), ("67", "D25", "input", "L"),
        ("66", "D26", "input", "L"), ("65", "D27", "input", "R"),
        ("64", "D28", "input", "R"), ("63", "D29", "input", "R"),
        ("62", "D30", "input", "R"), ("61", "D31", "input", "R"),
        ("60", "D32", "input", "R"), ("59", "D33", "input", "R"),
        ("58", "D34", "input", "R"), ("57", "D35", "input", "R"),
    ]),
    ("D_TMDS與HDMI", [
        ("33", "TXC+", "output", "R"), ("32", "TXC-", "output", "R"),
        ("43", "TX2+", "output", "R"), ("42", "TX2-", "output", "R"),
        ("40", "TX1+", "output", "R"), ("39", "TX1-", "output", "R"),
        ("36", "TX0+", "output", "R"), ("35", "TX0-", "output", "R"),
        ("53", "DDCSCL", "bidirectional", "L"),
        ("54", "DDCSDA", "bidirectional", "L"),
        ("30", "HPD",    "input",  "L"),
        ("52", "HEAC+",  "bidirectional", "L"),
        ("51", "HEAC-",  "bidirectional", "L"),
        ("28", "R_EXT",  "passive", "L"),
    ]),
    ("E_控制與音訊", [
        ("55", "SCL",     "input",          "L"),
        ("56", "SDA",     "bidirectional",  "L"),
        ("45", "~{INT}",  "open_collector", "R"),
        ("38", "PD/AD",   "input",          "L"),
        ("48", "CEC",     "bidirectional",  "R"),
        ("50", "CEC_CLK", "input",          "L"),
        ("10", "SPDIF",     "input",  "L"), ("46", "SPDIF_OUT", "output", "R"),
        ("11", "MCLK",      "input",  "L"), ("16", "SCLK",      "input",  "L"),
        ("17", "LRCLK",     "input",  "L"),
        ("12", "I2S0", "input", "L"), ("13", "I2S1", "input", "L"),
        ("14", "I2S2", "input", "L"), ("15", "I2S3", "input", "L"),
        ("3", "DSD0", "input", "R"), ("4", "DSD1", "input", "R"),
        ("5", "DSD2", "input", "R"), ("6", "DSD3", "input", "R"),
        ("7", "DSD4", "input", "R"), ("8", "DSD5", "input", "R"),
        ("9", "DSD_CLK", "input", "R"),
    ]),
]

# 生成前必擋的事
EXPECT = {
    "2":  "VSYNC",   # ⚠ 在左側，不在頂側 —— 四條同步訊號不同邊
    "79": "CLK",     # ⚠ 夾在 D17 與 D16 之間，不是 D
    "38": "PD/AD",   # ⚠ 一腳兩用：I2C 位址 + PD 極性
    "28": "R_EXT",   # ⚠ 887Ω ±1% 接地，漏了晶片不動
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
    miss = sorted(set(str(i) for i in range(1, 101)) - set(seen), key=int)
    if miss:
        sys.exit(f"✗ 缺腳號：{miss}")
    for num, want in EXPECT.items():
        if seen.get(num) != want:
            sys.exit(f"✗ pin {num} 應為 {want}，表裡是 {seen.get(num)}")
    print(f"  ✓ 100 腳齊全、無重複，四處易錯腳位核對通過")


def build_unit(idx, title, pins):
    left = [p for p in pins if p[3] == "L"]
    right = [p for p in pins if p[3] == "R"]
    rows = max(len(left), len(right), 1)
    y0 = ((rows - 1) // 2 + (rows - 1) % 2) * PITCH
    top = y0 + PITCH
    bot = y0 - (rows - 1) * PITCH - PITCH
    out = [
        f'    (symbol "ADV7511_{idx}_1"',
        f'      (rectangle (start {g(-WIDTH/2)} {g(top)}) (end {g(WIDTH/2)} {g(bot)})',
        '        (stroke (width 0.254) (type default))',
        '        (fill (type background))',
        '      )',
    ]
    for i, (num, name, typ, _) in enumerate(left):
        y = y0 - i * PITCH
        out.append(f"""      (pin {typ} line
        (at {g(-WIDTH/2 - PIN_LEN)} {g(y)} 0)
        (length {g(PIN_LEN)})
        (name "{esc(name)}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27))))
      )""")
    for i, (num, name, typ, _) in enumerate(right):
        y = y0 - i * PITCH
        out.append(f"""      (pin {typ} line
        (at {g(WIDTH/2 + PIN_LEN)} {g(y)} 180)
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
        '  (generator "gen_adv7511_symbol.py")',
        '  (generator_version "10.0")',
        '  (symbol "ADV7511"',
        '    (pin_names (offset 1.016))',
        '    (exclude_from_sim no)',
        '    (in_bom yes)',
        '    (on_board yes)',
        '    (property "Reference" "U" (at 0 0 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        '    (property "Value" "ADV7511KSTZ" (at 0 -2.54 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        '    (property "Footprint" "Package_QFP:LQFP-100_14x14mm_P0.5mm" (at 0 -5.08 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
        '    (property "Datasheet" "docs/reference/peripherals/ADV7511KSTZ_extracted.md" (at 0 -7.62 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
        '    (property "Description" "ADI HDMI transmitter, RGB/YCbCr in, TMDS out, LQFP-100 無 EPAD, LCSC C106732" (at 0 -10.16 0)',
        '      (effects (font (size 1.27 1.27)) (justify left) (hide yes))',
        '    )',
    ]
    for i, (title, pins) in enumerate(UNITS, start=1):
        parts.append(build_unit(i, title, pins))
        print(f"  unit {i}  {title:16s} {len(pins):3d} 腳")
    parts += ['  )', ')']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts) + "\n")
    print(f"\n已產生 {os.path.relpath(OUT, ROOT)}")
    print(f"  合計 {sum(len(p) for _, p in UNITS)} 腳")


if __name__ == "__main__":
    main()
