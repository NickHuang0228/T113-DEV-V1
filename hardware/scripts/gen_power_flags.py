#!/usr/bin/env python3
"""在電源頁補上 PWR_FLAG，告訴 ERC 這四條軌確實有電源進來。

★ 為什麼 ERC 會說「沒人驅動」

  ERC 的 power_pin_not_driven 是在問：
      「這條 net 上有沒有任何一支 power_out 型別的腳？」

  降壓器的輸出走的是 SW 腳 →[電感]→ 輸出節點。
  電感是被動件，所以輸出節點上一支 power_out 都沒有 —— 但電當然是有的。
  LDO 也一樣：它的輸出腳在符號上常被標成 power_out，可是中間只要隔一顆
  磁珠或 0Ω，下游節點就又「沒人驅動」了。

  PWR_FLAG 是 KiCad 給這件事的標準解法。它不進 BOM、不上板，
  只是把「這裡確實有電源進來」這個事實標註給 ERC 看。

⚠ 它會讓 ERC 閉嘴，所以只能用在確實有電的地方。
  拿它去蓋掉真的沒接的軌，等於把安全網剪掉。

這四條都是 RY1303（U1）三通道降壓與其後級產生的：
    +3V3   CH1 → 電感 → +3V3
    +1V5   CH3 → 電感 → +1V5（DDR3）
    +0V9   CH2 → 電感 → +0V9（VDD-CORE）
    GND    整板共地，源頭是 VBUS 的回流

這支腳本只「附加」，不碰電源頁既有的任何內容。

用法：python hardware/scripts/gen_power_flags.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import Page

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "power.kicad_sch")

# 電源頁既有內容到 y≈235 為止，所以擺在 y=254 這一排。
FLAGS = [("+3V3", 50.8), ("+1V5", 101.6), ("+0V9", 152.4), ("GND", 203.2)]
ROW_Y = 254.0


def main():
    p = Page(SCH, ROOT)
    for net, x in FLAGS:
        if net == "GND":
            # GND 的旗標要畫在下面（接地符號朝下），不然圖形會疊在一起
            p.rail(net, x, ROW_Y + 3.81)
            p.w(x, ROW_Y, x, ROW_Y + 3.81)
            from schlib import symbol
            p.out.append(symbol("power:PWR_FLAG", "#FLG", net, x, ROW_Y, 0,
                                "", 1, p.sheet, ("1",),
                                "Special symbol for telling ERC where power comes from",
                                False, -3.81, -6.35, hide_ref=True))
        else:
            p.pwr_flag(net, x, ROW_Y)
    p.stat["PWR_FLAG"] = len(FLAGS)

    p.note("PWR_FLAG —— 給 ERC 看的，不是真元件", 38.1, 236.22, 1.778)
    p.note("降壓器的輸出走 SW 腳 ->[電感]-> 輸出節點，電感是被動件，",
           38.1, 242.57)
    p.note("所以 ERC 在輸出節點上找不到任何 power_out 腳，判定「沒人驅動」。",
           38.1, 247.65)
    p.note("⚠ 只能用在確實有電的地方 —— 拿它蓋掉真的沒接的軌等於把安全網剪掉。",
           38.1, 274.32)

    p.commit()


if __name__ == "__main__":
    main()
