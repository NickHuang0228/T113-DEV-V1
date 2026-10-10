#!/usr/bin/env python3
"""生成 MIPI DSI 頁：40-pin 0.5mm FPC 座。

資料來源
  002-display.md §1.2（PD0~PD9 直通，ADV7511 掛在 0Ω 分支上）
                 §2.1/§2.2（D-PHY 的兩種模式與走線規則）
                 §2.3（接頭）· §2.4（面板電源 V1 不做）

⚠⚠ 這一頁的腳位順序是「暫定」，不是定案。

  002 §2.3 寫得很白：「面板 FPC 的 pin 定義各家不同，下單前務必用實體面板比對」。
  本頁採用的是常見的 40-pin 4-lane 排法（差分對之間夾 GND），
  但**任何一片實際面板都可能不同**，而 FPC 接錯的代價是整片面板報廢。

  所以：
    [ ] 選定面板之後，拿它的 datasheet 逐腳核對這張表
    [ ] 核對完才可以開始佈這一頁的線
  在那之前，這張圖的價值是「把訊號準備好」，不是「可以直接投板」。

★ 這一頁刻意沒有的東西
  面板電源（VSP +5.5V / VSN -5.5V / VGH +15V / VGL -10V）：
    002 §2.4 決定 V1 不做。理由是高壓 charge pump 的開關雜訊會耦合到
    200mV 的 HS 訊號，第一版不要同時冒這個險。需要時由外部供給。
  背光與觸控：
    同樣沒有 SoC 腳可用。V1 的目標是「DSI 出得了畫面」，不是完整面板模組。

★ PANEL_RESET_N 佔掉一支排針 GPIO（PG4）
  DSI 面板的初始化序列一定要能拉 RESET，沒有它連 DCS 命令都送不進去。
  MIPI 是本專案的第一優先（002 開頭），所以這支腳值得。

用法：python hardware/scripts/gen_mipi_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "mipi.kicad_sch")

FPC = "Connector_Generic:Conn_01x40"
FPC_FP = "Connector_FFC-FPC:TE_4-1734839-0_1x40-1MP_P0.5mm_Horizontal"

# 差分對之間夾 GND：回流路徑要就近可走，否則對與對之間會互相串擾。
PINOUT = {
    1: "GND",            2: "GND",
    3: "DSI_D0N",        4: "DSI_D0P",
    5: "GND",
    6: "DSI_D1N",        7: "DSI_D1P",
    8: "GND",
    9: "DSI_CKN",       10: "DSI_CKP",
    11: "GND",
    12: "DSI_D2N",      13: "DSI_D2P",
    14: "GND",
    15: "DSI_D3N",      16: "DSI_D3P",
    17: "GND",
    18: "PANEL_RESET_N",
    19: "GND",
    20: "PANEL_IOVCC",  21: "PANEL_IOVCC",
    22: "GND",
    23: "+3V3",         24: "+3V3",
    25: "GND",
}
NC_PINS = list(range(26, 41))          # 保留給面板電源，V1 不接
RAILS = {"GND", "+3V3", "PANEL_IOVCC"}

JX, JY = 190.5, 139.7
ROW0 = 48.26                            # 40 腳單排：第 1 腳在符號座標 dy=+48.26
PINDX = -5.08                           # 腳在符號左側（用 sym_pins.py 查的）


def main():
    p = Page(SCH, ROOT)
    p.part(FPC, "J8", "FPC 40P 0.5mm", JX, JY, 0, FPC_FP, 1,
           [str(n) for n in range(1, 41)],
           "MIPI DSI 面板 FPC 座，40 腳 0.5mm pitch",
           ref_dy=-55.88, val_dy=55.88)

    def y_of(pin):
        return JY - (ROW0 - (pin - 1) * 2.54)

    n_sig = n_rail = 0
    for pin, net in PINOUT.items():
        if net in RAILS:
            # PANEL_IOVCC 不是板級電源軌，用標籤；GND / +3V3 用電源符號
            if net == "PANEL_IOVCC":
                p.pin_label(JX + PINDX, y_of(pin), "L", net)
            else:
                p.pin_rail(JX + PINDX, y_of(pin), "L", net)
            n_rail += 1
        else:
            p.pin_label(JX + PINDX, y_of(pin), "L", net)
            n_sig += 1
    for pin in NC_PINS:
        p.nc(JX + PINDX, y_of(pin))
    p.stat["差分與控制"] = n_sig
    p.stat["電源與地"] = n_rail
    p.stat["保留不接"] = len(NC_PINS)

    # ── IOVCC 選擇：3.3V 或 1.8V，二選一 ──────────────
    # 面板的介面電壓是 1.8V 還是 3.3V 要看 datasheet。
    # 兩個位置都留，焊錯邊的代價是面板報廢，所以不做「預設值」——
    # 預設焊 3.3V 是因為多數小尺寸面板用 3.3V，但核對面板之前不要上電。
    # 來源端用電源符號而不是全域標籤：同一條 net 一邊是電源埠、
    # 一邊是同名標籤的話 ERC 會報，看圖的人也會以為是兩條線。
    for y, ref, src, dnp in ((101.6, "R77", "+3V3", False),
                             (116.84, "R78", "+1V8_SOC", True)):
        p.rail(src, 241.3, y)
        p.w(241.3, y, 248.92, y)
        p.res(ref, "0R", 252.73, y, 90, dnp=dnp)
        p.w(256.54, y, 264.16, y)
        p.lab("PANEL_IOVCC", 264.16, y)
    p.stat["IOVCC 選擇"] = 2

    # ── 圖紙註記 ──────────────────────────────────────
    p.note("⚠⚠ 這張腳位表是暫定值，不是定案", 20.32, 50.8, 2.54)
    p.note("002-display.md §2.3：面板 FPC 的 pin 定義各家不同，下單前務必用實體面板比對。",
           25.4, 59.69)
    p.note("選定面板後逐腳核對完，才可以開始佈這一頁的線。", 20.32, 64.77)

    p.note("MIPI D-PHY layout（002 §2.1 / §2.2）", 20.32, 80.01, 1.778)
    p.note("· 同一對銅線上有兩種訊號：HS 是 200mV 差分、LP 是 1.2V 單端。",
           25.4, 86.36)
    p.note("· 所以不能串任何電阻、不能加 AC 耦合電容 —— 那會破壞 LP 的直流準位。",
           25.4, 91.44)
    p.note("· 100 ohm 差分，對內等長 ±0.1mm，各資料對相對 CK 對 ±0.5mm。",
           25.4, 96.52)
    p.note("· 對與對之間 >= 3x 線寬；全程走完整 GND 平面，不跨分割。",
           25.4, 101.6)

    p.note("★ 不能有 stub —— 這是這塊板最重要的一條佈線規則", 20.32, 116.84, 1.778)
    p.note("PD0~PD9 這 10 條同時接到 MIPI FPC 與 ADV7511（002 §1.2）：", 20.32, 123.19)
    p.note("    SoC ══════════════════════> FPC 座      （直通，不經任何元件）",
           25.4, 128.27)
    p.note("           ╚═[0Ω]═════════════> ADV7511      （分支）", 20.32, 133.35)
    p.note("那 10 顆 0Ω 在 display 頁（R51~R60）。", 20.32, 138.43)
    p.note("規則：0Ω 焊盤邊緣距離 MIPI 主幹走線 <= 0.5mm。", 20.32, 143.51)
    p.note("放遠了就白做 —— stub 還在，只是換了個位置。", 20.32, 148.59)
    p.note("（HS 上升時間約 200ps，FR4 約 6.7ps/mm -> 臨界長度約 5mm）",
           25.4, 153.67)

    p.note("★ V1 刻意沒有面板電源（002 §2.4）", 20.32, 168.91, 1.778)
    p.note("MIPI 面板不是接 3.3V 就會亮：典型還要 VSP +5.5V / VSN -5.5V /",
           25.4, 175.26)
    p.note("VGH +15V / VGL -10V，需要專用 LCD bias IC（如 TPS65132）。",
           25.4, 180.34)
    p.note("不做的理由：charge pump 的開關雜訊會耦合到 200mV 的 HS 訊號，",
           25.4, 185.42)
    p.note("第一版不要同時冒這個險。pin 26~40 保留給它，V2 再補。", 20.32, 190.5)

    p.note("★ IOVCC：R77（3.3V，預設焊）/ R78（1.8V，不焊）二選一",
           25.4, 205.74, 1.778)
    p.note("焊錯邊的代價是面板報廢 —— 核對面板 datasheet 之前不要上電。",
           25.4, 212.09)

    p.commit()


if __name__ == "__main__":
    main()
