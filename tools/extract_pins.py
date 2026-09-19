import fitz, csv, re, sys

PDF = r"C:\Users\1131880\Downloads\T113-DEV-V1\docs\reference\allwinner\T113-S3_datasheet_v1.6.pdf"
OUT = r"C:\Users\1131880\Downloads\T113-DEV-V1\tools\t113s3_pins.csv"

doc = fitz.open(PDF)
rows = []
group = ""

# Table 4-2 橫跨 p.34~p.39 (0-indexed 33~38)
for pi in range(33, 39):
    page = doc[pi]
    for tab in page.find_tables().tables:
        for r in tab.extract():
            cells = [(c or "").strip().replace("\n", " ") for c in r]
            if not any(cells):
                continue
            first = cells[0]
            # 表頭列
            if first.startswith("Ball#") or "Ball Reset" in " ".join(cells) or first.startswith("State"):
                continue
            # 分組標題列：只有第一欄有字，其餘空
            if first and not any(cells[1:]):
                group = first
                continue
            # 資料列：第一欄必須是純數字
            if re.fullmatch(r"\d+", first):
                rows.append({
                    "pin":      int(first),
                    "name":     cells[1],
                    "type":     cells[2],
                    "reset":    cells[3],
                    "pull":     cells[4],
                    "drive_mA": cells[5],
                    "supply":   cells[6],
                    "group":    group,
                })

rows.sort(key=lambda x: x["pin"])

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["pin", "name", "type", "reset", "pull", "drive_mA", "supply", "group"])
    w.writeheader()
    w.writerows(rows)

# 驗證
pins = [r["pin"] for r in rows]
print(f"抽出 {len(rows)} 列，pin 範圍 {min(pins)}~{max(pins)}")
missing = sorted(set(range(1, 129)) - set(pins))
dup = sorted(p for p in set(pins) if pins.count(p) > 1)
print(f"缺號: {missing if missing else '無'}")
print(f"重複: {dup if dup else '無'}")

from collections import Counter
print("\n=== 依 group 統計 ===")
for g, n in Counter(r["group"] for r in rows).most_common():
    print(f"  {g:24s} {n:3d}")

print("\n=== 依 type 統計 ===")
for t, n in Counter(r["type"] for r in rows).most_common():
    print(f"  {t:8s} {n:3d}")

print("\n=== 依 Power Supply 統計（電源域）===")
for s, n in Counter(r["supply"] for r in rows).most_common():
    print(f"  {s:16s} {n:3d}")

print(f"\n寫入 {OUT}")
