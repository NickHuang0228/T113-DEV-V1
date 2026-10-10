#!/usr/bin/env python3
"""生成儲存頁：microSD（主要開機）+ SPI NOR 16MB（備援）+ BOOT-SEL strap。

資料來源
  004-usb-boot.md §4（SD 主力 / FEL 診斷 / NOR 備援，三條路互相獨立）
  007-pinmap.md   §5.2（PF2/PF4 的 UART0 分支）· §5.3（PC4/PC5 同時是 BOOT-SEL）
  MangoPi MQ-R 原理圖 p.3 —— BOOT-SEL 的真值表與實際接法（見下）

★ 這一頁解掉 007 §5.3 擱置的問題：BOOT-SEL 到底要怎麼接。

  MangoPi MQ-R 的原理圖上直接印了真值表：

      SEL[1:0]
        00:  NOR > NAND
        01:  SD  > NOR  > Other
      √ 10:  SD  > NAND > Other
        11:  SD0 > EMMC2 > EMMC2_USR > Other

  而它的接法是（PDF p.3 實圖核對過，不是從文字抽取猜的）：

      VCC3V3 ─┬─ R75 10K  ─ SPI0_MISO ─ R76 NC   ─┬─ GND
              └─ R77 NC   ─ SPI0_MOSI ─ R78 10K  ─┘
      → SEL1=1, SEL0=0 → 10 → SD > NAND

  本板有 SD + SPI NOR，沒有 NAND，所以要的是 **01 = SD > NOR > Other**，
  剛好跟 MangoPi 左右對調：

      SPI0_MISO (PC5, BOOT-SEL1)  10K 下拉  → 0
      SPI0_MOSI (PC4, BOOT-SEL0)  10K 上拉  → 1

  兩個位置都留焊盤、只焊一顆（照抄 MangoPi 的畫法）——
  改 boot order 不必飛線，而 strap 是「上電那一刻」的事，改不了就是改不了。

★ 同時也解掉 004 §7 的「FEL 按鍵接哪一支腳」：
  本板不需要專用 FEL 腳。SEL=01 時 BROM 依序試 SD → NOR → Other，
  兩個都失敗就落到 USB FEL。要強制進 FEL，把 SEL0 拉低變成 00（NOR > NAND）
  且 NOR 是空的即可 —— FEL 按鍵畫在 usb 頁（SW2，1K 對 GND，壓贏 10K 上拉）。

用法：python hardware/scripts/gen_storage_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "storage.kicad_sch")

SD = "Connector:Micro_SD_Card_Det1"
SD_FP = "Connector_Card:microSD_HC_Hirose_DM3D-SF"
NOR = "Memory_Flash:W25Q128JVS"
NOR_FP = "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm"

JX, JY = 95.25, 76.2          # microSD
UX, UY = 266.7, 76.2          # SPI NOR

# microSD：符號左側 dx = -22.86，原理圖 y = JY - dy
SD_LEFT = [("1", 10.16, "SDC0_D2"), ("2", 7.62, "SDC0_D3"),
           ("3", 5.08, "SDC0_CMD"), ("5", 0.0, "SDC0_CLK"),
           ("7", -5.08, "SDC0_D0"), ("8", -7.62, "SDC0_D1"),
           ("9", -12.7, "SDC0_DET")]
SD_RAIL = [("4", 2.54, "+3V3"), ("6", -2.54, "GND")]

# SPI NOR：符號左側 dx = -10.16
NOR_LEFT = [("1", 7.62, "SPI0_CS0"), ("6", 5.08, "SPI0_CLK"),
            ("5", 2.54, "SPI0_MOSI"), ("2", 0.0, "SPI0_MISO"),
            ("3", -2.54, "SPI0_WP"), ("7", -5.08, "SPI0_HOLD")]


def main():
    p = Page(SCH, ROOT)

    # ── J7  microSD ───────────────────────────────────
    p.part(SD, "J7", "microSD", JX, JY, 0, SD_FP, 1,
           [str(n) for n in range(1, 10)] + ["SH"],
           "microSD 卡座，含卡片偵測", ref_dy=-20.32, val_dy=20.32)
    for _, dy, net in SD_LEFT:
        p.pin_label(JX - 22.86, JY - dy, "L", net)
    for i, (_, dy, net) in enumerate(SD_RAIL):
        p.pin_rail(JX - 22.86, JY - dy, "L", net, stub=20.32 + i * 5.08)
    # 外殼接地：卡座金屬殼是手會碰到的地方，不接地等於放一根天線
    p.pin_rail(JX + 20.32, JY + 12.7, "R", "GND")
    p.stat["microSD"] = len(SD_LEFT) + len(SD_RAIL) + 1

    p.cap_bank(57.15, 120.65, [("C40", "10uF", "Capacitor_SMD:C_0805_2012Metric"),
                               ("C41", "100nF", None)], "+3V3")
    p.stat["SD 去耦"] = 2

    # ── SD 匯流排上拉 ─────────────────────────────────
    # SD 規範要求 CMD 與 DAT 線都有上拉。T113 內部有，但外部這一組的作用是
    # 「沒插卡 / 卡還沒初始化」時把線定義住 —— 否則 CMD 浮接會讀到隨機值。
    p.strap_bank(177.8, 50.8, [
        ("SDC0_CMD", "R79", "10K", "+3V3"),
        ("SDC0_D0",  "R80", "10K", "+3V3"),
        ("SDC0_D1",  "R81", "10K", "+3V3"),
        ("SDC0_D2",  "R82", "10K", "+3V3"),
        ("SDC0_D3",  "R83", "10K", "+3V3"),
        ("SDC0_DET", "R84", "10K", "+3V3"),
    ])
    p.stat["SD 上拉"] = 6

    # SDC0_DET 沒有 SoC 腳可用（PG bank 已經全部配完），
    # 所以拉到測試點。要用的時候從 TP12 飛一條線到排針的 GPIO。
    # dts 在那之前寫 broken-cd 即可。
    p.w(177.8 - 7.62, 127.0, 177.8 - 7.62 + 7.62, 127.0)
    p.lab("SDC0_DET", 170.18, 127.0, left=True)
    p.part("Connector:TestPoint", "TP12", "TP", 177.8, 127.0, 270,
           "TestPoint:TestPoint_Pad_D1.5mm", 1, ("1",),
           "測試點：microSD 卡片偵測", ref_dy=-2.54, val_dy=2.54,
           ref_dx=7.62, val_dx=7.62)
    p.stat["卡片偵測測試點"] = 1

    # ── U10  SPI NOR ──────────────────────────────────
    p.part(NOR, "U10", "W25Q128JVSIQ", UX, UY, 0, NOR_FP, 1,
           [str(n) for n in range(1, 9)],
           "16MB SPI NOR Flash，備援開機裝置", ref_dy=-17.78, val_dy=17.78)
    for _, dy, net in NOR_LEFT:
        p.pin_label(UX - 10.16, UY - dy, "L", net)
    p.w(UX, UY - 12.7, UX, UY - 17.78)
    p.rail("+3V3", UX, UY - 17.78)
    p.w(UX, UY + 12.7, UX, UY + 17.78)
    p.rail("GND", UX, UY + 17.78)
    p.cap_bank(247.65, 120.65, [("C42", "100nF", None)], "+3V3")
    p.stat["SPI NOR"] = len(NOR_LEFT) + 2 + 1

    # ── BOOT-SEL strap ────────────────────────────────
    p.strap_pair(266.7, 190.5, "SPI0_MISO",
                 up=("R85", "10K"), dn=("R86", "10K"), fitted="dn")
    p.strap_pair(327.66, 190.5, "SPI0_MOSI",
                 up=("R87", "10K"), dn=("R88", "10K"), fitted="up")
    p.stat["BOOT-SEL strap"] = 2

    p.note("BOOT-SEL（PC4 / PC5 上電瞬間的電平，來源：MangoPi MQ-R 原理圖 p.3）",
           228.6, 227.33, 1.778)
    p.note("SEL[1:0]   00: NOR > NAND", 228.6, 234.95)
    p.note("           01: SD  > NOR  > Other     <- 本板（有 SD、有 NOR、沒有 NAND）",
           228.6, 240.03)
    p.note("           10: SD  > NAND > Other     <- MangoPi MQ-R 用這個", 228.6, 245.11)
    p.note("           11: SD0 > EMMC2 > EMMC2_USR > Other", 228.6, 250.19)
    p.note("SEL1 = SPI0_MISO (PC5) = 0   -> R86 焊、R85 不焊", 228.6, 260.35)
    p.note("SEL0 = SPI0_MOSI (PC4) = 1   -> R87 焊、R88 不焊", 228.6, 265.43)
    p.note("★ 兩個位置都留焊盤：strap 改設定要動焊接，不留位置就得飛線。",
           228.6, 262.89)
    p.note("★ 不需要專用 FEL 腳：SD 與 NOR 都失敗時 BROM 自己落到 USB FEL。",
           228.6, 267.97)
    p.note("   要強制進 FEL 就把 SEL0 拉低變 00（usb 頁的 SW2）。", 228.6, 273.05)

    p.note("⚠ PC4 / PC5 一腳兩用：上電時是 BOOT-SEL，之後才切成 SPI0 的 MOSI/MISO。",
           25.4, 160.02, 1.778)
    p.note("   量測 strap 電平要抓上電那一刻，不是穩態 —— 穩態量到的是 SPI 波形。",
           25.4, 167.64)
    p.note("⚠ PF2(SDC0_CLK) / PF4(SDC0_D3) 另有 0Ω 分支到 CH340N 當 UART0 console，",
           25.4, 177.8)
    p.note("   見 usb 頁。SD 跑不穩時先拆那兩顆 0Ω 定位（007 §5.2）。", 25.4, 185.42)

    p.commit()


if __name__ == "__main__":
    main()
