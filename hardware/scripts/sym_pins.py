#!/usr/bin/env python3
"""印出一顆符號的腳位與座標 —— 寫生成器之前一定要先看這個。

生成器要自己算「這支腳在原理圖上的座標」，公式是
    原理圖座標 = 元件擺放座標 + (符號座標 dx, -符號座標 dy)
（符號的 Y 軸向上，原理圖向下，所以 dy 要變號。）

算錯的後果是線頭差幾 mm 卻完全看不出來 —— 圖上線還在，netlist 裡斷了。

用法：
    python hardware/scripts/sym_pins.py CH340N
    python hardware/scripts/sym_pins.py Connector:Micro_SD_Card_Det1
    python hardware/scripts/sym_pins.py --list USB_A
"""
import glob
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SYMDIRS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\share\kicad\symbols"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\9.0\share\kicad\symbols"),
    r"C:\Program Files\KiCad\10.0\share\kicad\symbols",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "symbols"),
]

PIN_RE = re.compile(
    r'\(pin (\w+) \w+\s*\n'
    r'(?:[^\n]*\n)*?\s*\(at (-?[\d.]+) (-?[\d.]+) (\d+)\)\s*\n'
    r'(?:[^\n]*\n)*?\s*\(length ([\d.]+)\)'
    r'[\s\S]*?\(name "([^"]*)"'
    r'[\s\S]*?\(number "([^"]*)"')


def libs():
    for d in SYMDIRS:
        if os.path.isdir(d):
            for f in sorted(glob.glob(os.path.join(d, "*.kicad_sym"))):
                yield f


def block(txt, name):
    i = txt.find('\n\t(symbol "%s"\n' % name)
    if i < 0:
        i = txt.find('\n\t(symbol "%s"' % name)
        if i < 0:
            return None
    j = txt.find('\n\t(symbol "', i + 10)
    return txt[i:j if j > 0 else len(txt)]


def find(name, _seen=None):
    """找符號。遇到 (extends "X") 要跳到母符號取腳位。

    KiCad 的符號可以繼承 —— CH340N 就是從 CH340C 繼承的。
    只看自己的區塊會得到「共 0 支腳」這種安靜的錯答案。
    """
    _seen = _seen or set()
    lib, _, sym = name.rpartition(":")
    for f in libs():
        if lib and os.path.basename(f)[:-10] != lib:
            continue
        t = io.open(f, encoding="utf-8", errors="replace").read()
        b = block(t, sym)
        if not b:
            continue
        this_lib = os.path.basename(f)[:-10]
        ext = re.search(r'\(extends "([^"]+)"\)', b)
        if ext and ext.group(1) not in _seen:
            _seen.add(sym)
            _, pb = find(f"{this_lib}:{ext.group(1)}", _seen)
            if pb:
                print(f"  （腳位繼承自 {ext.group(1)}）")
                return this_lib, b + pb
        return this_lib, b
    return None, None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--list":
        pat = sys.argv[2].upper()
        for f in libs():
            t = io.open(f, encoding="utf-8", errors="replace").read()
            n = [s for s in re.findall(r'^\t\(symbol "([^"]+)"', t, re.M)
                 if pat in s.upper()]
            if n:
                print(f"{os.path.basename(f)[:-10]:28s} {n}")
        return

    name = sys.argv[1]
    lib, b = find(name)
    if not b:
        sys.exit(f"✗ 找不到符號 {name}（試試 --list）")
    print(f"=== {lib}:{name.rpartition(':')[2]}")
    for k in ("Footprint", "Description", "ki_fp_filters"):
        m = re.search(r'\(property "%s" "([^"]*)"' % k, b)
        if m and m.group(1):
            print(f"  {k}: {m.group(1)}")
    units = sorted(set(re.findall(r'\(symbol "[^"]*_(\d+)_\d+"', b)), key=int)
    print(f"  units: {units}（0 = 共用圖形，實際 unit 從 1 起算）")
    print(f"\n  {'pin':>4} {'name':<16} {'type':<16} {'符號座標':<18} rot  len")
    rows = list(PIN_RE.finditer(b))
    for m in rows:
        typ, dx, dy, rot, ln, nm, num = m.groups()
        print(f"  {num:>4} {nm:<16} {typ:<16} ({dx:>7}, {dy:>7})  {rot:>3}  {ln}")
    print(f"\n  共 {len(rows)} 支腳")
    print("  原理圖座標 = (擺放 x + dx, 擺放 y - dy)")


if __name__ == "__main__":
    main()
