#!/usr/bin/env python3
"""生成網路頁：RTL8201F + HR911105A（含變壓器的 RJ45）+ 25MHz 晶振。

資料來源
  003-network.md              REF_CLK 方向定案、strap 配置、隔離
  RTL8201F Datasheet Rev1.4   §5.1 Figure 3 腳位、Table 1 strap 預設值
  KiCad Connector.kicad_sym   RJ45_Hanrun_HR911105A_Horizontal 的腳位對應

★ 整頁最關鍵的一顆被動件是 R41（RXDV / pin 8 的 4.7K 上拉）：
  RTL8201F 內部是弱下拉 = 預設 MII 模式。本板只拉了 RMII 的七條線，
  MII 要的 TXD[3:2] / RXD[3:2] / TXC / RXC 根本沒接到 T113 ——
  漏掉這顆上拉，PHY 停在 MII 模式，板子完全不通。
  而原理圖上看不出任何異常（所有線都接得好好的），要到 bring-up 才發現。

  同一類的還有三顆：
    R42  pin 12 CLK_CTL → GND   REF_CLK 由 PHY 提供（50MHz 從 TXC 出）
    R44  RMII_RXER      → GND   FXEN=0，銅線模式（不是光纖）
    R43  RMII_MDIO      → +3V3  MDIO 是開汲極，沒上拉讀不到暫存器
  這四顆的共通點：接錯或漏掉都不會燒件，但板子不會動。

用法：python hardware/scripts/gen_net_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page, snap

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "net.kicad_sch")

PHY_LIB = "T113-DEV-V1-rtl8201f:RTL8201F"
PHY_FP = "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias"
RJ_LIB = "Connector:RJ45_Hanrun_HR911105A_Horizontal"
RJ_FP = "Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal"
PINX = 27.94                     # RTL8201F 符號：WIDTH/2 + PIN_LEN = 22.86 + 5.08

# ── RTL8201F 三個 unit 的腳位排列 ───────────────────────
# 必須與 gen_rtl8201f_symbol.py 的 UNITS 同序，否則算出來的座標對不上腳。
U1_PINS = [("14", "L"), ("30", "L"), ("7", "L"), ("33", "L"), ("1", "L"), ("31", "L"),
           ("29", "R"), ("2", "R"), ("32", "R"),
           ("3", "R"), ("4", "R"), ("5", "R"), ("6", "R")]
U2_PINS = [("20", "L"), ("19", "L"), ("18", "L"), ("17", "L"), ("16", "L"),
           ("15", "L"), ("22", "L"), ("23", "L"), ("21", "L"),
           ("8", "R"), ("9", "R"), ("10", "R"), ("11", "R"), ("12", "R"), ("13", "R")]
U3_PINS = [("24", "R"), ("25", "R"), ("26", "R"), ("27", "R"), ("28", "R")]

AT = {1: (95.25, 63.5), 2: (95.25, 152.4), 3: (95.25, 238.76)}


def pin_map(pins, origin):
    """算出每支腳的原理圖座標。符號生成器的排法：左右各自由上往下，間距 2.54。"""
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


P1 = pin_map(U1_PINS, AT[1])
P2 = pin_map(U2_PINS, AT[2])
P3 = pin_map(U3_PINS, AT[3])
ALL = {**P1, **P2, **P3}

# ── 這頁的 net 名稱（已與 mcu.kicad_sch 的 11 條 RMII 標籤逐字核對）──
SIGNALS = {
    "20": "RMII_TX_EN",  "17": "RMII_TXD1",  "16": "RMII_TXD0",
    "15": "RMII_REF_CLK",                      # ★ PHY 輸出 50MHz 給 T113 PE3
    "22": "RMII_MDC",    "23": "RMII_MDIO",   "21": "PHY_RESET_N",
    "9": "RMII_RXD0",    "10": "RMII_RXD1",
    "26": "RMII_CRS_DV", "28": "RMII_RXER",
    "24": "PHY_LED0",    "25": "PHY_LED1",
    "31": "XTAL_IN",     "32": "XTAL_OUT",
    "3": "MDI0_P", "4": "MDI0_N", "5": "MDI1_P", "6": "MDI1_N",
}
RAILS = {"14": "+3V3", "30": "+3V3", "7": "+3V3", "33": "GND"}
LDO_OUT = {"29": "DVDD10", "2": "AVDD10"}      # 內部 LDO 輸出，不是板級電源軌
INLINE_STRAP = {
    # 腳號: (ref, 阻值, 接到哪條軌, 電阻往上還是往下)
    "8":  ("R41", "4.7K", "+3V3", True),       # ★ RMII 模式選擇
    "12": ("R42", "4.7K", "GND", False),       # REF_CLK 由 PHY 提供
}
# MII 專用、RMII 用不到，且不是 strap 的腳
NC_PINS = ["19", "18", "13", "11", "27"]


def main():
    p = Page(SCH, ROOT)

    def place(unit, pins, desc):
        p.part(PHY_LIB, "U8", "RTL8201F-VB-CG", *AT[unit], 0, PHY_FP, unit,
               [n for n, _ in pins], desc, ref_dy=-20.32, val_dy=20.32)

    # ── unit 1  電源與類比 ──────────────────────────────
    place(1, U1_PINS, "RTL8201F 電源與類比")
    # 三支 +3V3 走一條匯流排 —— 三個電源符號擠在 2.54mm 裡文字會疊
    p.pin_bus([(P1[n][0], P1[n][1]) for n in ("14", "30", "7")], "L", "+3V3")
    x, y, s = P1["33"]
    p.pin_rail(x, y, s, "GND")
    # RSET：1% 參考電阻，決定 MDI 驅動電流。漏了或換成 5% 的，鏈路跑不起來。
    x, y, s = P1["1"]
    p.pin_res_rail(x, y, s, "R40", "2.49K 1%", "GND")
    for n in ("31", "32", "3", "4", "5", "6"):
        x, y, s = P1[n]
        p.pin_label(x, y, s, SIGNALS[n])
    for n, net in LDO_OUT.items():
        x, y, s = P1[n]
        p.pin_label(x, y, s, net)
    p.stat["unit1 電源/類比"] = len(RAILS) + 1 + 6 + 2

    # ── unit 2  MII/RMII ───────────────────────────────
    place(2, U2_PINS, "RTL8201F MII/RMII")
    n2 = 0
    for n in ("20", "17", "16", "15", "22", "23", "21", "9", "10"):
        x, y, s = P2[n]
        p.pin_label(x, y, s, SIGNALS[n])
        n2 += 1
    for n, (ref, val, rk, up) in INLINE_STRAP.items():
        x, y, s = P2[n]
        p.pin_res_rail_v(x, y, s, ref, val, rk, up=up)
        n2 += 1
    for n in NC_PINS:
        if n in P2:
            x, y, _ = P2[n]
            p.nc(x, y)
            n2 += 1
    p.stat["unit2 RMII"] = n2

    # ── unit 3  LED 與 strap ───────────────────────────
    place(3, U3_PINS, "RTL8201F LED 與 strap")
    n3 = 0
    for n in ("24", "25", "26", "28"):
        x, y, s = P3[n]
        p.pin_label(x, y, s, SIGNALS[n])
        n3 += 1
    x, y, _ = P3["27"]
    p.nc(x, y)
    p.stat["unit3 LED/strap"] = n3 + 1

    # ── 掛在已命名訊號上的上下拉 ────────────────────────
    p.strap_bank(177.8, 114.3, [
        ("RMII_MDIO", "R43", "4.7K", "+3V3"),   # 開汲極，沒上拉讀不到 PHY 暫存器
        ("RMII_RXER", "R44", "4.7K", "GND"),    # FXEN=0 → 銅線模式
        ("PHY_LED0",  "R45", "4.7K", "+3V3"),   # PHYAD[0]=1
        ("PHY_LED1",  "R46", "4.7K", "+3V3"),   # PHYAD[1]=1  → PHY 位址 = 3
    ])
    p.stat["訊號端 strap"] = 4

    # ── 25MHz 晶振 ─────────────────────────────────────
    # CKXTAL1=輸入、CKXTAL2=輸出。PHY 自帶振盪器，50MHz REF_CLK 由它倍頻後
    # 從 TXC 送給 T113 —— 所以 T113 那邊不需要再給時鐘。
    cx, cy = 203.2, 63.5
    p.part("Device:Crystal_GND24", "Y1", "25MHz", cx, cy, 0,
           "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", 1, ("1", "2", "3", "4"),
           "Two pin crystal, GND on pins 2 and 4", ref_dy=-8.89, val_dy=-6.35)
    p.w(cx - 3.81, cy, cx - 17.78, cy)
    p.lab("XTAL_IN", cx - 17.78, cy, left=True)
    p.w(cx + 3.81, cy, cx + 17.78, cy)
    p.lab("XTAL_OUT", cx + 17.78, cy)
    p.w(cx, cy + 5.08, cx, cy + 7.62)
    p.rail("GND", cx, cy + 7.62)
    # 負載電容：22pF 是對應 20pF 負載的晶振 + 約 5pF 板上寄生。
    # 換晶振要重算，這是唯一會讓 PHY「時而能通時而不能」的地方。
    # 兩顆負載電容要離開 7.62mm 以上，否則 ref/value 文字會互相蓋
    for ref, lx in (("C59", cx - 12.7), ("C60", cx + 12.7)):
        p.w(lx, cy, lx, cy + 8.89)
        p.cap(ref, "22pF", lx, cy + 12.7, 0)
        p.w(lx, cy + 16.51, lx, cy + 19.05)
        p.rail("GND", lx, cy + 19.05)
    p.j(cx - 12.7, cy)
    p.j(cx + 12.7, cy)
    p.stat["晶振"] = 5

    # ── 去耦 ───────────────────────────────────────────
    p.cap_bank(57.15, 100.33, [("C49", "10uF", None), ("C50", "100nF", None),
                               ("C51", "100nF", None), ("C52", "100nF", None)],
               "+3V3")
    p.cap_bank(133.35, 100.33, [("C53", "10uF", None), ("C54", "100nF", None)],
               "DVDD10", top_label=True)
    p.cap_bank(171.45, 100.33, [("C55", "10uF", None), ("C56", "100nF", None)],
               "AVDD10", top_label=True)
    p.stat["去耦電容"] = 8

    # ── J2  RJ45（含變壓器）───────────────────────────
    # 用含磁性元件的 MagJack，所以板上不需要另畫變壓器。
    # 中心抽頭接 +3V3：RTL8201F 的 MDI 是電流模式驅動，從中心抽頭取電。
    jx, jy = 304.8, 152.4
    p.part(RJ_LIB, "J2", "HR911105A", jx, jy, 0, RJ_FP, 1,
           ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "SH"),
           "RJ45 MagJack 10/100, 內含變壓器與兩顆 LED", ref_dy=-15.24, val_dy=15.24)
    for dy, net in ((7.62, "MDI0_P"), (2.54, "MDI0_N"),
                    (0.0, "MDI1_P"), (-5.08, "MDI1_N")):
        p.pin_label(jx - 20.32, jy - dy, "L", net)
    # TCT/RCT 的 +3V3 要比 MDI 標籤再往左，不然兩種文字會疊
    p.pin_bus([(jx - 20.32, jy - 5.08)], "L", "+3V3", 12.7, 5.08)
    p.pin_bus([(jx - 20.32, jy + 2.54)], "L", "+3V3", 17.78, 5.08)
    # pin 8 與 SH 都當機殼地 —— 它們在符號上都畫在連接器下緣。
    # 兩支都接機殼地，但符號不能並排 —— GND_CHASSIS 這串字比符號寬得多
    p.w(jx + 10.16, jy + 10.16, jx + 10.16, jy + 15.24)
    p.w(jx + 15.24, jy + 10.16, jx + 15.24, jy + 22.86)
    p.rail("GND_CHASSIS", jx + 10.16, jy + 15.24)
    p.rail("GND_CHASSIS", jx + 15.24, jy + 22.86)
    # 兩顆 LED：陽極經 330R 到 +3V3，陰極由 PHY 下沉點亮。
    for ref, dy in (("R47", 7.62), ("R48", -2.54)):
        p.pin_res_rail(jx + 22.86, jy - dy, "R", ref, "330R", "+3V3", stub=12.7)
    for dy, net in ((5.08, "PHY_LED0"), (-5.08, "PHY_LED1")):
        p.pin_label(jx + 22.86, jy - dy, "R", net, stub=15.24)
    p.stat["RJ45"] = 4 + 2 + 2 + 2 + 2

    # 中心抽頭的去耦：擺在連接器旁邊，是這兩顆電容唯一的作用。
    p.cap_bank(287.02, 190.5, [("C57", "100nF", None), ("C58", "100nF", None)],
               "+3V3")
    p.stat["中心抽頭去耦"] = 2

    # ── 機殼地與系統地的隔離 ───────────────────────────
    # 不直接短接：乙太網線會把外界的突波與共模雜訊帶進來。
    # 1nF/2kV 給高頻一條回路，1M 把電荷洩掉避免浮接累積靜電。
    ix, iy = 304.8, 215.9
    p.cap("C61", "1nF 2kV", ix - 6.35, iy, 0,
          "Capacitor_SMD:C_1206_3216Metric")
    p.res("R49", "1M", ix + 6.35, iy, 0)
    p.w(ix - 6.35, iy - 3.81, ix + 6.35, iy - 3.81)
    p.w(ix - 6.35, iy + 3.81, ix + 6.35, iy + 3.81)
    # T 形接點一定要放 junction —— 線頭落在另一條線的「中間」時，
    # KiCad 不會自動連，而圖上看起來是連著的。
    p.j(ix, iy - 3.81)
    p.j(ix, iy + 3.81)
    p.w(ix, iy - 3.81, ix, iy - 6.35)
    p.rail("GND_CHASSIS", ix, iy - 6.35)
    p.w(ix, iy + 3.81, ix, iy + 6.35)
    p.rail("GND", ix, iy + 6.35)
    # 機殼地只經過一顆電容與一顆電阻，ERC 認為沒人驅動
    p.pwr_flag("GND_CHASSIS", ix + 25.4, iy)
    p.stat["地隔離"] = 2

    # ── 收尾前先確認 33 支腳一支都沒漏 ──────────────────
    touched = (set(RAILS) | set(LDO_OUT) | set(INLINE_STRAP) | set(NC_PINS)
               | {"1"} | {"31", "32", "3", "4", "5", "6"}
               | {"20", "17", "16", "15", "22", "23", "21", "9", "10"}
               | {"24", "25", "26", "28", "27"})
    missing = sorted(set(ALL) - touched, key=int)
    extra = sorted(touched - set(ALL), key=int)
    if missing or extra:
        raise SystemExit(f"✗ 腳位未處理 {missing}　表外腳號 {extra}")
    print(f"  ✓ U8 的 {len(ALL)} 支腳全部有去處（含 E-Pad 與五顆 strap）")

    p.commit("⚠ 待確認：J2 的 LED 極性（pin 9/12 當陽極）—— "
             "接反只是不亮，但要核對 HanRun datasheet 再投板")


if __name__ == "__main__":
    main()
