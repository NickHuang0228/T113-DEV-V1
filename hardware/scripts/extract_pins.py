#!/usr/bin/env python3
"""從 datasheet Table 4-2 抽出腳位表，並與 data/T113-S3_pinmap.csv 對帳。

腳位表的單一真實來源是 `hardware/data/T113-S3_pinmap.csv`。
那份表裡有兩種欄位：

    datasheet 欄位   name / ds_type / reset / pull / drive_mA / supply / group
                     ←── 本腳本從 Table 4-2 機器抽出，可隨時重抽重驗
    設計欄位         bank / type / note
                     ←── 人工判斷（KiCad 單元分組、電氣型別、mux 註記），無法從表裡抽

預設是**對帳模式**：重抽一次 Table 4-2，與 CSV 的 datasheet 欄位逐格比對，
不一致就列出並以非零碼結束。設計欄位不動也不比對。

    python hardware/scripts/extract_pins.py            # 對帳
    python hardware/scripts/extract_pins.py --write    # 重抽並覆寫 datasheet 欄位

抽取方法的教訓（見 notes/devlog.md 2026-09-21）：
Table 4-2 有繪製線框，必須用 page.find_tables() 依線框切格子。
用 get_text() 依文字座標重建欄位會跑位 —— 那是「Table 4-2 不可用」的真正原因。
"""
import csv
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
ROOT = os.path.dirname(HW)
CSV_PATH = os.path.join(HW, "data", "T113-S3_pinmap.csv")
PDF_PATH = os.path.join(ROOT, "docs", "reference", "allwinner",
                        "T113-S3_Datasheet_v1.6_20220303.pdf")

# Table 4-2 Pin Characteristics 橫跨 p.24~p.29（PDF 索引 33~38）
PAGES = range(33, 39)

# CSV 欄序。前七欄來自 datasheet，後三欄是設計判斷。
FIELDS = ["pin", "name", "bank", "type", "ds_type",
          "reset", "pull", "drive_mA", "supply", "group", "note"]
DS_FIELDS = ["name", "ds_type", "reset", "pull", "drive_mA", "supply", "group"]

# EPAD 不在 Table 4-2 裡（那張表只列 128 支訊號腳），機構圖才有。
EPAD_PIN = "129"


def extract(pdf_path=PDF_PATH):
    """回傳 {pin: {欄位}}，只含 Table 4-2 的 128 列。"""
    try:
        import fitz
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install pymupdf")
    if not os.path.exists(pdf_path):
        sys.exit(f"找不到 datasheet：{pdf_path}\n"
                 f"PDF 不進版控，取得方式見 docs/reference/README.md")

    doc = fitz.open(pdf_path)
    rows = {}
    group = ""
    for pi in PAGES:
        for tab in doc[pi].find_tables().tables:
            for raw in tab.extract():
                cells = [(c or "").strip().replace("\n", " ") for c in raw]
                if not any(cells):
                    continue
                first = cells[0]
                # 表頭列
                if first.startswith(("Ball#", "State")) or "Ball Reset" in " ".join(cells):
                    continue
                # 分組標題列：只有第一欄有字
                if first and not any(cells[1:]):
                    group = first
                    continue
                if not re.fullmatch(r"\d+", first):
                    continue
                rows[first] = {
                    "name":     cells[1],
                    "ds_type":  cells[2],
                    "reset":    cells[3],
                    "pull":     cells[4],
                    "drive_mA": cells[5],
                    "supply":   cells[6],
                    "group":    group,
                }
    return rows


def load_csv():
    rows = list(csv.DictReader(io.open(CSV_PATH, encoding="utf-8")))
    missing = [f for f in FIELDS if f not in rows[0]]
    if missing:
        sys.exit(f"{os.path.basename(CSV_PATH)} 缺欄位：{', '.join(missing)}")
    return rows


def write_csv(rows):
    with io.open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows)


def main():
    write = "--write" in sys.argv
    pdf = extract()
    print(f"Table 4-2 抽出 {len(pdf)} 列")

    nums = sorted(int(p) for p in pdf)
    gaps = sorted(set(range(1, 129)) - set(nums))
    if gaps or nums != sorted(set(nums)):
        sys.exit(f"抽取結果不完整 —— 缺號 {gaps or '無'}，重複 "
                 f"{[p for p in set(nums) if nums.count(p) > 1] or '無'}")

    rows = load_csv()
    by_pin = {r["pin"]: r for r in rows}

    only_csv = sorted(set(by_pin) - set(pdf) - {EPAD_PIN}, key=int)
    only_pdf = sorted(set(pdf) - set(by_pin), key=int)
    if only_csv or only_pdf:
        for p in only_csv:
            print(f"  ✗ pin {p} 只在 CSV 裡（{by_pin[p]['name']}）")
        for p in only_pdf:
            print(f"  ✗ pin {p} 只在 Table 4-2 裡（{pdf[p]['name']}）")
        sys.exit("腳號集合不一致")

    diffs = []
    for p in sorted(pdf, key=int):
        for f in DS_FIELDS:
            want, got = pdf[p][f], by_pin[p][f]
            if want != got:
                diffs.append((p, f, want, got))

    if write:
        for p, r in pdf.items():
            by_pin[p].update(r)
        write_csv(rows)
        print(f"已覆寫 {os.path.relpath(CSV_PATH, ROOT)} 的 datasheet 欄位"
              f"（{len(diffs)} 格有更動；設計欄位未動）")
        return

    if diffs:
        for p, f, want, got in diffs[:40]:
            print(f"  ✗ pin {p} {f}: datasheet={want!r}  CSV={got!r}")
        if len(diffs) > 40:
            print(f"  ...還有 {len(diffs) - 40} 格")
        sys.exit(f"{len(diffs)} 格與 datasheet 不符 —— 查清楚哪邊錯了，"
                 f"確認 CSV 該跟著改再跑 --write")

    epad = by_pin.get(EPAD_PIN)
    print(f"  ✓ 128 腳 × {len(DS_FIELDS)} 欄與 Table 4-2 完全一致")
    print(f"  ✓ pin {EPAD_PIN} {epad['name'] if epad else '—'} "
          f"不在 Table 4-2 裡（來源是 §7.2 機構圖），已跳過")


if __name__ == "__main__":
    main()
