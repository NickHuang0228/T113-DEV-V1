#!/usr/bin/env python3
"""生成 HDMI 座頁：HDMI Type-A 母座 + 5V 供電 + HPD 串接。

為什麼單獨一頁：ADV7511 的 100 腳已經吃掉整張 A3。
接頭另開一頁，佈線時可以只看這一頁處理「板邊」的事
（TMDS 等長、接頭機構、5V 保險絲位置）。

資料來源
  002-display.md §3.3（TMDS 差分規則）· §3.4（DDC 與 HPD）
  ADV7511KSTZ_extracted.md §3.4（HPD 1.8~5.0V CMOS，所以不需要分壓）
  KiCad Connector:HDMI_A 的腳位對應

★ V1 不放 TMDS 的 ESD 保護，這是刻意的取捨，理由寫在圖紙註記裡。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "hdmi.kicad_sch")

JX, JY = 190.5, 152.4

# 腳號: (符號座標 dx, 符號座標 dy)　—— 原理圖座標 = (JX+dx, JY-dy)
LEFT = {
    "1":  (20.32,  "TMDS_D2_P"), "3":  (17.78, "TMDS_D2_N"),
    "4":  (15.24,  "TMDS_D1_P"), "6":  (12.7,  "TMDS_D1_N"),
    "7":  (10.16,  "TMDS_D0_P"), "9":  (7.62,  "TMDS_D0_N"),
    "10": (5.08,   "TMDS_CK_P"), "12": (2.54,  "TMDS_CK_N"),
    "15": (-7.62,  "HDMI_DDC_SCL"), "16": (-10.16, "HDMI_DDC_SDA"),
}
LEFT_NC = {"13": -2.54, "14": -15.24}      # CEC（V1 不做）、UTILITY
GND_BOTTOM = {"2": -5.08, "5": -2.54, "8": 0.0, "11": 2.54,
              "17": 5.08, "SH": 7.62}      # 四組 TMDS 屏蔽 + DDC 地 + 外殼


def main():
    p = Page(SCH, ROOT)
    p.part("Connector:HDMI_A", "J1", "HDMI_A", JX, JY, 0,
           "Connector_Video:HDMI_A_Amphenol_10029449-x01xLF_Horizontal", 1,
           [str(n) for n in range(1, 20)] + ["SH"],
           "HDMI Type-A 母座", ref_dy=-35.56, val_dy=35.56)

    # ── TMDS 四對 + DDC ───────────────────────────────
    for num, (dy, net) in LEFT.items():
        p.pin_label(JX - 10.16, JY - dy, "L", net)
    for num, dy in LEFT_NC.items():
        p.nc(JX - 10.16, JY - dy)
    p.stat["TMDS + DDC"] = len(LEFT)
    p.stat["刻意不接"] = len(LEFT_NC)

    # ── HPD：不需要分壓 ───────────────────────────────
    # ADV7511 的 HPD 腳規格是 1.8~5.0V CMOS，HDMI 的 HPD 最高 5.3V 也在範圍內。
    # 串 1K 只是限制故障與 ESD 的灌入電流；未插線時的低準位由
    # display 頁的 R70（100K 下拉）定義。
    hx, hy = JX - 10.16, JY + 17.78
    p.w(hx, hy, hx - 7.62, hy)
    p.res("R78", "1K", hx - 11.43, hy, 90)
    p.w(hx - 15.24, hy, hx - 22.86, hy)
    p.lab("HDMI_HPD", hx - 22.86, hy, left=True)
    p.stat["HPD"] = 1

    # ── 屏蔽與地：走一條匯流排，只放一顆接地符號 ────
    ys = JY + 27.94
    xs = sorted(JX + dx for dx in GND_BOTTOM.values())
    for x in xs:
        p.w(x, ys, x, ys + 5.08)
    p.w(xs[0], ys + 5.08, xs[-1], ys + 5.08)
    for x in xs[1:-1]:
        p.j(x, ys + 5.08)
    p.w(JX, ys + 5.08, JX, ys + 10.16)
    p.rail("GND", JX, ys + 10.16)
    p.stat["屏蔽與地"] = len(GND_BOTTOM)

    # ── 板子供給 sink 的 +5V ──────────────────────────
    # HDMI 規範要求 source 至少供 55mA 給 sink 的 EDID EEPROM。
    # 加保險絲是因為 HDMI 線短路或對端異常不該把板子的 5V 拉掛。
    p.w(JX, JY - 27.94, JX, JY - 33.02)
    p.lab("HDMI_5V", JX, JY - 33.02)
    p.w(76.2, 124.46, 83.82, 124.46)
    p.rail("+5V_VBUS", 76.2, 124.46)
    p.part("Device:Polyfuse", "F1", "500mA", 87.63, 124.46, 90,
           "Fuse:Fuse_1206_3216Metric", desc="Resettable fuse",
           ref_dy=-3.81, val_dy=3.81)
    p.w(91.44, 124.46, 99.06, 124.46)
    p.rail("HDMI_5V", 99.06, 124.46)
    p.cap_bank(76.2, 148.59, [("C38", "10uF", "Capacitor_SMD:C_0805_2012Metric"),
                              ("C39", "100nF", None)], "HDMI_5V")
    p.pwr_flag("HDMI_5V", 110.49, 124.46)
    p.stat["5V 供電"] = 4

    # ── 寫在圖紙上的 layout 規則 ──────────────────────
    p.note("TMDS layout（002-display.md §3.3）", 25.4, 190.5, 1.778)
    p.note("· 100 ohm 差分，對內等長 ±0.15mm，對 CK 等長 ±0.5mm", 25.4, 196.85)
    p.note("· 1080p60 = 1.485 Gbps/pair，上升時間約 250ps", 25.4, 201.93)
    p.note("  -> 臨界長度約 4.7mm，接頭到 U7 全程都要當傳輸線處理", 25.4, 207.01)
    p.note("· 全程走在完整 GND 平面上方，不跨分割", 25.4, 212.09)

    p.note("★ V1 刻意不放 TMDS 的 ESD 保護", 25.4, 227.33, 1.778)
    p.note("理由（三條都成立才敢省）：", 25.4, 233.68)
    p.note("① TMDS 要求 ESD 元件電容 <1pF，符合的只有 0201 單線件", 25.4, 238.76)
    p.note("   （如 ESD131-B1-W0201）—— 超出本板手焊的能力", 25.4, 243.84)
    p.note("② 在 TMDS 走線上留「不焊的焊盤」本身就是 stub，比不放更糟", 25.4, 248.92)
    p.note("③ 只保護慢速線（HPD/DDC/CEC）會造成「有保護」的錯覺", 25.4, 254.0)
    p.note("V2 待辦：改用整合式 HDMI ESD 陣列，placement 階段就留位置", 25.4, 259.08)

    p.commit()


if __name__ == "__main__":
    main()
