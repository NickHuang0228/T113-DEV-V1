#!/usr/bin/env python3
"""補上 T113-S3 的逐腳去耦電容。

★ 為什麼這一頁原本是空的

  mcu 頁是手畫的，當時只拉了訊號線，去耦電容從來沒補。
  重新稽核 netlist 才發現：**T113 的 23 支電源腳一顆本地電容都沒有**，
  只有穩壓器輸出端的幾顆 bulk。

      +1V8_AUDIO   3 支腳   0 顆       ★ 011 §6.1 明寫「LDOA-OUT 2.2µF 到地」
      +0V9         5 支腳   只有 C7 22µF 在 buck 那端
      +1V5         2 支腳   只有 C8 22µF
      +1V8_SOC     5 支腳   只有 C11 1µF
      +3V3         6 支腳   有電容，但都在別顆 IC 旁邊

  對照之下 ADV7511 那頁（程式生成的）13 支電源腳各有一顆 0.1µF。
  **整塊板最重要的晶片反而是去耦最差的那一顆。**

  後果不是「不會開機」，是「時好時壞」：1.2GHz 的核心加 DDR3，
  本地沒有電荷水庫 → 電流瞬變時軌壓塌陷 → 隨機當機、DDR training 失敗。
  這種問題查起來要好幾週，而且每次重現條件都不一樣。
  （概念 08：本地電荷水庫，位置比容值重要。）

★ 配置

      軌            腳數   0.1µF   另加
      +0V9           5      5      10µF   核心，電流瞬變最大
      +1V5           2      2      10µF   DDR3
      +1V8_SOC       5      5      —
      +1V8_AUDIO     3      2      2.2µF  ← 011 §6.1 指定的那顆
      +3V3           6      6      —

⚠ 這一頁只決定「有幾顆、接哪一條軌」。
  **真正決定效果的是 layout**：每一顆要貼著它負責的那支腳，
  via 直接下地平面。擺遠了就只是 BOM 上多幾顆料。

用法：python hardware/scripts/gen_mcu_decoupling.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "mcu.kicad_sch")

C0805 = "Capacitor_SMD:C_0805_2012Metric"

# (軌, y, x 起點, [(ref, 值, footprint), ...])
# 擺在 y 230~280 這一帶：既有內容到 y≈222，而 x>170 被兩顆晶振佔住了。
BANKS = [
    # 編號刻意一顆一顆寫死，不用 f"C{n+i}" ——
    # 全專案重編 designator 時，算出來的編號不會被文字替換掃到，
    # 結果就是這一頁跟別頁對不起來（已經踩過一次）。
    ("+0V9", 238.76, 25.4,
     [("C62", "100nF", None), ("C63", "100nF", None), ("C64", "100nF", None),
      ("C65", "100nF", None), ("C66", "100nF", None), ("C67", "10uF", C0805)]),
    ("+1V5", 238.76, 91.44,
     [("C68", "100nF", None), ("C69", "100nF", None), ("C70", "10uF", C0805)]),
    ("+1V8_AUDIO", 238.76, 127.0,
     [("C71", "2.2uF", None), ("C72", "100nF", None), ("C73", "100nF", None)]),
    ("+1V8_SOC", 266.7, 25.4,
     [("C74", "100nF", None), ("C75", "100nF", None), ("C76", "100nF", None),
      ("C77", "100nF", None), ("C78", "100nF", None)]),
    ("+3V3", 266.7, 81.28,
     [("C79", "100nF", None), ("C80", "100nF", None), ("C81", "100nF", None),
      ("C82", "100nF", None), ("C83", "100nF", None), ("C84", "100nF", None)]),
]


def main():
    p = Page(SCH, ROOT)
    n = 0
    for net, y, x, specs in BANKS:
        p.cap_bank(x, y, specs, net, pitch=10.16)
        n += len(specs)
        p.stat[net] = len(specs)

    p.note("T113-S3 的逐腳去耦（2026-10-10 補；mcu 頁手畫時漏了）",
           25.4, 227.33, 1.778)
    p.note("每一條軌「幾支電源腳就幾顆 0.1uF」，核心與 DDR 另加 10uF 的本地 bulk。",
           25.4, 232.41)
    p.note("★ 真正決定效果的是 layout：每一顆要貼著它負責的那支腳、via 直接下地平面。",
           25.4, 285.75)
    p.note("   擺遠了就只是 BOM 上多幾顆料（概念 08）。", 25.4, 290.83)

    p.commit()


if __name__ == "__main__":
    main()
