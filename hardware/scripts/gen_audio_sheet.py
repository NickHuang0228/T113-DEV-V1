#!/usr/bin/env python3
"""生成音訊頁：3.5mm 立體聲座（line-out）。

資料來源
  SPEC.md「音訊 內建 codec → 3.5mm 座（line-out）」
  MangoPi MQ-R v1.6 原理圖 p.3 —— T113 的耳機輸出接法

T113 的 codec 輸出鏈畫在 mcu 頁（unit 6）：
    HPOUTL (99) ─[R37 33R]─[C20 0.1µF]─ HP_L
    HPOUTR (98) ─[R38 33R]─[C21 0.1µF]─ HP_R
    HPOUTFB (100) ───────────────────── HP_FB
這一頁只負責把那三條接到座子上。

★ HP_FB 不是 GND，不可以接地。
  它是耳機輸出的共同回授端，要接到座子的「接地環（sleeve）」。
  把它接到板上的 GND 會讓回授路徑經過整片地平面，
  輕則串音、重則輸出直流偏移 —— MangoPi 也是接到座子的接地環，不是 GND。

用法：python hardware/scripts/gen_audio_sheet.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "audio.kicad_sch")

JX, JY = 152.4, 101.6
# AudioJack3：三支腳都在右側 dx=+5.08。T=tip(左聲道) R=ring(右聲道) S=sleeve(地環)
PINS = {"T": (-2.54, "HP_L"), "R": (0.0, "HP_R"), "S": (2.54, "HP_FB")}


def main():
    p = Page(SCH, ROOT)
    p.part("Connector_Audio:AudioJack3", "J10", "3.5mm 立體聲", JX, JY, 0,
           "Connector_Audio:Jack_3.5mm_CUI_SJ1-3523N_Horizontal", 1,
           ("T", "R", "S"), "3.5mm 立體聲座，line-out",
           ref_dy=-12.7, val_dy=12.7)
    for num, (dy, net) in PINS.items():
        p.pin_label(JX + 5.08, JY - dy, "R", net)
    p.stat["音源座"] = 3

    p.note("3.5mm line-out（SPEC：內建 codec → 3.5mm 座）", 25.4, 50.8, 2.54)
    p.note("T113 側的輸出鏈畫在 mcu 頁 unit 6：", 25.4, 60.96)
    p.note("    HPOUTL  (99)  -[R37 33R]-[C20 0.1uF]- HP_L   -> J10 tip",
           25.4, 66.04)
    p.note("    HPOUTR  (98)  -[R38 33R]-[C21 0.1uF]- HP_R   -> J10 ring",
           25.4, 71.12)
    p.note("    HPOUTFB (100) ------------------------ HP_FB  -> J10 sleeve",
           25.4, 76.2)

    p.note("★ HP_FB 不是 GND，不可以接地", 25.4, 91.44, 1.778)
    p.note("它是耳機輸出的共同回授端，要接到座子的接地環（sleeve）。", 25.4, 97.79)
    p.note("接到板上的 GND 會讓回授路徑經過整片地平面 ——", 25.4, 102.87)
    p.note("輕則串音，重則輸出有直流偏移。MangoPi MQ-R 也是這樣接的。",
           25.4, 107.95)

    p.note("layout 提醒", 25.4, 123.19, 1.778)
    p.note("· 座子的接地環走獨立一條回到 codec 的 HPOUTFB，不要併進地平面。",
           25.4, 129.54)
    p.note("· AVCC / HPVCC 由 +1V8_AUDIO 供電（電源頁），與數位電源分開走。",
           25.4, 134.62)
    p.note("· 這條鏈路上的 0.1uF 是 AC 耦合，不是去耦 —— 不要「順手」改大小。",
           25.4, 139.7)

    p.commit()


if __name__ == "__main__":
    main()
