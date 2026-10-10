#!/usr/bin/env python3
"""生成 USB / 開機頁：Type-C ×2 + CH340N + USB-A Host + RESET / FEL 按鍵。

資料來源
  004-usb-boot.md §1（三個接口的角色）· §2（Type-C sink）· §5（CH340N）
                  §6（USB HS 差分規則）· §7（按鍵）
  007-pinmap.md   §5.2（UART0 沒有獨立腳位，用 2 顆 0Ω 從 SDC0 分支）
  MangoPi MQ-R 原理圖 p.3（BOOT-SEL 真值表，見 gen_storage_sheet.py）

三個 USB 接口各有不同角色，不要搞混：
  J4  Type-C #1  OTG + FEL 燒錄   → T113 的 USB0（USB0_DP/DM）
  J5  Type-C #2  UART0 console    → CH340N，再轉 UART0
  J6  USB-A      Host             → T113 的 USB1，供 WiFi dongle 與 UVC 攝影機

★ UART0 沒有自己的腳位（007 §5.2）。
  Table 4-3 裡 UART0 只有 PE2/PE3 與 PF2/PF4 兩組 mux，兩組都撞到別人。
  選 PF2/PF4，用 2 顆 0Ω 從 SDC0_CLK / SDC0_D3 分支到 CH340N ——
  這兩個功能在時間上本來就不重疊：

      BROM 階段     PF2/PF4 = UART0   印開機 log      ← CH340N 收得到
      切到 SD 讀卡   PF2/PF4 = SDC0    跑 50MHz 時脈   ← CH340N 收到亂碼（正常）
      Linux 起來後   console 改用 UART1

  0Ω 的作用是「必要時能完全斷開」：CH340N 的輸入電容掛在 50MHz 的 SDC0_CLK 上，
  SD 跑不穩時先拆這兩顆定位。⚠ 焊盤距主幹 ≤0.5mm，與 PD0~PD9 那 10 顆同規則。

★ FEL 按鍵（解掉 004 §7 的待確認項）
  本板不需要專用 FEL 腳。BOOT-SEL = 01 時 BROM 依序試 SD → NOR → Other，
  兩個都失敗就落到 USB FEL。SW2 把 SEL0（SPI0_MOSI / PC4）用 1K 拉到 GND，
  壓贏 storage 頁的 10K 上拉 → 上電瞬間變成 00（NOR > NAND），
  NOR 是空的、又沒有 NAND，於是直接進 FEL。

用法：python hardware/scripts/gen_usb_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "usb.kicad_sch")

TYPEC = "Connector:USB_C_Receptacle_USB2.0_16P"
TYPEC_FP = "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A"
TYPEC_PINS = ["A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
              "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12", "SH"]
ESD = "Power_Protection:USBLC6-2SC6"
ESD_FP = "Package_TO_SOT_SMD:SOT-23-6"
SW_FP = "Button_Switch_SMD:SW_SPST_B3U-1000P-B"


def type_c(p, ref, x, y, dp, dm, cc_refs, vbus="+5V_VBUS"):
    """一顆 USB2.0-only 的 Type-C 母座。

    ⚠ 兩個 CC 腳各要一顆 5.1k 下拉 —— Type-C 可正反插，
      插反了只有另一個 CC 在作用，少一顆就有一半機率不供電。
    ⚠ A6/B6（D+）與 A7/B7（D-）必須各自短接 —— USB2.0-only 的接法，
      不短接的話插反了就沒有資料線。
    """
    p.part(TYPEC, ref, "USB-C 16P", x, y, 0, TYPEC_FP, 1, TYPEC_PINS,
           "USB 2.0 Type-C 母座", ref_dy=-27.94, val_dy=27.94)
    px = x + 15.24
    p.pin_rail(px, y - 15.24, "R", vbus)                 # A4/A9/B4/B9 疊在一起
    p.pin_rail(x, y + 22.86, "R", "GND", stub=5.08)      # A1/A12/B1/B12
    p.w(x - 7.62, y + 22.86, x - 7.62, y + 27.94)        # 外殼
    p.rail("GND", x - 7.62, y + 27.94)
    for i, (dy, ref_r) in enumerate(((10.16, cc_refs[0]), (7.62, cc_refs[1]))):
        p.pin_res_rail_v(px, y - dy, "R", ref_r, "5.1K", "GND",
                         stub=22.86 + i * 5.08, up=False)
    # D-：A7 (dy=-2.54) 與 B7 (dy=0) 短接後拉出去
    p.w(px, y + 2.54, px + 7.62, y + 2.54)
    p.w(px, y, px + 7.62, y)
    p.w(px + 7.62, y, px + 7.62, y + 2.54)
    p.j(px + 7.62, y + 2.54)
    p.w(px + 7.62, y + 2.54, px + 15.24, y + 2.54)
    p.lab(dm, px + 15.24, y + 2.54)
    # D+：A6 (dy=-5.08) 與 B6 (dy=-7.62) 短接
    p.w(px, y + 5.08, px + 12.7, y + 5.08)
    p.w(px, y + 7.62, px + 12.7, y + 7.62)
    p.w(px + 12.7, y + 5.08, px + 12.7, y + 7.62)
    p.j(px + 12.7, y + 7.62)
    p.w(px + 12.7, y + 7.62, px + 15.24, y + 7.62)
    p.lab(dp, px + 15.24, y + 7.62)
    # SBU 不用（本板不做 DP Alt Mode）
    p.nc(px, y - 12.7)
    p.nc(px, y - 15.24 + 30.48)


def esd(p, ref, x, y, a_dp, a_dm, b_dp, b_dm):
    """USBLC6-2SC6 串在資料線上。左邊接接頭，右邊接晶片。

    004 §8 原本寫「電容 <1pF」；USBLC6-2SC6 是 1.5pF。
    放寬到 1.5pF 是刻意的：USB HS 480Mbps 對電容的容忍度遠高於
    TMDS 的 1.485Gbps，而 <1pF 的料只有 0201 單線件，手焊不了。
    （HDMI 那邊的同一個判斷走向相反結論 —— 見 hdmi 頁的註記。）
    """
    p.part(ESD, ref, "USBLC6-2SC6", x, y, 0, ESD_FP, 1,
           ["1", "2", "3", "4", "5", "6"],
           "低電容 ESD 保護，2 條資料線", ref_dy=-12.7, val_dy=12.7)
    p.w(x, y - 5.08, x, y - 10.16)
    p.rail("+5V_VBUS", x, y - 10.16)
    p.w(x, y + 7.62, x, y + 12.7)
    p.rail("GND", x, y + 12.7)
    for dx, net in ((-5.08, a_dp), (5.08, b_dp)):          # I/O1
        s = -1 if dx < 0 else 1
        p.w(x + dx, y, x + dx + s * 7.62, y)
        p.lab(net, x + dx + s * 7.62, y, left=(s < 0))
    for dx, net in ((-5.08, a_dm), (5.08, b_dm)):          # I/O2
        s = -1 if dx < 0 else 1
        p.w(x + dx, y + 2.54, x + dx + s * 7.62, y + 2.54)
        p.lab(net, x + dx + s * 7.62, y + 2.54, left=(s < 0))


def main():
    p = Page(SCH, ROOT)

    # ── J4  Type-C #1：OTG + FEL ──────────────────────
    type_c(p, "J4", 63.5, 63.5, "J4_DP", "J4_DM", ("R100", "R101"))
    esd(p, "D1", 152.4, 66.04, "J4_DP", "J4_DM", "USB0_DP", "USB0_DM")
    p.stat["Type-C #1"] = 8

    # ── J5  Type-C #2：UART0 console ──────────────────
    type_c(p, "J5", 63.5, 177.8, "J5_DP", "J5_DM", ("R102", "R103"))
    esd(p, "D2", 152.4, 180.34, "J5_DP", "J5_DM", "CH340_DP", "CH340_DM")
    p.stat["Type-C #2"] = 8

    # ── U9  CH340N ────────────────────────────────────
    ux, uy = 228.6, 177.8
    p.part("Interface_USB:CH340N", "U9", "CH340N", ux, uy, 0,
           "Package_SO:JEITA_SOIC-8_3.9x4.9mm_P1.27mm", 1,
           [str(n) for n in range(1, 9)],
           "USB 轉 UART，3.3V 介面", ref_dy=-15.24, val_dy=15.24)
    p.pin_label(ux - 10.16, uy + 2.54, "L", "CH340_DP")    # UD+ (dy=-2.54)
    p.pin_label(ux - 10.16, uy + 5.08, "L", "CH340_DM")    # UD- (dy=-5.08)
    # V3：3.3V 供電時這支要接到 VCC，再掛 0.1µF 到地（WCH 資料手冊的接法）
    p.w(ux - 10.16, uy - 2.54, ux - 17.78, uy - 2.54)
    p.rail("+3V3", ux - 17.78, uy - 2.54)
    p.w(ux, uy - 7.62, ux, uy - 12.7)
    p.rail("+3V3", ux, uy - 12.7)
    p.w(ux, uy + 10.16, ux, uy + 15.24)
    p.rail("GND", ux, uy + 15.24)
    p.pin_label(ux + 10.16, uy - 2.54, "R", "UART0_TX_CH")   # TXD → SoC RX
    p.pin_label(ux + 10.16, uy, "R", "UART0_RX_CH")          # RXD ← SoC TX
    p.nc(ux + 10.16, uy + 5.08)                              # RTS 不用
    p.cap_bank(203.2, 215.9, [("C50", "100nF", None), ("C51", "100nF", None)],
               "+3V3")
    p.stat["CH340N"] = 9

    # ── UART0 的兩顆 0Ω 分支 ──────────────────────────
    # 方向要對：PF2 = UART0-TX（SoC 輸出）→ CH340N 的 RXD
    #           PF4 = UART0-RX（SoC 輸入）← CH340N 的 TXD
    p.series_bank(292.1, 177.8, [
        ("SDC0_CLK", "R104", "0R", "UART0_RX_CH"),   # SoC TX → CH340N RXD
        ("SDC0_D3",  "R105", "0R", "UART0_TX_CH"),   # SoC RX ← CH340N TXD
    ], pitch=12.7)
    p.stat["UART0 分支"] = 2

    # ── J6  USB-A Host ────────────────────────────────
    jx, jy = 304.8, 69.85
    p.part("Connector:USB_A", "J6", "USB-A", jx, jy, 0,
           "Connector_USB:USB_A_Connfly_DS1095-BNR0", 1,
           ["1", "2", "3", "4", "SH"], "USB-A Host 母座",
           ref_dy=-15.24, val_dy=15.24)
    p.pin_rail(jx + 7.62, jy - 5.08, "R", "+5V_USB")
    p.w(jx, jy + 10.16, jx, jy + 15.24)
    p.rail("GND", jx, jy + 15.24)
    p.w(jx - 2.54, jy + 10.16, jx - 2.54, jy + 15.24)
    p.rail("GND", jx - 2.54, jy + 15.24)
    p.w(jx + 7.62, jy, jx + 15.24, jy)
    p.lab("J6_DP", jx + 15.24, jy)
    p.w(jx + 7.62, jy + 2.54, jx + 15.24, jy + 2.54)
    p.lab("J6_DM", jx + 15.24, jy + 2.54)
    esd(p, "D3", 243.84, 111.76, "USB1_DP", "USB1_DM", "J6_DP", "J6_DM")
    p.stat["USB-A Host"] = 6

    # USB_EN 預設上拉：TPS2051B 的 EN 是高有效，而 SoC 的 GPIO 上電時是高阻態。
    # 沒有這顆上拉，軟體跑起來之前 USB-A 完全沒電 —— 連 FEL 階段插隨身碟都不行。
    p.strap_bank(243.84, 142.24, [
        ("USB_EN", "R106", "100K", "+3V3"),
    ])
    # USB_OC_N 是 TPS2051B 的過流旗標（開汲極，上拉在電源頁的 R9）。
    # PG bank 已經配完，沒有 GPIO 可用，所以拉到測試點 ——
    # 失去的是「軟體讀得到過流」，不影響硬體保護本身（限流是 IC 內部做的）。
    p.w(236.22, 158.75, 243.84, 158.75)
    p.lab("USB_OC_N", 236.22, 158.75, left=True)
    p.part("Connector:TestPoint", "TP13", "USB_OC_N", 243.84, 158.75, 270,
           "TestPoint:TestPoint_Pad_D1.5mm", 1, ("1",),
           "測試點", ref_dy=-5.08, val_dy=-2.54)
    p.stat["USB 電源致能"] = 2

    # ── SW1 RESET ─────────────────────────────────────
    # 上拉已經在電源頁（APX803 的 R8），這裡只要一顆按鍵對地。
    sx, sy = 63.5, 241.3
    p.lab("SYS_RESET_N", sx - 12.7, sy, left=True)
    p.w(sx - 12.7, sy, sx - 5.08, sy)
    p.part("Switch:SW_Push", "SW1", "RESET", sx, sy, 0, SW_FP, 1, ("1", "2"),
           "輕觸開關", ref_dy=-6.35, val_dy=5.08)
    p.w(sx + 5.08, sy, sx + 12.7, sy)
    p.rail("GND", sx + 12.7, sy)

    # ── SW2 FEL ───────────────────────────────────────
    # 1K 對 GND，壓贏 storage 頁 R97 的 10K 上拉：
    #   按住上電 → SEL0 = 0 → BOOT-SEL 變 00（NOR > NAND）→ 都沒有 → USB FEL
    fx, fy = 63.5, 266.7
    p.lab("SPI0_MOSI", fx - 24.13, fy, left=True)
    p.w(fx - 24.13, fy, fx - 16.51, fy)
    p.res("R107", "1K", fx - 12.7, fy, 90)
    p.w(fx - 8.89, fy, fx - 5.08, fy)
    p.part("Switch:SW_Push", "SW2", "FEL", fx, fy, 0, SW_FP, 1, ("1", "2"),
           "輕觸開關", ref_dy=-6.35, val_dy=5.08)
    p.w(fx + 5.08, fy, fx + 12.7, fy)
    p.rail("GND", fx + 12.7, fy)
    p.stat["按鍵"] = 2

    # ── 圖紙註記 ──────────────────────────────────────
    p.note("USB 2.0 High Speed layout（004-usb-boot.md §6）", 134.62, 243.84, 1.778)
    p.note("· 90 ohm 差分，對內等長 ±0.15mm", 134.62, 250.19)
    p.note("· 480 Mbps -> 上升時間約 500ps -> 臨界長度約 12mm，必須控阻抗", 134.62, 255.27)
    p.note("· 三對都要認真做：WiFi dongle 與 UVC 攝影機都走 J6 那一對", 134.62, 260.35)
    p.note("· ESD 元件擺在接頭與晶片之間，貼近接頭", 134.62, 265.43)

    p.note("★ SW2 = FEL：按住上電把 BOOT-SEL0 拉低 -> 00（NOR > NAND）",
           134.62, 275.59, 1.778)
    p.note("   NOR 空的、沒有 NAND -> BROM 落到 USB FEL。1K 壓贏 storage 頁的 10K。",
           134.62, 281.94)
    p.note("★ R104 / R105 焊盤距 SDC0 主幹 <=0.5mm；SD 跑不穩先拆這兩顆。",
           134.62, 287.02)

    p.commit()


if __name__ == "__main__":
    main()
