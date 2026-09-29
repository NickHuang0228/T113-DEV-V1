#!/usr/bin/env python3
"""從 netlist 驗證電源頁：RY1303 三路 buck、兩顆 AP2112K LDO、被動件 footprint。

為什麼需要這支：原理圖階段最危險的錯誤是「值對、結構對、電源符號對，
只有回授那條線接到長得很像的另一支腳」—— 眼睛掃不出來，只有 netlist 看得見。
而它的後果是兩路電源同時失控（一路沒回授、另一路拿別人的電壓當目標）。

用法：
    python hardware/scripts/check_power_rails.py

會自己呼叫 kicad-cli 產生 netlist。若 kicad-cli 不在 PATH，用環境變數指定：
    KICAD_CLI=D:/KiCAD/bin/kicad-cli.exe python hardware/scripts/check_power_rails.py

規格來源：docs/design/011-power-tree.md §2.2（腳位）、§2.3（分壓）、§2.4（電容）、§3（LDO）
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
BUCK_CAP = "22uF"   # buck 輸出電容，§2.4

# 兩顆 AP2112K-1.8，出自 011 §3。腳位：1 VIN、2 GND、3 EN、5 VOUT（SOT-25）。
# EN 內建 3 MΩ 下拉，浮接 = 關機，所以必須接 VIN。
#   (designator, 輸入軌, 輸出軌)
LDOS = [
    ("U2", "+3V3", "+1V8_SOC"),
    ("U3", "+3V3", "+1V8_HDMI"),
]
LDO_CAP = "1uF"     # C_in / C_out，DS Note 4

# 被動件的 footprint 必須來自對應的庫。
# 之前兩次誤選（電感 → PQFP-160、電容 → SOIC-8）都是複製元件時一起帶過去的。
FP_LIB = {"C": "Capacitor_SMD:", "R": "Resistor_SMD:", "L": "Inductor_SMD:"}


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
    fps = {}
    for block in re.split(r'\(comp\s*\n', s[:s.index("\t(nets")])[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', block)
        fp = re.search(r'\(footprint "([^"]*)"\)', block)
        if ref:
            fps[ref.group(1)] = fp.group(1) if fp else ""
    seg = s[s.index("\t(nets"):]
    nets = {}
    for name, body in re.findall(
            r'\(net\s*\n\s*\(code "\d+"\)\s*\n\s*\(name "([^"]*)"\)(.*?)'
            r'(?=\n\t\t\(net\n|\Z)', seg, re.S):
        nets[name] = re.findall(
            r'\(ref "([^"]+)"\)\s*\n\s*\(pin "([^"]+)"\)', body)
    return comps, fps, nets


def is_cap(v, target):
    """'1uF' / '1µF' / '1u' 視為相同。"""
    norm = lambda x: (x or "").replace("µ", "u").lower().rstrip("f")
    return norm(v) == norm(target)


def ohm(v):
    """'25.5K' → 25500.0；解析不出來回 None。"""
    t = (v or "").upper().replace("Ω", "").replace("R", ".")
    t = t.replace("K", "e3").replace("M", "e6")
    try:
        return float(t)
    except ValueError:
        return None


def main():
    comps, fps, nets = parse(export_netlist())
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

        # ③ 輸出電容（只數 22µF —— +3V3 上還掛著 LDO 的 1µF，不能混算）
        caps = [r for r, _ in nets.get(rail, [])
                if r.startswith("C") and is_cap(comps.get(r), BUCK_CAP)]
        cok = len(caps) >= ncap
        print(f"  C    {caps or '無'}（需 ≥{ncap} 顆 {BUCK_CAP}）"
              f"{'' if cok else '   ✗'}")
        if not cok:
            fails.append(f"{ch} 輸出電容不足（{len(caps)}/{ncap}）")

        # ④ EN 不可浮接（datasheet 明寫）
        ennet = net_of(REG, en)
        eok = ennet and len(nets.get(ennet, [])) >= 2
        print(f"  EN   {REG}.{en} → {ennet or '✗ 浮接'}{'' if eok else '   ✗'}")
        if not eok:
            fails.append(f"{ch} EN 浮接 —— datasheet 明寫不可")

    # ── LDO ──────────────────────────────────────────
    for ref, vin, vout in LDOS:
        print(f"\n{ref}  {comps.get(ref, '✗ 不存在')}  {vin} → {vout}")
        if ref not in comps:
            fails.append(f"{ref} 不存在")
            continue
        for pin, name, want in (("1", "VIN", vin), ("3", "EN", vin),
                                ("2", "GND", "GND"), ("5", "VOUT", vout)):
            got = net_of(ref, pin)
            ok = got == want
            print(f"  {name:<4} {ref}.{pin} → {got or '✗ 浮接'}"
                  f"{'' if ok else f'   ✗ 應為 {want}'}")
            if not ok:
                hint = "（EN 內建下拉，浮接 = 關機）" if name == "EN" else ""
                fails.append(f"{ref} {name} 接到 {got}，應為 {want}{hint}")
        caps = [r for r, _ in nets.get(vout, [])
                if r.startswith("C") and is_cap(comps.get(r), LDO_CAP)
                and any(x[0] == r for x in nets.get("GND", []))]
        print(f"  Cout {caps or '無'}（需 ≥1 顆 {LDO_CAP} 到 GND）"
              f"{'' if caps else '   ✗'}")
        if not caps:
            fails.append(f"{ref} 輸出 {vout} 缺 {LDO_CAP} 電容")

    # 輸入電容：LDO 的 VIN 共用 +3V3，netlist 分不出哪顆靠哪顆，只能驗總數
    for vin in {v for _, v, _ in LDOS}:
        n_ldo = sum(1 for _, v, _ in LDOS if v == vin)
        caps = [r for r, _ in nets.get(vin, [])
                if r.startswith("C") and is_cap(comps.get(r), LDO_CAP)]
        ok = len(caps) >= n_ldo
        print(f"\nCin  {vin} 上的 {LDO_CAP}：{caps or '無'}（需 ≥{n_ldo}）"
              f"{'' if ok else '   ✗'}")
        if not ok:
            fails.append(f"{vin} 上的 LDO 輸入電容不足（{len(caps)}/{n_ldo}）")

    outs = [o for _, _, o in LDOS]
    if len(set(outs)) != len(outs):
        fails.append(f"LDO 輸出軌重複 {outs} —— ADV7511 需要專屬 LDO（011 §3）")

    # ── 被動件 footprint ─────────────────────────────
    bad, empty = [], []
    for ref, fp in sorted(fps.items()):
        lib = FP_LIB.get(re.match(r"[A-Z]+", ref).group())
        if lib is None or ref.startswith("#"):
            continue
        if not fp:
            empty.append(ref)
        elif not fp.startswith(lib):
            bad.append(f"{ref}={fp}")
    if bad:
        print(f"\n✗ 被動件 footprint 不在對應的庫：")
        for b in bad:
            print(f"    {b}")
        fails.append(f"footprint 錯庫 {len(bad)} 顆（應為 {'/'.join(FP_LIB.values())}）")
    if empty:
        print(f"\n⚠ 尚未指定 footprint（不算失敗）：{empty}")

    lone = [n for n, v in nets.items()
            if len(v) < 2 and not n.startswith("unconnected-")]
    if lone:
        print(f"\n⚠ 只有一個連接點的 net：{lone}")
        fails.append(f"孤立 net：{lone}")

    print("\n" + "=" * 52)
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        sys.exit(f"\n{len(fails)} 項未通過")
    print("  ✓ 三路 buck、兩顆 LDO、被動件 footprint 全部通過")


if __name__ == "__main__":
    main()
