#!/usr/bin/env python3
"""生成主晶片頁的 unit 6（類比音訊）與 unit 7（系統/USB）。

資料來源
  unit 6  MangoPi MQ-R v1.6 原理圖 p.3（datasheet 沒有應用電路）
          耳機   HPOUTL/R 各串 33R 再 AC 耦合 0.1µF；HPOUTFB 接耳機座接地環
          未用腳 FMINL/R 在 MangoPi 直接打 ✗ → 本板其餘未用類比腳比照辦理
  unit 7  011 §6.1（DZQ 240R）、004-usb-boot.md（USB 極性）、
          007-pinmap.md（RESET 接 SYS_RESET_N）

⚠ USB0 與 USB1 的 DP/DM 腳序相反（010-symbol.md 記的四處非連號之一）：
      USB0  pin114=DM  pin115=DP
      USB1  pin112=DP  pin113=DM
  照 pin 號推會接反，一定要照腳名接。

用法：python hardware/scripts/gen_mcu_unit67.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from schlib import (uid, snap, g, wire, junction, no_connect, global_label,
                    symbol, power, sheet_uuid_of, append_to_sheet,
                    guard_kicad_closed)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "mcu.kicad_sch")

SYM = "T113-DEV-V1:T113-S3"
R_FP = "Resistor_SMD:R_0603_1608Metric"
C_FP = "Capacitor_SMD:C_0603_1608Metric"

# 符號本體寬 63.5，腳位伸出 5.08 → 接點在 ±36.83
PINX = 36.83

# ⚠ unit 6 / unit 7 的符號本體**已經在 KiCad 裡手動放好了**，
#   這支腳本只負責接線，不再放一份。
#
#   第一版寫死座標 (190.5, 320.04) / (190.5, 441.96) 兩個問題：
#     ① 跟手動放的那一份重複 → ERC 噴 14 個 different_unit_net
#        （同一支腳出現在兩個地方，各自接到不同的 net）
#     ② A3 只有 297mm 高，y=320 / y=442 根本在紙面外
#   所以改成從檔案裡把既有的擺放位置讀出來。
def find_unit(txt, unit):
    """從 mcu.kicad_sch 讀出某個 unit 已經被放在哪裡。"""
    pat = (r'\(symbol\n\t\t\(lib_id "T113-DEV-V1:T113-S3"\)\n'
           r'\t\t\(at ([\d.]+) ([\d.]+) \d+\)\n\t\t\(unit (\d+)\)')
    for m in re.finditer(pat, txt):
        if int(m.group(3)) == unit:
            return (float(m.group(1)), float(m.group(2)))
    return None

# (pin, 腳名, 相對 y, 左右)
U6_PINS = {
    "94": ("FMINL",    11.43, "L"), "99": ("HPOUTL",   11.43, "R"),
    "93": ("FMINR",     8.89, "L"), "98": ("HPOUTR",    8.89, "R"),
    "101": ("GPADC0",   6.35, "L"), "104": ("TP-Y1",    6.35, "R"),
    "100": ("HPOUTFB",  3.81, "L"), "105": ("TP-Y2",    3.81, "R"),
    "96": ("LINEINL",   1.27, "L"), "111": ("TVIN-VRN", 1.27, "R"),
    "95": ("LINEINR",  -1.27, "L"), "110": ("TVIN-VRP",-1.27, "R"),
    "88": ("MICIN3N",  -3.81, "L"), "108": ("TVIN0",   -3.81, "R"),
    "87": ("MICIN3P",  -6.35, "L"), "109": ("TVIN1",   -6.35, "R"),
    "102": ("TP-X1",   -8.89, "L"), "78": ("TVOUT0",   -8.89, "R"),
    "103": ("TP-X2",  -11.43, "L"),
}
U7_PINS = {
    "23": ("DXIN",      6.35, "L"), "22": ("DXOUT",      6.35, "R"),
    "47": ("DZQ",       3.81, "L"), "21": ("REFCLK-OUT", 3.81, "R"),
    "106": ("NC0",      1.27, "L"), "114": ("USB0-DM",   1.27, "R"),
    "27": ("RESET",    -1.27, "L"), "115": ("USB0-DP",  -1.27, "R"),
    "112": ("USB1-DP", -3.81, "L"), "113": ("USB1-DM",  -3.81, "R"),
    "25": ("X32KIN",   -6.35, "L"), "24": ("X32KOUT",   -6.35, "R"),
}

# unit 6：直接拉全域標籤的腳（耳機回授）
U6_LABEL = {"100": "HP_FB"}
# unit 6：串 33R + 0.1µF 再出去的腳 → (標籤, R ref, C ref)
U6_AC = {
    "99": ("HP_L", "R37", "C20"),
    "98": ("HP_R", "R38", "C21"),
}
# unit 6：其餘全部 No Connect（MangoPi 對 FMINL/R 就是這樣）
U6_NC = ["94", "93", "101", "104", "105", "96", "111", "95", "110",
         "88", "108", "87", "109", "102", "78", "103"]

# unit 7：直接拉全域標籤
U7_LABEL = {
    "27":  "SYS_RESET_N",     # 電源頁的 APX803 已備好
    "114": "USB0_DM", "115": "USB0_DP",   # ⚠ 照腳名，不照 pin 號
    "112": "USB1_DP", "113": "USB1_DM",
    "22":  "DXOUT", "23": "DXIN",         # 24MHz 晶振，元件放這頁
    "24":  "X32KOUT", "25": "X32KIN",     # 32.768kHz
}


def pin_xy(at, rel_y, side):
    x = at[0] + (-PINX if side == "L" else PINX)
    return snap(x), snap(at[1] - rel_y)


def main():
    guard_kicad_closed(ROOT)
    path = sheet_uuid_of(SCH)
    if not path:
        sys.exit("✗ 取不到圖紙的階層 UUID 路徑")
    txt = io.open(SCH, encoding="utf-8").read()
    U6_AT = find_unit(txt, 6)
    U7_AT = find_unit(txt, 7)
    if not U6_AT or not U7_AT:
        sys.exit("✗ mcu.kicad_sch 上找不到已擺放的 unit 6 / unit 7 —— "
                 "先在 KiCad 裡把這兩個 unit 放上去再跑")
    if any(y > 290 for _, y in (U6_AT, U7_AT)):
        sys.exit(f"✗ unit 6/7 的擺放位置超出 A3 紙面：{U6_AT} {U7_AT}")
    print(f"圖紙路徑 {path}")
    print(f"沿用既有擺放：unit 6 @{U6_AT}　unit 7 @{U7_AT}")

    out = []
    n_lab = n_nc = n_ac = 0
    for p, lab in U6_LABEL.items():
        nm, ry, side = U6_PINS[p]
        x, y = pin_xy(U6_AT, ry, side)
        dx = -7.62 if side == "L" else 7.62
        out.append(wire(x, y, x + dx, y))
        out.append(global_label(lab, x + dx, y, 180 if side == "L" else 0,
                                justify="right" if side == "L" else "left"))
        n_lab += 1
    # 耳機：腳 →[33R]→[0.1µF]→ 標籤（兩顆都水平擺）
    for p, (lab, rref, cref) in U6_AC.items():
        nm, ry, side = U6_PINS[p]
        x, y = pin_xy(U6_AT, ry, side)
        out.append(wire(x, y, x + 5.08, y))
        out.append(symbol("Device:R", rref, "33R", x + 8.89, y, 90,
                          R_FP, sheet_path=path, desc="Resistor",
                          ref_dy=-3.81, val_dy=3.81))
        out.append(wire(x + 12.7, y, x + 17.78, y))
        out.append(symbol("Device:C", cref, "0.1uF", x + 21.59, y, 90,
                          C_FP, sheet_path=path, desc="Unpolarized capacitor",
                          ref_dy=-3.81, val_dy=3.81))
        out.append(wire(x + 25.4, y, x + 30.48, y))
        out.append(global_label(lab, x + 30.48, y, 0, justify="left"))
        n_ac += 1
    for p in U6_NC:
        nm, ry, side = U6_PINS[p]
        x, y = pin_xy(U6_AT, ry, side)
        out.append(no_connect(x, y))
        n_nc += 1

    # ── unit 7 ──
    for p, lab in U7_LABEL.items():
        nm, ry, side = U7_PINS[p]
        x, y = pin_xy(U7_AT, ry, side)
        dx = -7.62 if side == "L" else 7.62
        out.append(wire(x, y, x + dx, y))
        out.append(global_label(lab, x + dx, y, 180 if side == "L" else 0,
                                justify="right" if side == "L" else "left"))
        n_lab += 1

    # DZQ 240R 1% 到 GND（DDR3 阻抗校準基準，011 §6.1）
    nm, ry, side = U7_PINS["47"]
    x, y = pin_xy(U7_AT, ry, side)
    out.append(wire(x, y, x - 7.62, y))
    out.append(symbol("Device:R", "R39", "240R", x - 11.43, y, 90,
                      R_FP, sheet_path=path, desc="Resistor",
                      ref_dy=-3.81, val_dy=3.81))
    out.append(wire(x - 15.24, y, x - 20.32, y))
    out.append(power("GND", x - 20.32, y, 270, path))

    # NC0 (pin 106)：MangoPi 掛 1K 標 NC；本板直接 No Connect
    nm, ry, side = U7_PINS["106"]
    out.append(no_connect(*pin_xy(U7_AT, ry, side)))

    # REFCLK-OUT (pin 21)：時脈輸出，本板不用
    nm, ry, side = U7_PINS["21"]
    out.append(no_connect(*pin_xy(U7_AT, ry, side)))

    # ── 兩顆晶振 ──────────────────────────────────────
    # ★ 第一版整個漏掉了。ERC 的 isolated_pin_label（DXIN/DXOUT/X32KIN/X32KOUT
    #   四個標籤接不到任何東西）才抓出來 —— 沒有 24MHz 晶振，SoC 根本不會動。
    #
    # 規格照 MangoPi MQ-R v1.6 p.3（同一顆 T113-S3，已量產驗證過）：
    #     X1  XTAL2520-24M   CL=18pF    load cap C8/C9   = 22pF
    #     XT1 32.768K        CL=12.5pF  load cap C43/C45 = 22pF
    # 晶片端的雜散電容 MangoPi 也標了：DCXO Cshunt 6.5pF、RTC Cshunt 1.1pF。
    # ⚠ 換晶振一定要重算負載電容 —— 這是唯一會讓板子「時好時壞」的地方。
    for (cx, cy, ref, val, fp, lin, lout, ca, cb) in (
            (190.5, 243.84, "Y2", "24MHz",
             "Crystal:Crystal_SMD_2520-4Pin_2.5x2.0mm",
             "DXIN", "DXOUT", "C43", "C44"),
            (266.7, 243.84, "Y3", "32.768kHz",
             "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm",
             "X32KIN", "X32KOUT", "C45", "C46")):
        out.append(symbol("Device:Crystal_GND24", ref, val, cx, cy, 0, fp,
                          sheet_path=path, pins=("1", "2", "3", "4"),
                          desc="Two pin crystal, GND on pins 2 and 4",
                          ref_dy=-8.89, val_dy=-6.35))
        out.append(wire(cx - 3.81, cy, cx - 11.43, cy))
        out.append(global_label(lin, cx - 11.43, cy, 180, justify="right"))
        out.append(wire(cx + 3.81, cy, cx + 11.43, cy))
        out.append(global_label(lout, cx + 11.43, cy, 0, justify="left"))
        out.append(wire(cx, cy + 5.08, cx, cy + 7.62))
        out.append(power("GND", cx, cy + 7.62, 0, path))
        for cref, lx in ((ca, cx - 3.81), (cb, cx + 3.81)):
            out.append(junction(lx, cy))
            out.append(wire(lx, cy, lx, cy + 8.89))
            out.append(symbol("Device:C", cref, "22pF", lx, cy + 12.7, 0, C_FP,
                              sheet_path=path, desc="Unpolarized capacitor",
                              ref_dy=-3.81, val_dy=3.81))
            out.append(wire(lx, cy + 16.51, lx, cy + 19.05))
            out.append(power("GND", lx, cy + 19.05, 0, path))

    append_to_sheet(SCH, out)
    print("✓ 晶振：Y2 24MHz（DCXO）、Y3 32.768kHz（RTC），各配兩顆 22pF")
    print(f"✓ unit 6：標籤 {len(U6_LABEL)}、耳機鏈 {n_ac} 組、No Connect {n_nc}")
    print(f"✓ unit 7：標籤 {len(U7_LABEL)}、DZQ 240R、No Connect 2")
    print(f"  寫入 {os.path.relpath(SCH, ROOT)}")


if __name__ == "__main__":
    main()
