#!/usr/bin/env python3
"""一次把剩下的八張子圖紙生出來，順序不能亂。

為什麼要有這支：步驟之間有相依性 ——
  · 子頁檔案必須先被 new_sheet.py 掛進根圖紙，生成器才算得出
    元件的 instances 路徑（對不上的話 reference 全變 "?"）
  · 改名要在生成之前，否則 display 頁的 HDMI_PD 會接到舊名字
  · 驗證要在最後，而且要跑兩支：
      check_power_rails.py  用座標比對電源軌
      check_schematic.py    用 kicad-cli 匯出 netlist 再套規則

⚠ 執行前 KiCad 必須關閉。腳本自己會擋，但先關掉比較省事。
⚠ 這支會真的寫檔。跑之前先 git commit —— 出事才回得去。

用法：python hardware/scripts/run_all.py            # 預演，只印步驟
      python hardware/scripts/run_all.py --apply    # 真的跑
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import guard_kicad_closed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJ = os.path.dirname(ROOT)

# (檔名, 圖紙標題)。順序決定根圖紙上的格子位置與頁碼。
SHEETS = [
    ("display", "顯示 · ADV7511"),
    ("hdmi",    "顯示 · HDMI 座"),
    ("mipi",    "顯示 · MIPI DSI"),
    ("net",     "網路"),
    ("usb",     "USB 與開機"),
    ("storage", "儲存"),
    ("header",  "排針"),
    ("audio",   "音訊"),
]

STEPS = (
    [("改名：PG12/PG14/PG4 挪給 HDMI 與面板", ["rename_nets.py", "--apply"]),
     ("主晶片頁 unit 6/7（類比音訊 + 系統/USB）", ["gen_mcu_unit67.py"])]
    + [(f"建立子頁 {s}（{t}）", ["new_sheet.py", s, t]) for s, t in SHEETS]
    + [(f"生成 {s} 頁內容", [f"gen_{s}_sheet.py"]) for s, _ in SHEETS]
    + [("驗證：電源軌（座標比對）", ["check_power_rails.py"]),
       ("驗證：netlist 規則（kicad-cli）", ["check_schematic.py"])]
)


def main():
    apply = "--apply" in sys.argv
    guard_kicad_closed(ROOT)

    if not apply:
        print("預演 —— 以下步驟會依序執行（加 --apply 才真的跑）：\n")
        for i, (why, cmd) in enumerate(STEPS, 1):
            print(f"  {i:2d}. {why}")
            print(f"      python hardware/scripts/{' '.join(cmd)}")
        print(f"\n共 {len(STEPS)} 步。執行前請確認 git 已 commit。")
        return

    for i, (why, cmd) in enumerate(STEPS, 1):
        print(f"\n{'=' * 64}\n[{i}/{len(STEPS)}] {why}\n{'=' * 64}")
        r = subprocess.run([sys.executable, os.path.join(HERE, cmd[0])] + cmd[1:],
                           cwd=PROJ)
        # 驗證腳本回非零代表「查到問題」，不是「跑失敗」，所以不中斷。
        if r.returncode != 0 and not cmd[0].startswith("check_"):
            sys.exit(f"\n✗ 第 {i} 步失敗（exit {r.returncode}）—— 停在這裡。"
                     f"\n  前面的步驟已經寫進檔案了，要回復用 git checkout hardware/")
    print(f"\n{'=' * 64}\n✓ 八張子圖紙全部生成完畢。\n{'=' * 64}")
    print("接下來：")
    print("  1. 開 KiCad 看每一頁有沒有元件重疊、標籤被蓋住")
    print("  2. 跑 ERC，把剩下的問題一條一條清掉")
    print("  3. 補 footprint 與 LCSC 欄位，才能出 BOM")


if __name__ == "__main__":
    main()
