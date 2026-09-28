#!/usr/bin/env python3
"""產生電源頁用的小顆 IC 符號 → symbols/T113-DEV-V1-power.kicad_sym

KiCad 內建庫沒有、或內建的料號不對的才放這裡：
    RY1303        三路 DC-DC            內建庫沒有
    APX803-29SA   RESET supervisor      內建庫沒有；⚠ SA / SR 兩種腳位
    TPS2051B      USB 限流開關          內建只有 TPS2051C（腳位相同但料號不同，BOM 會錯）
AP2112K-1.8 直接用內建 Regulator_Linear:AP2112K-1.8，不在這裡。

腳位表就寫在下面 PARTS 裡，每顆附 datasheet 出處 —— 改腳位改這裡再重跑，不要手改 .kicad_sym。
（T113-S3 另外由 gen_t113_symbol.py 生成，它會整檔覆寫，所以不能放同一個檔。）

用法：python hardware/scripts/gen_power_symbols.py
"""
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "symbols", "T113-DEV-V1-power.kicad_sym")

PITCH = 2.54
PIN_LEN = 5.08

# 每支腳：(腳號, 名稱, KiCad 電氣型別, 邊, 位置索引)
#   邊：L 左 / R 右 / B 下 / T 上；位置索引以 PITCH 為單位，L/R 由上往下、B/T 由左往右
#   ★ 同一邊留空的索引就是視覺上的分組間隔
PARTS = [
    {
        "name": "RY1303",
        "value": "RY1303",
        "footprint": "",   # ⚠ 封裝圖是圖片，pitch / EP 尺寸未核對 → footprint 階段再填
        "datasheet": "docs/reference/peripherals/RY1303_datasheet.pdf",
        "desc": "RYCHIP 3ch 2A 1.2MHz sync buck, VIN 2.7-5.5V, total Pout < 6W, QFN20-3x3, LCSC C370881",
        "src": "RY1303 datasheet p.2 Pin Description",
        "width": 25.4,
        "pins": [
            ("10", "VIN1", "power_in", "L", 0),
            ("9",  "EN1",  "input",    "L", 1),
            ("7",  "VIN2", "power_in", "L", 3),
            ("8",  "EN2",  "input",    "L", 4),
            ("19", "VIN3", "power_in", "L", 6),
            ("18", "EN3",  "input",    "L", 7),
            ("11", "SW1",  "output",   "R", 0),
            ("14", "FB1",  "input",    "R", 1),
            ("6",  "SW2",  "output",   "R", 3),
            ("3",  "FB2",  "input",    "R", 4),
            ("20", "SW3",  "output",   "R", 6),
            ("2",  "FB3",  "input",    "R", 7),
            ("12", "GND1A", "power_in", "B", 0),
            ("13", "GND1B", "power_in", "B", 1),
            ("4",  "GNDA",  "power_in", "B", 2),   # CH2 的功率地
            ("5",  "GNDB",  "power_in", "B", 3),   # CH2 的功率地
            ("1",  "GND3",  "power_in", "B", 4),
            ("15", "AGNDA", "power_in", "B", 5),
            ("17", "AGNDB", "power_in", "B", 6),
            ("21", "EP",    "power_in", "B", 7),   # 必須焊大片銅箔並接 GND
            ("16", "NC",    "no_connect", "T", 0),
        ],
    },
    {
        "name": "APX803-29SA",
        "value": "APX803-29SAG-7",
        "footprint": "Package_TO_SOT_SMD:SOT-23",
        "datasheet": "docs/reference/peripherals/APX803_datasheet.pdf",
        "desc": "Diodes reset supervisor 2.93V, 200ms typ, open-drain active-low, SOT23 SA pinout, LCSC C460551",
        "src": "APX803 DS32131 Rev.3-3 p.1 Pin Assignments（SA package）",
        "width": 15.24,
        "pins": [
            ("3", "VCC",      "power_in",       "L", 0),
            ("2", "~{RESET}", "open_collector", "R", 0),
            ("1", "GND",      "power_in",       "B", 0),
        ],
    },
    {
        "name": "TPS2051B",
        "value": "TPS2051BDBVR",
        "footprint": "Package_TO_SOT_SMD:SOT-23-5",
        "datasheet": "docs/reference/peripherals/TPS2051B_datasheet.pdf",
        "desc": "TI 0.5A current-limited power switch, EN active-high, SOT-23-5, LCSC C24593",
        "src": "TPS20xxB SLVS514P Table 5-1（SOT-23 欄）",
        "width": 15.24,
        "pins": [
            ("5", "IN",    "power_in",       "L", 0),
            ("4", "EN",    "input",          "L", 1),
            ("1", "OUT",   "power_out",      "R", 0),
            ("3", "~{OC}", "open_collector", "R", 1),
            ("2", "GND",   "power_in",       "B", 0),
        ],
    },
]

