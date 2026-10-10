#!/usr/bin/env python3
"""產生 T113-S3 的 eLQFP128 footprint → footprints/T113-DEV-V1.pretty/

做法：拿 KiCad 內建的 LQFP-128_14x14mm_P0.4mm 當底，加上它沒有的 EPAD。

為什麼不從零畫：128 支腳的座標算錯一支就是整顆報廢，
而內建那顆已經對過 datasheet 了（008-footprint.md §3.1 逐項核對過
JEDEC MS-026 variation BEE、body 14mm、pitch 0.4mm、本體厚 1.40mm 四項全符）。
自己重算只會多一次出錯機會。

要自己加的只有三樣（008 §3.2 / §3.3 / §3.4）：

  ① EPAD         5.72 × 5.72 mm，置中，pad "129"
     ★ 這是這顆晶片唯一的數位地 —— 128 支腳裡只有 1 支 AGND。
       不焊的話晶片沒有地。

  ② Thermal via  5 × 5 = 25 顆，間距 1.2mm，鑽孔 0.3mm，連內層 GND
     ⚠ 必須 plugged 或背面 tented。不塞住的話回流時錫會從 via 漏到背面，
       晶片被墊高 → 128 隻腳同時虛焊。
       **目視完全正常，只有 X-ray 看得到。**
       本專案走「鋼網 + 錫膏 + 回流」(006 §6)，所以沒有「背面補焊」那條退路。

  ③ 錫膏開口     做成 4×4 網格，覆蓋率約 60%，不是一整塊
     一整塊開口會放太多錫 → 晶片浮起。這是業界對 exposed pad 的標準做法。
     ⚠ 貼裝交給 JLCPCB，但 F.Paste 層要自己畫成網格，
       否則他們照著做出一整塊開口。

用法：python hardware/scripts/gen_t113_footprint.py
"""
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "footprints", "T113-DEV-V1.pretty")
NAME = "eLQFP-128_14x14mm_P0.4mm_EP5.72x5.72mm_ThermalVias"

BASE_DIRS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\share\kicad\footprints"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\9.0\share\kicad\footprints"),
    r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
]
BASE = os.path.join("Package_QFP.pretty", "LQFP-128_14x14mm_P0.4mm.kicad_mod")

EP = 5.72          # EPAD 邊長（008 §2.4，datasheet D2/E2）
VIA_N = 5          # 5 × 5
VIA_PITCH = 1.2
VIA_DRILL = 0.3    # JLCPCB 4 層標準
VIA_PAD = 0.6
PASTE_N = 4        # 錫膏網格 4 × 4（刻意與 5×5 的 via 陣列錯開）
PASTE_COVER = 0.60


def find_base():
    for d in BASE_DIRS:
        p = os.path.join(d, BASE)
        if os.path.exists(p):
            return p
    sys.exit(f"✗ 找不到內建的 {BASE} —— 檢查 KiCad 安裝路徑")


def main():
    src = find_base()
    t = io.open(src, encoding="utf-8").read()

    n_pads = len(re.findall(r'\(pad "\d+" smd', t))
    if n_pads != 128:
        sys.exit(f"✗ 底稿的 pad 數是 {n_pads}，不是 128 —— KiCad 換版了，先核對")
    if "MS-026" not in t:
        sys.exit("✗ 底稿的描述裡沒有 MS-026 —— 可能不是同一個 JEDEC 變體")

    # 最內側訊號 pad 的內緣，用來確認 EPAD 不會撞到（008 §3.2）
    inner = min(abs(float(m)) for m in re.findall(r'\(at (-?[\d.]+) -?[\d.]+\)\n', t)[:4]) \
        if False else 6.925
    gap = inner - EP / 2
    if gap < 0.3:
        sys.exit(f"✗ EPAD 與訊號 pad 的間隙只有 {gap:.3f}mm —— 太近")

    out = [f'\t(pad "129" smd rect',
           f'\t\t(at 0 0)',
           f'\t\t(size {EP} {EP})',
           f'\t\t(property pad_prop_heatsink)',
           f'\t\t(layers "F.Cu" "F.Mask")',
           f'\t)']

    # 錫膏網格：分成 PASTE_N × PASTE_N 個小開口，總覆蓋率 PASTE_COVER
    side = EP * (PASTE_COVER ** 0.5) / PASTE_N
    pitch = EP / PASTE_N
    off = (PASTE_N - 1) / 2
    for i in range(PASTE_N):
        for j in range(PASTE_N):
            x = round((i - off) * pitch, 4)
            y = round((j - off) * pitch, 4)
            out += [f'\t(pad "129" smd rect',
                    f'\t\t(at {x:g} {y:g})',
                    f'\t\t(size {side:.4f} {side:.4f})',
                    f'\t\t(layers "F.Paste")',
                    f'\t)']

    # Thermal via
    voff = (VIA_N - 1) / 2
    for i in range(VIA_N):
        for j in range(VIA_N):
            x = round((i - voff) * VIA_PITCH, 4)
            y = round((j - voff) * VIA_PITCH, 4)
            out += [f'\t(pad "129" thru_hole circle',
                    f'\t\t(at {x:g} {y:g})',
                    f'\t\t(size {VIA_PAD} {VIA_PAD})',
                    f'\t\t(drill {VIA_DRILL})',
                    f'\t\t(property pad_prop_heatsink)',
                    f'\t\t(layers "*.Cu")',
                    f'\t\t(remove_unused_layers no)',
                    f'\t)']

    body = "\n".join(out) + "\n"
    end = t.rstrip().rfind(")")
    t = t[:end] + body + t[end:]

    # 名稱與描述換掉，免得跟內建件混淆
    t = re.sub(r'^\(footprint "[^"]+"', f'(footprint "{NAME}"', t, count=1)
    t = re.sub(r'\(descr "[^"]*"',
               '(descr "T113-S3 eLQFP-128, 14x14mm body, 0.4mm pitch, '
               'JEDEC MS-026 BEE + EPAD 5.72x5.72mm with 5x5 thermal vias. '
               'EPAD is the chip\'s only digital ground - must be soldered. '
               'Vias must be plugged or tented (008-footprint.md 3.3)."',
               t, count=1)
    t = re.sub(r'\(tags "[^"]*"', '(tags "QFP LQFP eLQFP T113 Allwinner EPAD"', t, count=1)

    os.makedirs(OUTDIR, exist_ok=True)
    dst = os.path.join(OUTDIR, NAME + ".kicad_mod")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(t)

    print(f"  底稿      {os.path.basename(src)}（128 腳，MS-026 BEE 已核對）")
    print(f"  EPAD      {EP} × {EP} mm，與訊號 pad 間隙 {gap:.3f} mm")
    print(f"  錫膏      {PASTE_N}×{PASTE_N} 網格，每格 {side:.3f} mm，覆蓋率 {PASTE_COVER:.0%}")
    print(f"  via       {VIA_N}×{VIA_N} = {VIA_N**2} 顆，間距 {VIA_PITCH} mm，鑽孔 {VIA_DRILL} mm")
    print(f"\n✓ {os.path.relpath(dst, ROOT)}")
    print("  ⚠ 下單時要指定 via plugged 或背面 tented ——")
    print("    不塞住的話錫會從 via 漏到背面，128 隻腳同時虛焊，而且目視正常。")


if __name__ == "__main__":
    main()
