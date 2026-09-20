#!/usr/bin/env python3
"""原理圖檢查器 —— 對照設計文件驗證 KiCad 原理圖。

作法：用 kicad-cli 匯出 netlist（讓 KiCad 自己做 net 解析，
我們不碰 wire/junction/label 的幾何，那是最容易出錯的部分），
再對 netlist 套規則。

用法：
    python hardware/scripts/check_schematic.py
    python hardware/scripts/check_schematic.py --sch <path.kicad_sch>

規則定義在 rules_t113.py。新增檢查請改那份，不要改這支。
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
sys.path.insert(0, HERE)

KICAD_CLI_CANDIDATES = [
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
    "kicad-cli",
]


def find_cli():
    for c in KICAD_CLI_CANDIDATES:
        if os.path.exists(c):
            return c
        w = shutil.which(c)
        if w:
            return w
    sys.exit("找不到 kicad-cli")


def export_netlist(sch):
    out = os.path.join(tempfile.mkdtemp(), "net.net")
    r = subprocess.run(
        [find_cli(), "sch", "export", "netlist", sch, "-o", out, "--format", "kicadsexpr"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit(f"匯出 netlist 失敗：\n{r.stdout}\n{r.stderr}")
    return io.open(out, encoding="utf-8", errors="replace").read()


def parse_netlist(txt):
    """回傳 (comps, nets)
    comps: {ref: {"value":.., "footprint":.., "lib":..}}
    nets:  {netname: [(ref, pin), ...]}
    """
    comps = {}
    for m in re.finditer(r'\(comp\s+\(ref\s+"([^"]+)"\)(.*?)(?=\(comp\s+\(ref|\(libparts|\Z)', txt, re.S):
        ref, body = m.group(1), m.group(2)
        val = re.search(r'\(value\s+"([^"]*)"\)', body)
        fp = re.search(r'\(footprint\s+"([^"]*)"\)', body)
        comps[ref] = {
            "value": val.group(1) if val else "",
            "footprint": fp.group(1) if fp else "",
        }
    nets = {}
    for m in re.finditer(r'\(net\s+\(code\s+"?\d+"?\)\s*\(name\s+"([^"]*)"\)(.*?)(?=\(net\s+\(code|\Z)', txt, re.S):
        name, body = m.group(1), m.group(2)
        pins = re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)\s*\(pin\s+"([^"]+)"\)', body)
        nets[name] = pins
    return comps, nets


def build_pinmap(nets):
    """{(ref, pin): netname}"""
    pm = {}
    for n, pins in nets.items():
        for ref, pin in pins:
            pm[(ref, pin)] = n
    return pm


def norm_net(n):
    """把 KiCad 的階層前綴與自動命名去掉，方便比對。"""
    n = n.split("/")[-1]
    return n.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sch", default=os.path.join(HW, "T113-DEV-V1.kicad_sch"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.sch):
        sys.exit(f"找不到原理圖：{args.sch}")

    txt = export_netlist(args.sch)
    comps, nets = parse_netlist(txt)
    pinmap = build_pinmap(nets)

    import rules_t113
    findings = rules_t113.run(comps, nets, pinmap, norm_net)

    err = [f for f in findings if f[0] == "ERR"]
    warn = [f for f in findings if f[0] == "WARN"]
    info = [f for f in findings if f[0] == "INFO"]

    print(f"原理圖：{os.path.relpath(args.sch, os.path.dirname(HW))}")
    print(f"元件 {len(comps)} 個 · net {len(nets)} 條\n")

    if not comps:
        print("（圖上還沒有元件，先畫再檢查）")
        return 0

    for tag, lst, mark in (("錯誤", err, "✗"), ("警告", warn, "⚠"), ("提示", info, "·")):
        if lst:
            print(f"── {tag} {len(lst)} 項 " + "─" * 40)
            for _, rule, msg in lst:
                print(f"  {mark} [{rule}] {msg}")
            print()

    if not findings:
        print("✓ 全部規則通過")
    else:
        print(f"合計：錯誤 {len(err)} · 警告 {len(warn)} · 提示 {len(info)}")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
