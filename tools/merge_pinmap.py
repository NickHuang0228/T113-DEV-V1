#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 datasheet 自動抽取的電氣欄位，併進 KiCad 用的腳位表，成為單一真實來源。

流程（需要重做時照這個順序）：
    1. python tools/extract_pins.py      從 datasheet 抽 → tools/t113s3_pins.csv
    2. python tools/merge_pinmap.py      併進 → hardware/data/T113-S3_pinmap.csv
    3. rm tools/t113s3_pins.csv          中間產物，不留在版控

設計成**冪等**：目標檔已有的欄位（bank / type / note 這些人工判斷的）永遠不動，
只補上 datasheet 側的欄位。所以重跑安全，不會蓋掉人工整理的結果。

EPAD（pin 129）不在 datasheet 的 Table 4-2 裡，datasheet 側欄位留空。
"""
import csv, io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DS = os.path.join(ROOT, "tools", "t113s3_pins.csv")               # datasheet 抽取
TARGET = os.path.join(ROOT, "hardware", "data", "T113-S3_pinmap.csv")  # 單一來源

# datasheet 側要併進來的欄位：CSV 欄名 → 目標欄名
DS_FIELDS = {
    "type":     "ds_type",    # datasheet 的 I/O 型別（I/O, P, AI, AO...），與 KiCad 的 type 不同
    "reset":    "reset",      # 上電重置後的狀態
    "pull":     "pull",       # 內部上下拉
    "drive_mA": "drive_mA",   # 驅動能力
    "supply":   "supply",     # ★ 這支腳吃哪條電源 —— 決定 bank 電壓
    "group":    "ds_group",   # datasheet 的分組（GPIOD / Audio Codec / Power...）
}

OUT_ORDER = ["pin", "name", "bank", "type", "note",
             "ds_type", "reset", "pull", "drive_mA", "supply", "ds_group"]


def main():
    if not os.path.exists(TARGET):
        sys.exit(f"找不到目標檔：{TARGET}")
    if not os.path.exists(SRC_DS):
        sys.exit(f"找不到 datasheet 抽取檔：{SRC_DS}\n先跑 tools/extract_pins.py")

    target = list(csv.DictReader(io.open(TARGET, encoding="utf-8")))
    ds = {int(r["pin"]): r for r in csv.DictReader(io.open(SRC_DS, encoding="utf-8"))}

    # 合併前先驗：兩邊的 pin + name 必須一致（原本 gen_t113_symbol.py 的交叉檢查）
    mismatch = []
    for r in target:
        p = int(r["pin"])
        if p in ds and ds[p]["name"] != r["name"]:
            mismatch.append(f"  pin {p}: 目標={r['name']} datasheet={ds[p]['name']}")
    if mismatch:
        sys.exit("兩份腳位表的 name 不一致，停止合併：\n" + "\n".join(mismatch))

    merged, filled, skipped = [], 0, 0
    for r in target:
        p = int(r["pin"])
        row = dict(r)
        if p in ds:
            for src, dst in DS_FIELDS.items():
                # 冪等：已有值就不覆蓋
                if not row.get(dst, "").strip():
                    row[dst] = ds[p][src]
            filled += 1
        else:
            for dst in DS_FIELDS.values():
                row.setdefault(dst, "")
            skipped += 1
        merged.append(row)

    merged.sort(key=lambda x: int(x["pin"]))

    with io.open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=OUT_ORDER, extrasaction="ignore")
        w.writeheader()
        for row in merged:
            w.writerow({k: row.get(k, "") for k in OUT_ORDER})

    print(f"合併完成：{len(merged)} 列 → {os.path.relpath(TARGET, ROOT)}")
    print(f"  datasheet 欄位已填：{filled} 列")
    print(f"  datasheet 無此腳（欄位留空）：{skipped} 列"
          + (f"  → {[r['name'] for r in merged if not r.get('supply','').strip()]}" if skipped else ""))
    print(f"  欄位：{', '.join(OUT_ORDER)}")


if __name__ == "__main__":
    main()
