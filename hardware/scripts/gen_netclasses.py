#!/usr/bin/env python3
"""在專案設定裡建立 netclass 分組，給佈線用。

★ 刻意不填線寬與間距

  005-stackup.md §2 寫得很白：

      ⚠ 線寬必須用 JLCPCB 下單頁的阻抗計算器回算，不能自行假設。
        下單時勾選「阻抗控制」，他們會給對應的線寬/間距表，照那個重畫。

  所以這支只做「分類」—— 把每條 net 歸到正確的 class 並寫上阻抗目標，
  線寬沿用 Default。等 JLCPCB 回算之後，在 PCB 編輯器的
  「板子設定 → 網路類別」一個地方改數字，全部走線就跟著改。

  先分類的好處：佈線時一眼看得出哪條線屬於哪一類，
  而且之後填數字不必一條一條挑 net。

★ 差分對能被識別的前提是命名

  KiCad 用 net 名稱的字尾 `_P`/`_N`（或 `+`/`-`）判斷「這兩條是一對」。
  原本 MIPI 叫 `DSI_D0P`（字尾是 `0P`）、USB 叫 `USB0_DP`，
  兩者都不符合 → 差分對佈線工具與對內等長調整都不能用。
  已經全部改成 `DSI_D0_P` / `USB0_D_P` 這種寫法（17 組全部合規）。

用法：python hardware/scripts/gen_netclasses.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import guard_kicad_closed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRO = os.path.join(ROOT, "T113-DEV-V1.kicad_pro")

# (類別名稱, 說明, 顏色, [net 樣式...])
CLASSES = [
    ("MIPI_DSI", "100 ohm 差分 · 對內 ±0.1mm · 相對 CK ±0.5mm · 不可有 stub",
     "rgba(220, 60, 180, 1.000)", ["DSI_*"]),
    ("TMDS", "100 ohm 差分 · 對內 ±0.15mm · 相對 CK ±0.5mm",
     "rgba(60, 140, 220, 1.000)", ["TMDS_*"]),
    ("USB_HS", "90 ohm 差分 · 對內 ±0.15mm",
     "rgba(80, 190, 90, 1.000)",
     ["USB?_D_*", "CH340_D_*", "J4_D_*", "J5_D_*", "J6_D_*"]),
    ("ETH_MDI", "100 ohm 差分 · 過變壓器前後都要控",
     "rgba(230, 160, 40, 1.000)", ["MDI?_*"]),
    ("RGB_LCD", "單端 · CLK 要控阻抗、走線短、旁邊不走高頻（002 §3.2.3）",
     "rgba(150, 150, 150, 1.000)", ["LCD0_*", "HDMI_D1?", "HDMI_D?"]),
    ("POWER", "線寬依電流另算，不吃 Default 的 0.25mm",
     "rgba(200, 60, 60, 1.000)",
     ["+*", "GND", "GND_CHASSIS", "HDMI_5V", "PANEL_IOVCC"]),
]


def main():
    guard_kicad_closed(ROOT)
    d = json.load(io.open(PRO, encoding="utf-8"))
    ns = d.setdefault("net_settings", {})
    classes = ns.setdefault("classes", [])
    base = next((c for c in classes if c.get("name") == "Default"), {})

    have = {c.get("name") for c in classes}
    added = []
    for name, desc, color, _pats in CLASSES:
        if name in have:
            continue
        c = dict(base)
        c.update({
            "name": name,
            "description": desc,
            "pcb_color": color,
            "priority": len(classes),
        })
        # ⚠ 線寬 / 間距 / 差分對參數刻意不設 —— 沿用 Default，
        #   等 JLCPCB 的阻抗回算結果出來再填（005 §2）。
        classes.append(c)
        added.append(name)

    pats = ns.setdefault("netclass_patterns", [])
    exist = {(p.get("netclass"), p.get("pattern")) for p in pats}
    n_pat = 0
    for name, _d, _c, patterns in CLASSES:
        for pat in patterns:
            if (name, pat) not in exist:
                pats.append({"netclass": name, "pattern": pat})
                n_pat += 1

    json.dump(d, io.open(PRO, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=2)
    print(f"  新增 netclass {len(added)} 類：{added or '（都已存在）'}")
    print(f"  新增 net 樣式 {n_pat} 條")
    print("\n  ⚠ 線寬與間距刻意留空（沿用 Default 0.25mm）——")
    print("    005 §2：必須用 JLCPCB 的阻抗計算器回算，不能自行假設。")
    print("    回算之後在「板子設定 → 網路類別」一個地方改，全部走線跟著改。")


if __name__ == "__main__":
    main()
