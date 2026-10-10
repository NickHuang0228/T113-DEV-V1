#!/usr/bin/env python3
"""建立一張新的子圖紙，並掛進根圖紙的階層。

KiCad 的階層由兩邊構成，缺一不可：
  ① 子頁檔案 xxx.kicad_sch        自己的 uuid、paper、title_block
  ② 根圖紙裡的 (sheet ...) 區塊    指向該檔，並給它一個 uuid 與 page 編號

②的 uuid 很關鍵：子頁上每個元件的 instances 路徑是
`/<根圖紙 uuid>/<這個 sheet 的 uuid>`，對不上的話 KiCad 會認為元件不屬於這張圖，
reference 全部變成 "?"。

用法：
    python hardware/scripts/new_sheet.py display 顯示
    python hardware/scripts/new_sheet.py net 網路
"""
import io
import os
import re
import sys
import uuid as _uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import guard_kicad_closed, esc

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOP = os.path.join(ROOT, "T113-DEV-V1.kicad_sch")

SHEET_W, SHEET_H = 88.9, 54.61
COL_X = (15.24, 116.84, 218.44, 320.04)   # 根圖紙上四欄 × 三列 = 12 格
ROW_Y = (39.37, 109.22, 179.07)
NCOL = len(COL_X)


def blank_sheet(title):
    """空白子頁。刻意不放 sheet_instances —— 那個區塊只屬於根圖紙，
    子頁放了會讓 instances 路徑的查找拿到 "/"（已核對過 mcu.kicad_sch 沒有）。"""
    return f"""(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{_uuid.uuid4()}")
\t(paper "A3")
\t(title_block
\t\t(title "{esc(title)}")
\t)
\t(lib_symbols
\t)
\t(embedded_fonts no)
)
"""


def sheet_block(name, fname, x, y, page, sid, root_uuid):
    return f"""\t(sheet
\t\t(at {x:g} {y:g})
\t\t(size {SHEET_W:g} {SHEET_H:g})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(fields_autoplaced yes)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0)
\t\t)
\t\t(uuid "{sid}")
\t\t(property "Sheetname" "{esc(name)}"
\t\t\t(at {x:g} {y - 0.7116:g} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "{esc(fname)}"
\t\t\t(at {x:g} {y + SHEET_H + 0.9546:g} 0)
\t\t\t(show_name no)
\t\t\t(do_not_autoplace no)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
\t\t(instances
\t\t\t(project "T113-DEV-V1"
\t\t\t\t(path "/{root_uuid}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
"""


def main():
    if len(sys.argv) < 3:
        sys.exit("用法: new_sheet.py <檔名(不含副檔名)> <圖紙名稱>")
    stem, title = sys.argv[1], sys.argv[2]
    guard_kicad_closed(ROOT)

    fname = f"{stem}.kicad_sch"
    fpath = os.path.join(ROOT, fname)
    top = io.open(TOP, encoding="utf-8").read()

    if f'"{fname}"' in top:
        sys.exit(f"✗ {fname} 已掛在根圖紙上，不重複建立")

    root_uuid = re.search(r'\(uuid "([0-9a-f-]+)"\)', top).group(1)
    used = re.findall(r'\(page "(\d+)"\)', top)
    page = max([int(p) for p in used] + [1]) + 1
    n_exist = len(re.findall(r'\n\t\(sheet\n', top))
    if n_exist >= NCOL * len(ROW_Y):
        sys.exit(f"✗ 根圖紙上已經有 {n_exist} 張子頁，格子用完了 —— 先擴 COL_X/ROW_Y")
    x = COL_X[n_exist % NCOL]
    y = ROW_Y[n_exist // NCOL]
    sid = str(_uuid.uuid4())

    if not os.path.exists(fpath):
        io.open(fpath, "w", encoding="utf-8", newline="\n").write(blank_sheet(title))
        print(f"✓ 建立 {fname}")
    else:
        print(f"· {fname} 已存在，只補掛階層")

    end = top.rstrip().rfind(")")
    out = top[:end] + sheet_block(title, fname, x, y, page, sid, root_uuid) + top[end:]
    io.open(TOP, "w", encoding="utf-8", newline="\n").write(out)
    print(f"✓ 掛進根圖紙　page {page}　at ({x:g}, {y:g})")
    print(f"  sheet uuid {sid}")
    print(f"  元件的 instances 路徑應為 /{root_uuid}/{sid}")


if __name__ == "__main__":
    main()
