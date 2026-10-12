#!/usr/bin/env python3
"""把既有圖紙上的全域標籤改名（唯一一支會動到手畫內容的腳本）。

其他 gen_*_sheet.py 都只「附加」，刻意不碰既有內容。
這支不一樣，所以多三道保險：
  ① KiCad 開著就中止
  ② 工作目錄不乾淨就中止 —— 改壞了要能 git checkout 回去
  ③ 每個舊名稱必須「剛好出現一次」，多一次少一次都中止

為什麼要改名：mcu 頁的 PG bank 原本全部當排針 GPIO，
但三個週邊訊號沒有其他腳可用，而它們缺了會直接影響 bring-up。

    PG12  HDR_GPIO8 → HDMI_INT_N     ADV7511 中斷。HPD 偵測是本專案的練習重點，
                                     輪詢也能做，但中斷才是 driver 真正的寫法。
    PG14  HDR_GPIO9 → HDMI_PD        002 §1.4：MIPI 模式時要能關掉 ADV7511。
                                     它同時是 I2C 位址的 strap（display 頁 R52 下拉）。
    PG4   HDR_GPIO7 → PANEL_RESET_N  DSI 面板的初始化序列一定要能拉 RESET，
                                     沒有它連 DCS 命令都送不進去。

代價：排針的純 GPIO 從 10 支變成 7 支（SPEC 寫 10）。
這是刻意的取捨，理由寫在 gen_header_sheet.py 與排針頁的圖紙註記上。

另外兩個也想要 GPIO 的訊號改用不佔腳的做法，所以不在這份清單裡：
    USB_EN    100K 上拉常開（usb 頁 R75）
    USB_OC_N  拉到測試點 TP13

用法：python hardware/scripts/rename_nets.py          # 預覽
      python hardware/scripts/rename_nets.py --apply  # 真的改
"""
import io
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

RENAMES = [
    ("mcu.kicad_sch", "HDR_GPIO8", "HDMI_INT_N",
     "PG12 · ADV7511 中斷輸出"),
    ("mcu.kicad_sch", "HDR_GPIO9", "HDMI_PD",
     "PG14 · ADV7511 power-down（同時是 I2C 位址 strap）"),
    ("mcu.kicad_sch", "HDR_GPIO7", "PANEL_RESET_N",
     "PG4 · MIPI 面板 RESET"),
    # ★ 差分對改名。KiCad 是用 net 名稱的字尾 _P/_N（或 +/-）判斷
    #   「這兩條是一對」—— DSI_D0P 的字尾是 0P，不符合，所以
    #   差分對佈線工具與對內等長調整對 MIPI 全部不能用。
    #   而 MIPI 的差分佈線正是這塊板最主要的練習目標。
    ("mcu.kicad_sch", "DSI_D0P", "DSI_D0_P",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D0N", "DSI_D0_N",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D1P", "DSI_D1_P",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D1N", "DSI_D1_N",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D2P", "DSI_D2_P",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D2N", "DSI_D2_N",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D3P", "DSI_D3_P",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_D3N", "DSI_D3_N",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_CKP", "DSI_CK_P",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
    ("mcu.kicad_sch", "DSI_CKN", "DSI_CK_N",
     "MIPI 差分對：KiCad 用字尾 _P/_N 才認得出是一對"),
]


def git_clean():
    """只看「已追蹤檔案有沒有被改過」。

    -uno 是必要的：run_all.py 匯入 schlib 就會產生 scripts/__pycache__，
    那是未追蹤檔，不影響 git checkout 能不能把改壞的內容救回來。
    不加這個旗標的話，這支腳本永遠認為工作目錄是髒的。
    """
    r = subprocess.run(["git", "status", "--porcelain", "-uno", "--", "hardware"],
                       cwd=PROJ, capture_output=True, text=True)
    return r.returncode == 0 and not r.stdout.strip()


def main():
    apply = "--apply" in sys.argv
    guard_kicad_closed(ROOT)
    # run_all.py 會在第一步之前檢查一次，之後每一步都會把工作目錄弄髒，
    # 所以它用 --skip-git-check 把這裡關掉。單獨跑的時候仍然要檢查。
    if apply and "--skip-git-check" not in sys.argv and not git_clean():
        sys.exit("✗ hardware/ 有未提交的變更 —— 先 commit，改壞了才回得去。")

    ok = True
    for fname, old, new, why in RENAMES:
        path = os.path.join(ROOT, fname)
        s = io.open(path, encoding="utf-8").read()
        n_old = s.count(f'"{old}"')
        n_new = s.count(f'"{new}"')
        tag = "✓" if n_old == 1 and n_new == 0 else "✗"
        if tag == "✗":
            ok = False
        print(f"  {tag} {fname}  {old} -> {new}")
        print(f"      {why}")
        print(f"      舊名稱出現 {n_old} 次（要 1 次）、新名稱 {n_new} 次（要 0 次）")
        if apply and tag == "✓":
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                s.replace(f'"{old}"', f'"{new}"'))

    if not ok:
        sys.exit("\n✗ 有項目不符預期，一個都沒改。")
    if apply:
        print("\n✓ 已改名。接著跑 check_schematic.py 確認 net 接到正確的 T113 腳。")
    else:
        print("\n（預覽模式，沒有改檔。要真的改請加 --apply）")


if __name__ == "__main__":
    main()
