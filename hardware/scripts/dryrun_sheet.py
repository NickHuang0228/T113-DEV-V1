#!/usr/bin/env python3
"""乾跑一支 gen_*_sheet.py：不碰任何檔案，只檢查它會生出什麼。

為什麼需要：KiCad 開著的時候 guard_kicad_closed() 會硬性中止，
但生成器的座標算錯、designator 撞號、net 打錯字這些問題，
不需要寫檔就能先抓出來。

檢查項目
  ① 非格點座標        線頭差 0.01mm 也是斷的，而圖上看不出來
  ② designator 撞號    多 unit 的同一顆 IC 例外
  ③ designator 跳號    BOM 複核時會以為掉件
  ④ 浮空線頭          線的一端沒有任何東西（最常見的「看起來接了其實沒連」）
  ⑤ net 清單          跟其他頁人工比對用

用法：
    python hardware/scripts/dryrun_sheet.py gen_net_sheet
    python hardware/scripts/dryrun_sheet.py gen_net_sheet gen_display_sheet
"""
import io
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import schlib                                                    # noqa: E402

MULTI_UNIT_OK = {"U7", "U8", "U6"}      # 多 unit 的 IC，reference 本來就重複


def dryrun(modname):
    captured = []

    def fake_init(self, path, project_root=None):
        self.path = path
        self.sheet = "/DRYRUN/SHEET"
        self.out = []
        self.stat = {}

    orig_init, orig_append = schlib.Page.__init__, schlib.append_to_sheet
    schlib.Page.__init__ = fake_init
    schlib.append_to_sheet = lambda path, blocks: captured.append((path, list(blocks)))
    try:
        mod = __import__(modname)
        mod.main()
    finally:
        schlib.Page.__init__ = orig_init
        schlib.append_to_sheet = orig_append

    if not captured:
        return ["✗ 生成器沒有呼叫 append_to_sheet / commit"]
    txt = "".join(captured[0][1])
    errs = []

    # ① 格點
    off = set()
    for m in re.finditer(r"\(xy (-?[\d.]+) (-?[\d.]+)\)", txt):
        for v in m.groups():
            f = float(v)
            if abs(round(f / 1.27) * 1.27 - f) > 1e-6:
                off.add(v)
    if off:
        errs.append(f"✗ 非格點座標 {sorted(off)}")

    # ②③ designator
    refs = [r for r in re.findall(r'\(reference "([^"]+)"', txt)
            if not r.startswith("#")]
    dup = sorted({r for r in refs if refs.count(r) > 1} - MULTI_UNIT_OK)
    if dup:
        errs.append(f"✗ designator 撞號 {dup}")
    byp = defaultdict(list)
    for r in set(refs):
        m = re.match(r"([A-Za-z_]+)(\d+)$", r)
        if m:
            byp[m.group(1)].append(int(m.group(2)))
    gaps = {}
    for pre, nums in byp.items():
        lo, hi = min(nums), max(nums)
        miss = sorted(set(range(lo, hi + 1)) - set(nums))
        if miss:
            gaps[pre] = miss
    if gaps:
        errs.append(f"· designator 跳號（本頁範圍內）{gaps}")

    # ④ 浮空線頭：線的端點必須碰到另一條線、接點、標籤或元件接腳
    ends = Counter()
    for m in re.finditer(r"\(xy (-?[\d.]+) (-?[\d.]+)\) \(xy (-?[\d.]+) (-?[\d.]+)\)", txt):
        a, b, c, d = (float(x) for x in m.groups())
        ends[(a, b)] += 1
        ends[(c, d)] += 1
    anchors = set()
    for pat in (r"\(junction\s*\n\s*\(at (-?[\d.]+) (-?[\d.]+)\)",
                r"\(global_label \"[^\"]+\"[\s\S]{0,120}?\(at (-?[\d.]+) (-?[\d.]+) \d+\)",
                r"\(no_connect\s*\n\s*\(at (-?[\d.]+) (-?[\d.]+)\)"):
        for m in re.finditer(pat, txt):
            anchors.add((float(m.group(1)), float(m.group(2))))
    # 元件接腳位置無法只靠文字還原（要查符號庫），所以只報「端點只出現一次
    # 又沒有 junction/label/NC」的情形，由人工確認那頭是不是元件接腳。
    lone = sorted(pt for pt, n in ends.items() if n == 1 and pt not in anchors)
    print(f"  端點總數 {len(ends)}　單一端點（應為元件接腳或電源符號）{len(lone)}")

    # ⑤ net
    labels = sorted(set(re.findall(r'\(global_label "([^"]+)"', txt)))
    pw = re.findall(r'\(lib_id "power:([^"]+)"\)[\s\S]{0,500}?\(property "Value" "([^"]+)"', txt)
    print(f"  元件 {len(set(refs))} 顆: {sorted(set(refs))}")
    print(f"  全域標籤 {len(labels)}: {labels}")
    print(f"  電源 net: {dict(Counter(v for _, v in pw))}")
    return errs


def main():
    mods = sys.argv[1:] or ["gen_net_sheet"]
    bad = 0
    for m in mods:
        print(f"\n═══ {m} ═══")
        errs = dryrun(m)
        for e in errs:
            print(" ", e)
            if e.startswith("✗"):
                bad += 1
        if not any(e.startswith("✗") for e in errs):
            print("  ✓ 幾何與編號檢查通過")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
