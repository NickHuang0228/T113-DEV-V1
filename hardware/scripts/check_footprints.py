#!/usr/bin/env python3
"""驗證每顆元件的「符號腳號」都能在它的 footprint 上找到對應焊盤。

★ 為什麼要有這支

  ERC 只驗原理圖內部（線有沒有接上、腳有沒有驅動），
  **它完全不看原理圖與 footprint 的對應關係。**
  所以下面這兩種錯 ERC 一個都抓不到，要到 Update PCB 才爆：

      TP9/TP10/TP11 的 footprint 被設成「繼電器」
        測試點只有 pad 1，繼電器的焊盤編號是 1A/1B/… —— 對不上。
        而「有沒有填 footprint」「footprint 檔案在不在」這兩個檢查都過得去。

      Y3 用 4 腳的 Crystal_GND24 符號，配 2 腳的 3215 封裝
        符號有 pin 3/4，footprint 只有 1/2。

  共通點：**原理圖上完全正常，BOM 也正常，只有把兩邊擺在一起比才看得出來。**

檢查四件事
  ① Footprint 欄位不是空的
  ② 那個 footprint 檔案真的存在（專案庫優先，再找 KiCad 內建庫）
  ③ 原理圖用到的每一個腳號，都能在 footprint 的焊盤編號裡找到
  ④ 自建的 footprint 庫，KiCad 自己解析得動
     （用 `kicad-cli fp export svg` 驗 —— 自建件是用程式產生的，
       格式壞掉的話要到 Update PCB 才發現，而那時已經在佈線了）

⚠ 反過來不檢查：footprint 有、但原理圖沒用到的焊盤是正常的
  （機構固定腳、未使用的 shield pad 等）。

用法：python hardware/scripts/check_footprints.py
"""
import io
import os
import re
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "T113-DEV-V1.kicad_sch")

CLI_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad-cli.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\9.0\bin\kicad-cli.exe"),
    r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    "kicad-cli",
]
FP_DIRS = [
    os.path.join(ROOT, "footprints"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\share\kicad\footprints"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\9.0\share\kicad\footprints"),
    r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
]


def find_cli():
    import shutil
    for c in CLI_CANDIDATES:
        if os.path.exists(c):
            return c
        w = shutil.which(c)
        if w:
            return w
    sys.exit("✗ 找不到 kicad-cli")


def netlist():
    out = os.path.join(tempfile.mkdtemp(), "n.net")
    r = subprocess.run([find_cli(), "sch", "export", "netlist", SCH,
                        "-o", out, "--format", "kicadsexpr"],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit(f"✗ 匯出 netlist 失敗\n{r.stdout}\n{r.stderr}")
    return io.open(out, encoding="utf-8", errors="replace").read()


def fp_pads(fp):
    """回傳 (焊盤編號集合, 檔案路徑)；找不到檔案時回傳 (None, None)。"""
    lib, _, name = fp.partition(":")
    for d in FP_DIRS:
        p = os.path.join(d, lib + ".pretty", name + ".kicad_mod")
        if os.path.exists(p):
            s = io.open(p, encoding="utf-8", errors="replace").read()
            return set(re.findall(r'\(pad "([^"]*)"', s)), p
    return None, None


def main():
    t = netlist()
    comps = {}
    for m in re.finditer(r'\(comp\s*\n\s*\(ref "([^"]+)"\)\s*\n\s*'
                         r'\(value "([^"]*)"\)'
                         r'(?:\s*\n\s*\(footprint "([^"]*)"\))?', t):
        comps[m.group(1)] = (m.group(2), m.group(3) or "")
    used = {}
    for m in re.finditer(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', t):
        used.setdefault(m.group(1), set()).add(m.group(2))

    real = {r: v for r, v in comps.items() if not r.startswith(("#", "FLG"))}
    empty, nofile, mismatch = [], [], []
    for ref, (val, fp) in sorted(real.items()):
        if not fp:
            empty.append((ref, val))
            continue
        pads, path = fp_pads(fp)
        if pads is None:
            nofile.append((ref, val, fp))
            continue
        miss = sorted(used.get(ref, set()) - pads)
        if miss:
            mismatch.append((ref, val, fp, miss, sorted(pads)[:10], len(pads)))

    print(f"檢查 {len(real)} 顆元件")
    bad = 0
    if empty:
        bad += 1
        print(f"\n✗ Footprint 欄位空白　{len(empty)} 顆")
        for r, v in empty:
            print(f"    {r}  {v}")
    if nofile:
        bad += 1
        print(f"\n✗ Footprint 檔案找不到　{len(nofile)} 顆")
        for r, v, f in nofile:
            print(f"    {r}  {v}　{f}")
    if mismatch:
        bad += 1
        print(f"\n✗ 腳號在 footprint 上不存在　{len(mismatch)} 顆"
              f"　← Update PCB 會卡在這裡")
        for r, v, f, miss, pads, n in mismatch:
            print(f"    {r}  {v}")
            print(f"       {f}")
            print(f"       原理圖用到但焊盤沒有的編號：{miss}")
            print(f"       footprint 的焊盤編號（前 10 個，共 {n} 個）：{pads}")
    # ④ 自建庫能不能被 KiCad 解析
    own = os.path.join(ROOT, "footprints")
    if os.path.isdir(own):
        import shutil
        for lib in sorted(d for d in os.listdir(own) if d.endswith(".pretty")):
            tmp = tempfile.mkdtemp()
            r = subprocess.run([find_cli(), "fp", "export", "svg",
                                os.path.join(own, lib), "-o", tmp],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            n_mod = len([f for f in os.listdir(os.path.join(own, lib))
                         if f.endswith(".kicad_mod")])
            n_svg = len([f for f in os.listdir(tmp) if f.endswith(".svg")])
            shutil.rmtree(tmp, ignore_errors=True)
            if r.returncode != 0 or n_svg < n_mod:
                bad += 1
                print(f"\n✗ 自建庫 {lib}　KiCad 解析不動"
                      f"（{n_mod} 個 .kicad_mod 只匯出 {n_svg} 個 SVG）")
                print((r.stderr or r.stdout)[:400])
            else:
                print(f"\n✓ 自建庫 {lib}　{n_mod} 個 footprint，KiCad 都解析得動")

    if not bad:
        print("\n✓ 全部元件的腳號都對得上焊盤 —— 可以 Update PCB")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
