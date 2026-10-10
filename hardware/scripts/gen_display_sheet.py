#!/usr/bin/env python3
"""生成顯示頁：ADV7511（RGB→HDMI）+ HDMI 座 + MIPI DSI FPC 座。

資料來源
  002-display.md §1（MIPI/RGB 共用腳與 0Ω 隔離）
                 §3.2.1（電源與電平）
                 §3.2.2（原理圖必備外部元件）
                 ✅ 腳位級接線表（Figure 6, p.18 目視抄出）
  011-power-tree.md §5（三組 1.8V 各經 10µH + 10µF）
  ADV7511KSTZ_extracted.md §3（完整腳位）

⚠ 本板用 RGB666：T113 只給得出 18 bit（PD0~PD21），
  ADV7511 的 D0/D1/D8/D9/D16/D17 與 D24~D35 全部接 GND。

用法：python hardware/scripts/gen_display_sheet.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import (snap, wire, no_connect, global_label, symbol, power,
                    sheet_uuid_of, append_to_sheet, guard_kicad_closed)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "display.kicad_sch")

ADV = "T113-DEV-V1-adv7511:ADV7511"
R_FP = "Resistor_SMD:R_0603_1608Metric"
C_FP = "Capacitor_SMD:C_0603_1608Metric"
L_FP = "Inductor_SMD:L_0805_2012Metric"
PINX = 30.48          # WIDTH/2 + PIN_LEN = 50.8/2 + 5.08

# ── ADV7511 各 unit 的腳位（與 gen_adv7511_symbol.py 的 UNITS 同序）──
# (pin, 名稱, 左右, 第幾列)
def layout(pins):
    """重算符號生成器的排列：左右各自由上往下，間距 2.54。"""
    L = [p for p in pins if p[2] == "L"]
    R = [p for p in pins if p[2] == "R"]
    rows = max(len(L), len(R), 1)
    y0 = ((rows - 1) // 2 + (rows - 1) % 2) * 2.54
    out = {}
    for i, (num, name, side) in enumerate(L):
        out[num] = (name, "L", y0 - i * 2.54)
    for i, (num, name, side) in enumerate(R):
        out[num] = (name, "R", y0 - i * 2.54)
    return out

U1 = layout([("1","DVDD","L"),("19","DVDD","L"),("49","DVDD","L"),("76","DVDD","L"),
             ("77","DVDD","L"),("24","PVDD","L"),("25","PVDD","L"),("21","PLVDD","L"),
             ("26","BGVDD","L"),("29","AVDD","L"),("34","AVDD","L"),("41","AVDD","L"),
             ("47","MVDD","L"),
             ("18","GND","R"),("20","GND","R"),("22","GND","R"),("23","GND","R"),
             ("27","GND","R"),("31","GND","R"),("37","GND","R"),("44","GND","R"),
             ("75","GND","R"),("99","GND","R"),("100","GND","R")])
U2 = layout([("96","D0","L"),("95","D1","L"),("94","D2","L"),("93","D3","L"),
             ("92","D4","L"),("91","D5","L"),("90","D6","L"),("89","D7","L"),
             ("88","D8","L"),("87","D9","L"),("86","D10","L"),("85","D11","L"),
             ("84","D12","R"),("83","D13","R"),("82","D14","R"),("81","D15","R"),
             ("80","D16","R"),("78","D17","R"),("79","CLK","R"),("97","DE","R"),
             ("98","HSYNC","R"),("2","VSYNC","R")])
U3 = layout([("74","D18","L"),("73","D19","L"),("72","D20","L"),("71","D21","L"),
             ("70","D22","L"),("69","D23","L"),("68","D24","L"),("67","D25","L"),
             ("66","D26","L"),("65","D27","R"),("64","D28","R"),("63","D29","R"),
             ("62","D30","R"),("61","D31","R"),("60","D32","R"),("59","D33","R"),
             ("58","D34","R"),("57","D35","R")])
U4 = layout([("53","DDCSCL","L"),("54","DDCSDA","L"),("30","HPD","L"),
             ("52","HEAC+","L"),("51","HEAC-","L"),("28","R_EXT","L"),
             ("33","TXC+","R"),("32","TXC-","R"),("43","TX2+","R"),("42","TX2-","R"),
             ("40","TX1+","R"),("39","TX1-","R"),("36","TX0+","R"),("35","TX0-","R")])
U5 = layout([("55","SCL","L"),("56","SDA","L"),("38","PD/AD","L"),("50","CEC_CLK","L"),
             ("10","SPDIF","L"),("11","MCLK","L"),("16","SCLK","L"),("17","LRCLK","L"),
             ("12","I2S0","L"),("13","I2S1","L"),("14","I2S2","L"),("15","I2S3","L"),
             ("45","~{INT}","R"),("48","CEC","R"),("46","SPDIF_OUT","R"),
             ("3","DSD0","R"),("4","DSD1","R"),("5","DSD2","R"),("6","DSD3","R"),
             ("7","DSD4","R"),("8","DSD5","R"),("9","DSD_CLK","R")])

AT = {1:(127,76.2), 2:(127,190.5), 3:(127,304.8), 4:(304.8,76.2), 5:(304.8,215.9)}

# 電源分組（011 §5）
PWR = {"1":"+1V8_DVDD","19":"+1V8_DVDD","49":"+1V8_DVDD","76":"+1V8_DVDD","77":"+1V8_DVDD",
       "24":"+1V8_AVDD","25":"+1V8_AVDD","29":"+1V8_AVDD","34":"+1V8_AVDD","41":"+1V8_AVDD",
       "21":"+1V8_PLVDD","26":"+1V8_PLVDD","47":"+3V3"}

# RGB666：T113 的 LCD0_D → ADV7511 的 D（002 腳位級接線表）
RGB = {"94":"LCD0_D2","93":"LCD0_D3","92":"LCD0_D4","91":"LCD0_D5","90":"LCD0_D6","89":"LCD0_D7",
       "86":"LCD0_D10","85":"LCD0_D11","84":"LCD0_D12","83":"LCD0_D13","82":"LCD0_D14","81":"LCD0_D15",
       "74":"LCD0_D18","73":"LCD0_D19","72":"LCD0_D20","71":"LCD0_D21","70":"LCD0_D22","69":"LCD0_D23",
       "79":"LCD0_CLK","97":"LCD0_DE","98":"LCD0_HSYNC","2":"LCD0_VSYNC"}
# 未用的視訊輸入 → GND（002：它們是輸入腳 VIL -0.3~0.7V，接地安全）
RGB_GND = ["96","95","88","87","80","78"] + [str(p) for p in range(57,69)]


def main():
    guard_kicad_closed(ROOT)
    if not os.path.exists(SCH):
        sys.exit(f"✗ {os.path.basename(SCH)} 不存在 —— 先跑 new_sheet.py display 顯示")
    path = sheet_uuid_of(SCH)
    out, stat = [], {}

    def place(unit, pins, desc):
        out.append(symbol(ADV, "U7", "ADV7511KSTZ", *AT[unit], unit=unit,
                          sheet_path=path, pins=list(pins),
                          footprint="Package_QFP:LQFP-100_14x14mm_P0.5mm",
                          desc=desc, ref_dy=-22.86, val_dy=22.86))

    def pin_xy(unit, side, ry):
        return snap(AT[unit][0] + (-PINX if side == "L" else PINX)), snap(AT[unit][1] - ry)

    def to_power(unit, info, num, rail):
        name, side, ry = info[num]
        x, y = pin_xy(unit, side, ry)
        dx = -6.35 if side == "L" else 6.35
        out.append(wire(x, y, x + dx, y))
        out.append(power(rail, x + dx, y, 0 if side == "R" else 0, path))

    def to_label(unit, info, num, lab):
        name, side, ry = info[num]
        x, y = pin_xy(unit, side, ry)
        dx = -7.62 if side == "L" else 7.62
        out.append(wire(x, y, x + dx, y))
        out.append(global_label(lab, x + dx, y, 180 if side == "L" else 0,
                                justify="right" if side == "L" else "left"))

    # unit 1 電源與地
    place(1, U1, "ADV7511 電源與地")
    for num, rail in PWR.items():
        to_power(1, U1, num, rail)
    for num in ("18","20","22","23","27","31","37","44","75","99","100"):
        to_power(1, U1, num, "GND")
    stat["電源腳"] = len(PWR) + 11

    # unit 2/3 視訊輸入
    place(2, U2, "ADV7511 視訊輸入 D0~D17")
    place(3, U3, "ADV7511 視訊輸入 D18~D35")
    n_rgb = n_gnd = 0
    for num, lab in RGB.items():
        info, u = (U2, 2) if num in U2 else (U3, 3)
        to_label(u, info, num, lab)
        n_rgb += 1
    for num in RGB_GND:
        info, u = (U2, 2) if num in U2 else (U3, 3)
        to_power(u, info, num, "GND")
        n_gnd += 1
    stat["RGB666 訊號"] = n_rgb
    stat["未用輸入接地"] = n_gnd

    # unit 4 TMDS 與 HDMI
    place(4, U4, "ADV7511 TMDS 與 HDMI")
    for num, lab in (("33","TMDS_CK_P"),("32","TMDS_CK_N"),
                     ("43","TMDS_D2_P"),("42","TMDS_D2_N"),
                     ("40","TMDS_D1_P"),("39","TMDS_D1_N"),
                     ("36","TMDS_D0_P"),("35","TMDS_D0_N"),
                     ("53","HDMI_DDC_SCL"),("54","HDMI_DDC_SDA"),("30","HDMI_HPD")):
        to_label(4, U4, num, lab)
    for num in ("52","51"):            # HEAC（ARC）本板不用
        name, side, ry = U4[num]
        out.append(no_connect(*pin_xy(4, side, ry)))
    # R_EXT 887Ω ±1% 接地 —— 漏了晶片不動（002 §3.2.2）
    name, side, ry = U4["28"]
    x, y = pin_xy(4, side, ry)
    out.append(wire(x, y, x - 7.62, y))
    out.append(symbol("Device:R", "R40", "887R", x - 11.43, y, 90, R_FP,
                      sheet_path=path, desc="Resistor", ref_dy=-3.81, val_dy=3.81))
    out.append(wire(x - 15.24, y, x - 20.32, y))
    out.append(power("GND", x - 20.32, y, 270, path))
    stat["TMDS + DDC + HPD"] = 11

    # unit 5 控制與音訊
    place(5, U5, "ADV7511 控制與音訊")
    for num, lab in (("55","HDMI_I2C_SCL"),("56","HDMI_I2C_SDA"),("45","HDMI_INT_N")):
        to_label(5, U5, num, lab)
    # PD/AD：固定下拉 → I2C 位址 0x72、PD 極性確定（002 §3.2.2 要求明確定義）
    name, side, ry = U5["38"]
    x, y = pin_xy(5, side, ry)
    out.append(wire(x, y, x - 7.62, y))
    out.append(symbol("Device:R", "R41", "10K", x - 11.43, y, 90, R_FP,
                      sheet_path=path, desc="Resistor", ref_dy=-3.81, val_dy=3.81))
    out.append(wire(x - 15.24, y, x - 20.32, y))
    out.append(power("GND", x - 20.32, y, 270, path))
    # 其餘音訊與 CEC 全部不用
    for num in ("50","10","11","16","17","12","13","14","15","48","46",
                "3","4","5","6","7","8","9"):
        name, side, ry = U5[num]
        out.append(no_connect(*pin_xy(5, side, ry)))
    stat["控制訊號"] = 3
    stat["音訊/CEC 不接"] = 18

    append_to_sheet(SCH, out)
    for k, v in stat.items():
        print(f"  {k:16s} {v}")
    print(f"\n✓ 寫入 {os.path.basename(SCH)}")
    print("  ⚠ 尚未產生：HDMI 座、MIPI FPC 座、三組 1.8V 的 LC、去耦電容、I2C 上拉")


if __name__ == "__main__":
    main()
