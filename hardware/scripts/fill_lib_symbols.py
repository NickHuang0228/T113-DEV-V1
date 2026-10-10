#!/usr/bin/env python3
"""把每張圖紙用到的符號定義補進它自己的 (lib_symbols) 快取。

★ 為什麼非做不可

  .kicad_sch 裡的 (lib_symbols) 不是「方便離線開啟」的選配，
  它是 KiCad 判斷「這顆元件的腳在哪裡」的唯一依據。

  快取是空的 → KiCad 不知道任何一支腳的座標
             → 畫好的線一條都接不上
             → ERC 噴出成百上千個 unconnected_wire_endpoint / label_dangling

  第一次跑完八張子頁時就是這樣：圖看起來完全正常，ERC 1309 個違規。
  這是「看起來接了其實沒連」的最大一次 —— 整整八張圖。

★ 兩個容易做錯的地方

  ① 命名規則
     外層要寫完整 lib_id：  (symbol "Device:R" ...)
     內層的圖形/腳位子符號要去掉庫名： (symbol "R_0_1" ...)
     KiCad 是用「外層名稱去掉 lib: 之後」去配內層的，配不上就沒有腳。

  ② 繼承（extends）
     CH340N 是從 CH330N 繼承的，自己的區塊裡一支腳都沒有。
     快取如果照抄，等於存了一顆沒有腳的元件。
     這支腳本的做法是**攤平**：把母符號的圖形與腳位搬過來，
     重新命名成子符號的名字，屬性則以子符號的為準。

用法：
    python hardware/scripts/fill_lib_symbols.py            # 檢查
    python hardware/scripts/fill_lib_symbols.py --apply    # 補進去
    python hardware/scripts/fill_lib_symbols.py --apply --refresh
                                       # 整個重建（修 lib_symbol_mismatch）
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import guard_kicad_closed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SYMDIRS = [
    os.path.join(ROOT, "symbols"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\share\kicad\symbols"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\9.0\share\kicad\symbols"),
    r"C:\Program Files\KiCad\10.0\share\kicad\symbols",
]
_cache = {}


def sexp_block(txt, start):
    """從 start（必須指著一個 '('）切出完整的 S-expression。"""
    d, i = 0, start
    while True:
        c = txt[i]
        if c == '"':                       # 跳過字串，裡面的括號不算
            i += 1
            while txt[i] != '"':
                i += 2 if txt[i] == "\\" else 1
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return txt[start:i + 1]
        i += 1


def lib_text(lib):
    if lib not in _cache:
        for d in SYMDIRS:
            p = os.path.join(d, lib + ".kicad_sym")
            if os.path.exists(p):
                _cache[lib] = io.open(p, encoding="utf-8").read()
                break
        else:
            _cache[lib] = None
    return _cache[lib]


def top_symbol(txt, name):
    """找庫裡的頂層符號。

    ⚠ 縮排不能寫死成 tab：KiCad 內建庫用 tab，
      但本專案 gen_*_symbol.py 產生的庫用 2 個空格。
      只認 tab 的話，自建符號一律「找不到」—— 而那看起來像庫壞了。
    """
    m = re.search(r'\n[\t ]+\(symbol "%s"' % re.escape(name), txt)
    if not m:
        return None
    return sexp_block(txt, txt.index("(", m.start()))


def parts_of(block):
    """拆成 (屬性行們, 其餘設定行們, 內層子符號們, extends 的母符號名)。"""
    body = block[block.index("\n") + 1:]
    props, misc, subs, ext = [], [], [], None
    i = 0
    while i < len(body):
        j = body.find("(", i)
        if j < 0:
            break
        blk = sexp_block(body, j)
        head = blk[1:20].split()[0] if len(blk) > 2 else ""
        if head == "property":
            props.append(blk)
        elif head == "symbol":
            subs.append(blk)
        elif head == "extends":
            ext = re.search(r'\(extends "([^"]+)"\)', blk).group(1)
        else:
            misc.append(blk)
        i = j + len(blk)
    return props, misc, subs, ext


def prop_name(blk):
    return re.match(r'\(property "([^"]+)"', blk).group(1)


def build(lib, name, _depth=0):
    """組出快取用的 (symbol "lib:name" ...) 區塊，攤平繼承。"""
    if _depth > 4:
        raise SystemExit(f"✗ {lib}:{name} 的繼承太深，可能有循環")
    txt = lib_text(lib)
    if txt is None:
        return None, f"找不到符號庫 {lib}.kicad_sym"
    blk = top_symbol(txt, name)
    if blk is None:
        return None, f"{lib}.kicad_sym 裡沒有 {name}"
    props, misc, subs, ext = parts_of(blk)

    if ext:
        pblk = top_symbol(txt, ext)
        if pblk is None:
            return None, f"{name} 繼承自 {ext}，但庫裡找不到 {ext}"
        pprops, pmisc, psubs, pext = parts_of(pblk)
        if pext:                                   # 母符號自己也是繼承來的
            sub_lib, err = build(lib, ext, _depth + 1)
            if sub_lib is None:
                return None, err
            pprops, pmisc, psubs, _ = parts_of(sub_lib)
        misc = pmisc or misc
        subs = psubs
        # 子符號的屬性優先，母符號的補位
        own = {prop_name(p) for p in props}
        props = props + [p for p in pprops if prop_name(p) not in own]
        # 內層子符號要改名成「子符號的名字」，否則 KiCad 配不起來
        subs = [re.sub(r'^\(symbol "[^"_]+(_\d+_\d+)"',
                       lambda m: f'(symbol "{name}{m.group(1)}"', s, count=1)
                for s in subs]

    out = [f'\t\t(symbol "{lib}:{name}"']
    for blk2 in misc + props + subs:
        out.append("\n".join("\t\t\t" + ln if ln.strip() else ln
                             for ln in blk2.splitlines()))
    out.append("\t\t)")
    return "\n".join(out) + "\n", None


def process(path, apply, refresh=False):
    s = io.open(path, encoding="utf-8").read()
    i = s.find("(lib_symbols")
    if i < 0:
        return f"{os.path.basename(path)}: 沒有 lib_symbols 區塊", 0
    cache = sexp_block(s, i)        # ⚠ 原文的長度，切檔案時一定要用這個
    have = set(re.findall(r'\n\t\t\(symbol "([^"]+)"', cache))
    used = sorted(set(re.findall(r'\(lib_id "([^"]+)"\)', s)))
    missing = [u for u in used if u not in have]
    keep = cache[len("(lib_symbols"):].lstrip("\n")
    if refresh:
        # 整個重建快取。用在 lib_symbol_mismatch ——
        # 那代表快取裡存的是舊版符號，跟庫裡的已經不一樣了。
        # 改過符號（例如 RY1303 的 pin 16 從 NC 改成 VCC）就會發生。
        missing = used
        keep = "\t)\n"              # 只留收尾，既有條目全部丟掉重建
    if not missing:
        return f"{os.path.basename(path):22s} ✓ {len(used)} 種符號都在快取裡", 0

    blocks, errs = [], []
    for lid in missing:
        lib, _, name = lid.partition(":")
        b, err = build(lib, name)
        if err:
            errs.append(f"      ✗ {lid}：{err}")
        else:
            blocks.append(b)
    if errs:
        return (f"{os.path.basename(path):22s} ✗ 補不齊\n" + "\n".join(errs), -1)

    if apply:
        new_cache = "(lib_symbols\n" + "".join(blocks) + keep
        io.open(path, "w", encoding="utf-8", newline="\n").write(
            s[:i] + new_cache + s[i + len(cache):])
    return (f"{os.path.basename(path):22s} "
            f"{'補上' if apply else '待補'} {len(missing)} 種：{', '.join(missing)}",
            len(missing))


def main():
    apply = "--apply" in sys.argv
    refresh = "--refresh" in sys.argv
    if apply:
        guard_kicad_closed(ROOT)
    total = bad = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "*.kicad_sch"))):
        msg, n = process(p, apply, refresh)
        print("  " + msg)
        if n < 0:
            bad += 1
        else:
            total += n
    print(f"\n{'已補上' if apply else '待補'} {total} 筆符號定義")
    if bad:
        sys.exit(f"✗ 有 {bad} 張圖紙補不齊 —— 先處理上面的錯誤")
    if not apply and total:
        print("（檢查模式，沒有改檔。要補請加 --apply）")


if __name__ == "__main__":
    main()
