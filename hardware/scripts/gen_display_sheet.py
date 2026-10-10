#!/usr/bin/env python3
"""生成顯示頁：ADV7511 本體（RGB666 → TMDS）。

HDMI 座、5V 供電與 HPD 串接在另一張圖紙（gen_hdmi_sheet.py），
MIPI FPC 座再另一張 —— 100 腳的晶片加上接頭塞不進一張 A3，
而「塞得進去」比「分頁」重要得多：這張圖是接下來佈線時唯一的依據。

資料來源
  002-display.md  §1.2（PD0~PD9 用 0Ω 隔離）· §3.2.1（電源與電平）
                  §3.2.2（原理圖必備外部元件）· §3.2 正確的 D 索引對應
  011-power-tree.md §5（三組 1.8V 各經 10µH + 10µF）
  ADV7511KSTZ_extracted.md §3.4（電平）· §3B（Figure 27 參考接法）

兩個關鍵決定
  ① RGB666：T113 只給得出 18 bit。D0/D1/D8/D9/D16/D17 與 D24~D35 全部接 GND。
     接 GND 而不是把 MSB 複製到 LSB —— 為了 1.2% 的亮度在 6 條線上多掛分支不划算。
  ② PD0~PD9 這 10 條與 MIPI DSI 共用實體接腳，中間要串 0Ω：
       跑 MIPI → 0Ω 不焊，ADV7511 的輸入電容從 MIPI 線上斷開
       跑 HDMI → 0Ω 焊上
     ★ 那十顆 0Ω 是 mcu 頁的 R10~R19，不在這一頁。
       這一頁只接 0Ω 的下游（LCD0_D2~D13），不要再串一顆。
     ⚠ layout 時 0Ω 焊盤邊緣距離 MIPI 主幹必須 ≤ 0.5mm，放遠了 stub 還在。

用法：python hardware/scripts/gen_display_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page, snap

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "display.kicad_sch")

ADV = "T113-DEV-V1-adv7511:ADV7511"
ADV_FP = "Package_QFP:LQFP-100_14x14mm_P0.5mm"
PINX = 30.48                     # 符號：WIDTH/2 + PIN_LEN = 25.4 + 5.08

# ── 五個 unit 的腳位排列（必須與 gen_adv7511_symbol.py 的 UNITS 同序）──
U1_PINS = [("1", "L"), ("19", "L"), ("49", "L"), ("76", "L"), ("77", "L"),
           ("24", "L"), ("25", "L"), ("21", "L"), ("26", "L"),
           ("29", "L"), ("34", "L"), ("41", "L"), ("47", "L"),
           ("18", "R"), ("20", "R"), ("22", "R"), ("23", "R"), ("27", "R"),
           ("31", "R"), ("37", "R"), ("44", "R"), ("75", "R"), ("99", "R"),
           ("100", "R")]
U2_PINS = [("96", "L"), ("95", "L"), ("94", "L"), ("93", "L"), ("92", "L"),
           ("91", "L"), ("90", "L"), ("89", "L"), ("88", "L"), ("87", "L"),
           ("86", "L"), ("85", "L"),
           ("84", "R"), ("83", "R"), ("82", "R"), ("81", "R"), ("80", "R"),
           ("78", "R"), ("79", "R"), ("97", "R"), ("98", "R"), ("2", "R")]
U3_PINS = [("74", "L"), ("73", "L"), ("72", "L"), ("71", "L"), ("70", "L"),
           ("69", "L"), ("68", "L"), ("67", "L"), ("66", "L"),
           ("65", "R"), ("64", "R"), ("63", "R"), ("62", "R"), ("61", "R"),
           ("60", "R"), ("59", "R"), ("58", "R"), ("57", "R")]
U4_PINS = [("53", "L"), ("54", "L"), ("30", "L"), ("52", "L"), ("51", "L"),
           ("28", "L"),
           ("33", "R"), ("32", "R"), ("43", "R"), ("42", "R"),
           ("40", "R"), ("39", "R"), ("36", "R"), ("35", "R")]
U5_PINS = [("55", "L"), ("56", "L"), ("38", "L"), ("50", "L"), ("10", "L"),
           ("11", "L"), ("16", "L"), ("17", "L"),
           ("12", "L"), ("13", "L"), ("14", "L"), ("15", "L"),
           ("45", "R"), ("48", "R"), ("46", "R"),
           ("3", "R"), ("4", "R"), ("5", "R"), ("6", "R"), ("7", "R"),
           ("8", "R"), ("9", "R")]

AT = {1: (95.25, 54.61), 2: (95.25, 125.73), 3: (95.25, 200.66),
      4: (289.56, 54.61), 5: (289.56, 134.62)}


def pin_map(pins, origin):
    L = [n for n, s in pins if s == "L"]
    R = [n for n, s in pins if s == "R"]
    rows = max(len(L), len(R), 1)
    y0 = ((rows - 1) // 2 + (rows - 1) % 2) * 2.54
    ox, oy = origin
    out = {}
    for i, n in enumerate(L):
        out[n] = (snap(ox - PINX), snap(oy - (y0 - i * 2.54)), "L")
    for i, n in enumerate(R):
        out[n] = (snap(ox + PINX), snap(oy - (y0 - i * 2.54)), "R")
    return out


P = {u: pin_map(pins, AT[u])
     for u, pins in ((1, U1_PINS), (2, U2_PINS), (3, U3_PINS),
                     (4, U4_PINS), (5, U5_PINS))}
UNIT_OF = {n: u for u, m in P.items() for n in m}

# ── 電源（011 §5 的三組分法）────────────────────────────
PWR = {"1": "+1V8_DVDD", "19": "+1V8_DVDD", "49": "+1V8_DVDD",
       "76": "+1V8_DVDD", "77": "+1V8_DVDD",
       "24": "+1V8_AVDD", "25": "+1V8_AVDD",         # PVDD 併進 AVDD 組
       "29": "+1V8_AVDD", "34": "+1V8_AVDD", "41": "+1V8_AVDD",
       "21": "+1V8_PLVDD", "26": "+1V8_PLVDD",       # PLVDD + BGVDD
       "47": "+3V3"}                                  # MVDD
GND_PINS = ["18", "20", "22", "23", "27", "31", "37", "44", "75", "99", "100"]

# ── 視訊輸入（002 §3.2：按 D 索引 1:1 接，不經過顏色名稱）──
#
# ⚠ 002 §1.2 要求的那 10 顆 0Ω 隔離電阻 **已經畫在 mcu 頁了**（R10~R19）：
#       U6 PD0 ──┬── MIPI FPC        直通
#                └─[R10 0Ω]── LCD0_D2 ── ADV7511 D2
#   第一版在這裡又串了一顆（R71~R80），變成每條線兩顆 0Ω、兩個分支點，
#   連「0Ω 焊盤距主幹 ≤0.5mm」這條規則都失去意義（要距離哪一個？）。
#   所以這裡全部直接接 LCD0_Dx —— 隔離由 mcu 頁那十顆負責。
DIRECT = {"94": "LCD0_D2", "93": "LCD0_D3", "92": "LCD0_D4",
          "91": "LCD0_D5", "90": "LCD0_D6", "89": "LCD0_D7",
          "86": "LCD0_D10", "85": "LCD0_D11", "84": "LCD0_D12",
          "83": "LCD0_D13",
          "82": "LCD0_D14", "81": "LCD0_D15",
          "74": "LCD0_D18", "73": "LCD0_D19", "72": "LCD0_D20",
          "71": "LCD0_D21", "70": "LCD0_D22", "69": "LCD0_D23",
          "79": "LCD0_CLK", "97": "LCD0_DE",
          "98": "LCD0_HSYNC", "2": "LCD0_VSYNC"}
# 用不到的視訊輸入 → GND（都是輸入腳，VIL 下限 -0.3V，接地安全）
VID_GND = ["96", "95", "88", "87", "80", "78"] + [str(n) for n in range(57, 69)]

# ── 控制 ───────────────────────────────────────────────
CTRL = {"53": "HDMI_DDC_SCL", "54": "HDMI_DDC_SDA", "30": "HDMI_HPD",
        "33": "TMDS_CK_P", "32": "TMDS_CK_N",
        "43": "TMDS_D2_P", "42": "TMDS_D2_N",
        "40": "TMDS_D1_P", "39": "TMDS_D1_N",
        "36": "TMDS_D0_P", "35": "TMDS_D0_N",
        # I2C 與排針的 TWI1 共用同一條匯流排（PG7/PG8，經 mcu 頁的 100R）
        "55": "HDR_I2C1_SCL", "56": "HDR_I2C1_SDA",
        "45": "HDMI_INT_N",
        # PD/AD 一腳兩用：上電瞬間的準位同時決定 I2C 位址與 PD 極性。
        # 下拉電阻保證上電準位，GPIO 之後才有辦法把晶片關掉（002 §1.4）。
        "38": "HDMI_PD"}
# CEC_CLK 需要外部 12MHz 振盪器，V1 不做 CEC → 接 GND。
# 不能讓它浮接：它是 CMOS 輸入腳。
TO_GND = ["50"]
# HEAC（ARC）、CEC、以及全部音訊都不做
NC_PINS = ["52", "51", "48", "46",
           "10", "11", "16", "17", "12", "13", "14", "15",
           "3", "4", "5", "6", "7", "8", "9"]


def main():
    p = Page(SCH, ROOT)
    desc = {1: "ADV7511 電源與地", 2: "ADV7511 視訊輸入 D0~D17",
            3: "ADV7511 視訊輸入 D18~D35", 4: "ADV7511 TMDS 與 HDMI",
            5: "ADV7511 控制與音訊"}
    for u, pins in ((1, U1_PINS), (2, U2_PINS), (3, U3_PINS),
                    (4, U4_PINS), (5, U5_PINS)):
        p.part(ADV, "U7", "ADV7511KSTZ", *AT[u], 0, ADV_FP, u,
               [n for n, _ in pins], desc[u], ref_dy=-24.13, val_dy=24.13)

    def at(n):
        return P[UNIT_OF[n]][n]

    # ── 電源與地 ──────────────────────────────────────
    for n, kind in PWR.items():
        x, y, s = at(n)
        p.pin_rail(x, y, s, kind)
    for n in GND_PINS:
        x, y, s = at(n)
        p.pin_rail(x, y, s, "GND")
    p.stat["電源腳"] = len(PWR)
    p.stat["接地腳"] = len(GND_PINS)

    # ── 視訊輸入 ──────────────────────────────────────
    for n, net in DIRECT.items():
        x, y, s = at(n)
        p.pin_label(x, y, s, net)
    for n in VID_GND:
        x, y, s = at(n)
        p.pin_rail(x, y, s, "GND")
    p.stat["RGB 訊號"] = len(DIRECT)
    p.stat["未用輸入接地"] = len(VID_GND)

    # ── 控制與 TMDS ───────────────────────────────────
    for n, net in CTRL.items():
        x, y, s = at(n)
        p.pin_label(x, y, s, net)
    for n in TO_GND:
        x, y, s = at(n)
        p.pin_rail(x, y, s, "GND")
    for n in NC_PINS:
        x, y, _ = at(n)
        p.nc(x, y)
    p.stat["控制/TMDS"] = len(CTRL)
    p.stat["刻意不接"] = len(NC_PINS) + len(TO_GND)

    # ── R_EXT：887Ω ±1% 接地 ──────────────────────────
    # 設定內部參考電流。datasheet 寫「走線越短越好」，而且特別點名
    # LRCLK（含 via）不可靠近 pin 28 —— 所以畫在腳位旁邊，不丟進電阻區。
    x, y, s = at("28")
    p.pin_res_rail(x, y, s, "R70", "887R 1%", "GND")
    p.stat["R_EXT"] = 1

    # ── 三組 1.8V 的 LC ───────────────────────────────
    for i, (dst, lref, cref) in enumerate((("+1V8_DVDD", "L4", "C22"),
                                           ("+1V8_AVDD", "L5", "C23"),
                                           ("+1V8_PLVDD", "L6", "C24"))):
        p.lc_filter(30.48 + i * 83.82, 236.22, "+1V8_HDMI", dst,
                    lref, "10uH", cref, "10uF",
                    "Capacitor_SMD:C_0805_2012Metric")
    p.stat["1.8V LC"] = 3

    # ── 每支電源腳一顆 0.1µF ──────────────────────────
    p.cap_bank(38.1, 266.7, [(f"C{25+i}", "100nF", None) for i in range(5)],
               "+1V8_DVDD")
    p.cap_bank(114.3, 266.7, [(f"C{30+i}", "100nF", None) for i in range(5)],
               "+1V8_AVDD")
    p.cap_bank(190.5, 266.7, [("C35", "100nF", None), ("C36", "100nF", None)],
               "+1V8_PLVDD")
    p.cap_bank(228.6, 266.7, [("C37", "100nF", None)], "+3V3")
    p.stat["去耦電容"] = 13

    # ── 上下拉（002 §3.2.2 / §3B Figure 27）───────────
    p.strap_bank(289.56, 180.34, [
        ("HDR_I2C1_SCL", "R73", "2K",   "+3V3"),     # 控制 I2C，2kΩ ±5%
        ("HDR_I2C1_SDA", "R74", "2K",   "+3V3"),
        ("HDMI_INT_N",   "R75", "2K",   "+3V3"),     # 開汲極輸出，2kΩ ±10%
        ("HDMI_DDC_SCL", "R76", "2K",   "HDMI_5V"),  # DDC 依規範上拉到 5V
        ("HDMI_DDC_SDA", "R77", "2K",   "HDMI_5V"),
        ("HDMI_HPD",     "R71", "100K", "GND"),      # 沒插線時定義為低
        ("HDMI_PD",      "R72", "10K",  "GND"),      # ★ 決定 I2C 位址與 PD 極性
    ])
    p.stat["上下拉"] = 7

    # 三組 1.8V 是經過電感來的、HDMI_5V 是經過保險絲來的 ——
    # 電感與保險絲都是被動件，ERC 看不出這些軌有人供電。
    for i, net in enumerate(("+1V8_DVDD", "+1V8_AVDD", "+1V8_PLVDD")):
        p.pwr_flag(net, 30.48 + i * 83.82, 215.9)
    p.stat["PWR_FLAG"] = 3

    # ── 收尾前確認 100 支腳一支都沒漏 ────────────────
    touched = (set(PWR) | set(GND_PINS) | set(DIRECT)
               | set(VID_GND) | set(CTRL) | set(TO_GND) | set(NC_PINS) | {"28"})
    allp = set(UNIT_OF)
    miss = sorted(allp - touched, key=int)
    extra = sorted(touched - allp, key=int)
    if miss or extra:
        raise SystemExit(f"✗ 腳位未處理 {miss}　表外腳號 {extra}")
    print(f"  ✓ U7 的 {len(allp)} 支腳全部有去處")

    p.commit("⚠ HDMI 座、5V 保險絲、HPD 串接電阻在 hdmi.kicad_sch")


if __name__ == "__main__":
    main()
