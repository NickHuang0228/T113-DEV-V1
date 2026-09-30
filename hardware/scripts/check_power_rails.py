#!/usr/bin/env python3
"""從 netlist 驗證 RY1303 三路 buck 的接線與分壓值。

為什麼需要這支：原理圖階段最危險的錯誤是「值對、結構對、電源符號對，
只有回授那條線接到長得很像的另一支腳」—— 眼睛掃不出來，只有 netlist 看得見。
而它的後果是兩路電源同時失控（一路沒回授、另一路拿別人的電壓當目標）。

用法：
    python hardware/scripts/check_power_rails.py

會自己呼叫 kicad-cli 產生 netlist。若 kicad-cli 不在 PATH，用環境變數指定：
    KICAD_CLI=D:/KiCAD/bin/kicad-cli.exe python hardware/scripts/check_power_rails.py

規格來源：docs/design/011-power-tree.md §2.2（腳位）、§2.3（分壓）、§2.4（電容）
"""
import os
import re
import io
import sys
import shutil
import subprocess
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCH = os.path.join(ROOT, "T113-DEV-V1.kicad_sch")

# RY1303 三通道。腳位出自 011 §2.2，分壓目標與容許範圍出自 §2.3。
#   (通道, EN腳, SW腳, FB腳, 期望軌, 容許範圍, 輸出電容最少幾顆)
CHANNELS = [
    ("CH1", "9",  "11", "14", "+0V9", (None,  None),  1),
    ("CH2", "8",  "6",  "3",  "+1V5", (1.425, 1.575), 1),
    ("CH3", "18", "20", "2",  "+3V3", (2.97,  3.63),  2),
]
VREF = 0.6          # RY1303 的 FB 參考電壓
REG = "U1"          # RY1303 的 designator