# ⚠ 容易混淆、生成前一定要擋下來的事
EXPECT = {
    # APX803 SA 與 SR 兩種 SOT23 腳位相反：SA = GND1 RESET2 VCC3，SR = RESET1 GND2 VCC3
    ("APX803-29SA", "1"): "GND",
    ("APX803-29SA", "2"): "~{RESET}",
    # TPS2041B 的 EN 是低有效、TPS2051B 是高有效；腳號一樣，名稱不能寫成 ~{EN}
    ("TPS2051B", "4"): "EN",
    # RY1303 腳位不連號的幾處（對照 011-power-tree.md §2.2）
    ("RY1303", "8"): "EN2",
    ("RY1303", "9"): "EN1",
    ("RY1303", "14"): "FB1",
}


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def g(v):
    return f"{round(v, 4):g}"


def self_check(part):
    bad = []
    nums = [p[0] for p in part["pins"]]
    if len(nums) != len(set(nums)):
        bad.append("腳號重複")
    expected_n = max(int(n) for n in nums)
    missing = sorted(set(range(1, expected_n + 1)) - {int(n) for n in nums})
    if missing:
        bad.append(f"缺腳號 {missing}")
    slots = [(p[3], p[4]) for p in part["pins"]]
    if len(slots) != len(set(slots)):
        bad.append("兩支腳擺在同一個位置")
    for (pn, num), name in EXPECT.items():
        if pn == part["name"]:
            got = {p[0]: p[1] for p in part["pins"]}.get(num)
            if got != name:
                bad.append(f"pin {num} 應為 {name}，表裡是 {got}")
    return bad


def build(part):
    pins = part["pins"]
    w = part["width"]
    side_n = {s: max([p[4] for p in pins if p[3] == s], default=-1) + 1 for s in "LRBT"}
    rows = max(side_n["L"], side_n["R"], 1)
    y0 = ((rows - 1) // 2 + (rows - 1) % 2) * PITCH   # 第一列的 y，落在 100 mil 格點
    top = y0 + PITCH
    bot = y0 - (rows - 1) * PITCH - PITCH  # 本體下緣

    def x_of(idx, n):                      # 上下邊的腳，大致置中且落在 100 mil 格點
        return (idx - n // 2) * PITCH

    out = [
        f'  (symbol "{esc(part["name"])}"',
        '    (pin_names (offset 1.016))',
        '    (exclude_from_sim no)',
        '    (in_bom yes)',
        '    (on_board yes)',
        f'    (property "Reference" "U" (at {g(-w/2)} {g(top + 1.27)} 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        f'    (property "Value" "{esc(part["value"])}" (at {g(-w/2)} {g(bot - 1.27 - (PIN_LEN if side_n["B"] else 0))} 0)',
        '      (effects (font (size 1.27 1.27)) (justify left))',
        '    )',
        f'    (property "Footprint" "{esc(part["footprint"])}" (at 0 0 0)',
        '      (effects (font (size 1.27 1.27)) (hide yes))',
        '    )',
        f'    (property "Datasheet" "{esc(part["datasheet"])}" (at 0 0 0)',
        '      (effects (font (size 1.27 1.27)) (hide yes))',
        '    )',
        f'    (property "Description" "{esc(part["desc"])}" (at 0 0 0)',
        '      (effects (font (size 1.27 1.27)) (hide yes))',
        '    )',
        f'    (symbol "{esc(part["name"])}_0_1"',
        f'      (rectangle (start {g(-w/2)} {g(top)}) (end {g(w/2)} {g(bot)})',
        '        (stroke (width 0.254) (type default))',
        '        (fill (type background))',
        '      )',
        '    )',
        f'    (symbol "{esc(part["name"])}_1_1"',
    ]
    for num, name, typ, side, idx in pins:
        if side == "L":
            x, y, rot = -w / 2 - PIN_LEN, y0 - idx * PITCH, 0
        elif side == "R":
            x, y, rot = w / 2 + PIN_LEN, y0 - idx * PITCH, 180
        elif side == "B":
            x, y, rot = x_of(idx, side_n["B"]), bot - PIN_LEN, 90
        else:
            x, y, rot = x_of(idx, side_n["T"]), top + PIN_LEN, 270
        out += [
            f'      (pin {typ} line',
            f'        (at {g(x)} {g(y)} {rot})',
            f'        (length {g(PIN_LEN)})',
            f'        (name "{esc(name)}" (effects (font (size 1.27 1.27))))',
            f'        (number "{esc(num)}" (effects (font (size 1.27 1.27))))',
            '      )',
        ]
    out += ['    )', '  )']
    return "\n".join(out)


def main():
    failed = False
    for part in PARTS:
        bad = self_check(part)
        if bad:
            failed = True
            for b in bad:
                print(f"  ✗ {part['name']}：{b}")
        else:
            print(f"  ✓ {part['name']:<12} {len(part['pins']):2d} 腳 · 出處 {part['src']}")
    if failed:
        sys.exit("腳位表自我檢查未過 —— 先修 PARTS，不要直接生成")

    parts = [
        '(kicad_symbol_lib',
        '  (version 20251024)',
        '  (generator "gen_power_symbols.py")',
        '  (generator_version "10.0")',
    ]
    parts += [build(p) for p in PARTS]
    parts.append(')')
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(parts) + "\n")
    print(f"已產生 {os.path.relpath(OUT, os.path.dirname(ROOT))}")


if __name__ == "__main__":
    main()
