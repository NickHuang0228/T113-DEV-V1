#!/usr/bin/env python3
"""生成排針頁：2×13 = 26 pin 擴充排針 + UART0 console 備援。

資料來源
  SPEC.md §（排針 26-pin 2×13，全部經限流電阻）
  007-pinmap.md §4（排針放 PG bank 的理由）· §6.1
  004-usb-boot.md §5（UART 排針備援）

★ 為什麼排針放 PG bank（007 §4）
  排針是全板最容易燒的地方 —— 手滑短路、接錯模組、熱插拔、外部電源倒灌。
      排針放 PB/PC/PF → 燒了同時失去 SD 開機 + NOR 開機 + UART log → 變磚
      排針放 PG       → 燒了只失去排針本身
  限流電阻（100R / 330R，畫在 mcu 頁）是同一個考量的延伸。

⚠ 與 SPEC 的差異：純 GPIO 從 10 支變成 7 支。
  PG12 / PG14 / PG4 改作 HDMI_INT_N / HDMI_PD / PANEL_RESET_N：
    HDMI_INT_N  ADV7511 的中斷輸出。HPD 偵測是本專案的練習重點之一
                （002 §bring-up「插拔線時 /sys/class/drm/.../status 正確變化」），
                用輪詢也能做，但中斷才是 driver 真正的寫法。
    HDMI_PD     002 §1.4 明確要求「MIPI 模式時 ADV7511 要保持關閉」。
                它同時是 I2C 位址的 strap，所以 GPIO + 下拉電阻兩者都要。
    PANEL_RESET_N  DSI 面板的初始化序列一定要能拉 RESET，
                沒有它連 DCS 命令都送不進去。MIPI 是本專案第一優先。
  其餘兩個原本也想要 GPIO 的訊號改用不佔腳的做法：
    USB_EN      100K 上拉常開（usb 頁 R75）—— 失去軟體關閉 USB 埠的能力
    USB_OC_N    拉到測試點 TP13 —— 失去軟體讀過流狀態的能力
  這兩個失去的能力都不影響 bring-up，而 HDMI 那兩個會。

用法：python hardware/scripts/gen_header_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "header.kicad_sch")

HDR = "Connector_Generic:Conn_02x13_Odd_Even"
HDR_FP = "Connector_PinHeader_2.54mm:PinHeader_2x13_P2.54mm_Vertical"

# 腳號 → net。奇數在左、偶數在右（Odd_Even 符號的排法）。
PINOUT = {
    1:  "+3V3",         2:  "+5V_VBUS",
    3:  "HDR_I2C1_SDA", 4:  "+5V_VBUS",
    5:  "HDR_I2C1_SCL", 6:  "GND",
    7:  "HDR_GPIO0",    8:  "HDR_UART1_TX",
    9:  "GND",          10: "HDR_UART1_RX",
    11: "HDR_GPIO1",    12: "HDR_GPIO2",
    13: "HDR_GPIO3",    14: "GND",
    15: "HDR_GPIO4",    16: "HDR_GPIO5",
    17: "+3V3",         18: "HDR_GPIO6",
    19: "HDR_I2C2_SDA", 20: "GND",
    21: "HDR_I2C2_SCL", 22: "GND",
    # UART0 console 備援（004 §5）。接在 0Ω 的 CH340N 那一側，
    # 不是直接接 SDC0 主幹 —— 否則排針就成了 50MHz SD 時脈上的 stub。
    23: "UART0_TX_CH",  24: "UART0_RX_CH",
    25: "GND",          26: "+3V3",
}
RAILS = {"+3V3", "+5V_VBUS", "GND"}

JX, JY = 152.4, 127.0
# Conn_02x13_Odd_Even：奇數腳在左 dx=-5.08、偶數在右 dx=+7.62（兩邊不對稱，
# 用 sym_pins.py 查過才知道），第 1/2 腳在最上方，每往下一列 dy 減 2.54。
ROW0 = 15.24
DX = {"L": -5.08, "R": 7.62}


def main():
    p = Page(SCH, ROOT)
    p.part(HDR, "J7", "Conn_02x13", JX, JY, 0, HDR_FP, 1,
           [str(n) for n in range(1, 27)],
           "2x13 擴充排針", ref_dy=-20.32, val_dy=20.32)

    n_rail = n_sig = 0
    for pin, net in PINOUT.items():
        row = (pin - 1) // 2
        side = "L" if pin % 2 else "R"
        x = JX + DX[side]
        y = JY - (ROW0 - row * 2.54)
        if net in RAILS:
            p.pin_rail(x, y, side, net)
            n_rail += 1
        else:
            p.pin_label(x, y, side, net)
            n_sig += 1
    p.stat["訊號腳"] = n_sig
    p.stat["電源與地"] = n_rail

    # ── 圖紙註記：排針腳位表 ─────────────────────────
    p.note("2x13 擴充排針腳位", 25.4, 50.8, 2.54)
    p.note("（T113 側全部經限流電阻，畫在 mcu 頁 R20~R35）", 25.4, 57.15)
    for i in range(13):
        a, b = 2 * i + 1, 2 * i + 2
        p.note(f"{a:>2}  {PINOUT[a]:<14}  {b:>2}  {PINOUT[b]}",
               25.4, 67.31 + i * 5.08)

    p.note("⚠ 與 SPEC 的差異：純 GPIO 10 支 -> 7 支", 25.4, 147.32, 1.778)
    p.note("   PG12 -> HDMI_INT_N（ADV7511 中斷，HPD 偵測要用）", 25.4, 153.67)
    p.note("   PG14 -> HDMI_PD  （002 §1.4：MIPI 模式要能關掉 ADV7511）", 25.4, 158.75)
    p.note("   PG4  -> PANEL_RESET_N（DSI 面板沒有 RESET 連初始化都做不了）", 25.4, 163.83)

    p.note("⚠ HDR_I2C1 是共用匯流排", 25.4, 173.99, 1.778)
    p.note("   ADV7511 的控制 I2C 也掛在這兩條上（display 頁）。", 25.4, 180.34)
    p.note("   外接模組的位址不可與 ADV7511 衝突（0x39 / 0x3D）。", 25.4, 185.42)

    p.note("⚠ pin 23/24 的 UART0 console 是分支，不是主幹", 25.4, 200.66, 1.778)
    p.note("   它們接在 usb 頁 R104/R105 這兩顆 0Ω 的 CH340N 那一側。", 25.4, 207.01)
    p.note("   0Ω 焊上時，這段排針走線也掛在 SDC0_CLK / SDC0_D3 上 ——", 25.4, 212.09)
    p.note("   SD 高速模式跑不穩就拆掉 0Ω（007 §5.2）。", 25.4, 217.17)

    p.note("★ 排針放 PG bank 的理由（007 §4）", 25.4, 232.41, 1.778)
    p.note("   排針是全板最容易燒的地方：手滑短路、接錯模組、熱插拔、外部電源倒灌。",
           25.4, 238.76)
    p.note("   放 PB/PC/PF -> 燒了同時失去 SD 開機 + NOR 開機 + UART log -> 變磚",
           25.4, 243.84)
    p.note("   放 PG       -> 燒了只失去排針本身", 25.4, 248.92)

    p.commit()


if __name__ == "__main__":
    main()