def find_cli():
    cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if cli and os.path.exists(cli):
        return cli
    for p in (r"D:/KiCAD/bin/kicad-cli.exe",
              r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"):
        if os.path.exists(p):
            return p
    sys.exit("找不到 kicad-cli —— 用環境變數 KICAD_CLI 指定路徑")


def export_netlist():
    out = os.path.join(tempfile.gettempdir(), "t113_rails.net")
    r = subprocess.run([find_cli(), "sch", "export", "netlist",
                        "--format", "kicadsexpr", "-o", out, SCH],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit(f"netlist 匯出失敗：\n{r.stderr}")
    return out


def parse(path):
    s = io.open(path, encoding="utf-8").read()
    comps = dict(re.findall(
        r'\(comp\s*\n\s*\(ref "([^"]+)"\)\s*\n\s*\(value "([^"]*)"\)', s))
    seg = s[s.index("\t(nets"):]
    nets = {}
    for name, body in re.findall(
            r'\(net\s*\n\s*\(code "\d+"\)\s*\n\s*\(name "([^"]*)"\)(.*?)'
            r'(?=\n\t\t\(net\n|\Z)', seg, re.S):
        nets[name] = re.findall(
            r'\(ref "([^"]+)"\)\s*\n\s*\(pin "([^"]+)"\)', body)
    return comps, nets


def ohm(v):
    """'25.5K' → 25500.0；解析不出來回 None。"""
    t = (v or "").upper().replace("Ω", "").replace("R", ".")
    t = t.replace("K", "e3").replace("M", "e6")
    try:
        return float(t)
    except ValueError:
        return None


def main():
    comps, nets = parse(export_netlist())
    net_of = lambda ref, pin: next(
        (n for n, v in nets.items() if (ref, pin) in v), None)

    fails = []
    for ch, en, sw, fb, rail, (lo, hi), ncap in CHANNELS:
        print(f"\n{ch}  {rail}")

        # ① 電感：SW 腳 → 電感 → 期望的軌
        swnet = net_of(REG, sw)
        L = next((r for r, _ in nets.get(swnet, []) if r.startswith("L")), None)
        lrail = next((n for n, v in nets.items()
                      if L and any(x[0] == L for x in v) and n != swnet), None)
        ok = (lrail == rail)
        print(f"  SW   {REG}.{sw} → {L or '✗無電感'} → {lrail or '?'}"
              f"{'' if ok else '   ✗ 電感輸出不在期望的軌'}")
        if not ok:
            fails.append(f"{ch} 電感輸出接到 {lrail}，應為 {rail}")

        # ② 分壓：R_top 在軌上、R_bot 在 GND，兩者中點接 FB
        fbnet = net_of(REG, fb)
        rs = [r for r, _ in nets.get(fbnet, []) if r.startswith("R")]
        top = [r for r in rs if any(x[0] == r for x in nets.get(rail, []))]
        bot = [r for r in rs if any(x[0] == r for x in nets.get("GND", []))]
        if len(top) == 1 and len(bot) == 1:
            rt, rb = ohm(comps.get(top[0])), ohm(comps.get(bot[0]))
            if rt and rb:
                vout = VREF * (1 + rt / rb)
                inr = lo is None or lo <= vout <= hi
                print(f"  FB   {REG}.{fb} ← {top[0]}({comps[top[0]]}) / "
                      f"{bot[0]}({comps[bot[0]]}) → {vout:.3f} V"
                      f"{'' if inr else f'   ✗ 超出 {lo}~{hi} V'}")
                if not inr:
                    fails.append(f"{ch} 輸出 {vout:.3f} V 超出 {lo}~{hi} V")
            else:
                print(f"  FB   ✗ 阻值解析失敗")
                fails.append(f"{ch} 分壓阻值解析失敗")
        else:
            print(f"  FB   {REG}.{fb} ← ✗ 分壓結構異常（top={top} bot={bot}）")
            fails.append(f"{ch} 分壓沒有正確接到 {rail} 與 GND —— "
                         f"最常見的原因是 FB 接到別的通道的腳")

        # ③ 輸出電容
        caps = [r for r, _ in nets.get(rail, []) if r.startswith("C")]
        cok = len(caps) >= ncap
        print(f"  C    {caps or '無'}（需 ≥{ncap}）{'' if cok else '   ✗'}")
        if not cok:
            fails.append(f"{ch} 輸出電容不足（{len(caps)}/{ncap}）")

        # ④ EN 不可浮接（datasheet 明寫）
        ennet = net_of(REG, en)
        eok = ennet and len(nets.get(ennet, [])) >= 2
        print(f"  EN   {REG}.{en} → {ennet or '✗ 浮接'}{'' if eok else '   ✗'}")
        if not eok:
            fails.append(f"{ch} EN 浮接 —— datasheet 明寫不可")

    # 跨頁訊號在對手方那一頁畫好之前，本頁只會看到一個連接點 —— 那不是錯。
    # 這裡列出「已知還在等其他頁」的 net，畫到那一頁時要從這裡移除。
    PENDING_CROSS_SHEET = {
        "USB_EN":      "等主晶片頁的 T113 GPIO",
        "USB_OC_N":    "等主晶片頁的 T113 GPIO",
        "SYS_RESET_N": "等主晶片頁的 T113 pin 27",
    }
    lone = [n for n, v in nets.items()
            if len(v) < 2 and not n.startswith("unconnected-")]
    waiting = [n for n in lone if n in PENDING_CROSS_SHEET]
    real = [n for n in lone if n not in PENDING_CROSS_SHEET]
    if waiting:
        print("\n· 跨頁訊號（尚未接上對手方，非錯誤）：")
        for n in waiting:
            print(f"    {n} —— {PENDING_CROSS_SHEET[n]}")
    if real:
        print(f"\n⚠ 只有一個連接點的 net：{real}")
        fails.append(f"孤立 net：{real}")

    print("\n" + "=" * 52)
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        sys.exit(f"\n{len(fails)} 項未通過")
    print("  ✓ 三路 buck 全部通過")


if __name__ == "__main__":
    main()
