#!/usr/bin/env python3
"""T113-DEV-V1 原理圖檢查規則。

每條規則都要標出處（設計文件的章節），這樣看到警告時知道去哪查。
規則只在相關元件存在時才生效 —— 還沒畫到的頁不會噴一堆錯。
"""
import csv
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PINMAP_CSV = os.path.join(os.path.dirname(HERE), "data", "T113-S3_pinmap.csv")

# ── T113-S3 電源腳應該接哪條軌 ──────────────────────────────
#    出處：011-power-tree.md §1 電源樹
T113_POWER_NETS = {
    "VCC-IO": "+3V3",
    "VCC-PD": "+3V3",
    "VCC-PE": "+3V3",
    "VCC-PG": "+3V3",
    "VCC-TVOUT": "+3V3",
    "LDO-IN": "+3V3",
    "VCC-PLL": "+1V8_SOC",
    "VCC-RTC": "+1V8_SOC",
    "VCC-LVDS": "+1V8_SOC",
    "VCC-TVIN": "+1V8_SOC",
    "AVCC": "+1V8_SOC",
    "HPVCC": "+1V8_SOC",
    "VDD18-DRAM": "+1V8_SOC",
    "VCC-DRAM0": "+1V5",
    "VCC-DRAM1": "+1V5",
    "VDD-CORE0": "+0V9",
    "VDD-CORE1": "+0V9",
    "VDD-SYS0": "+0V9",
    "VDD-SYS1": "+0V9",
    "VDD-SYS2": "+0V9",
    "AGND": "GND",
    "EPAD": "GND",
}

# 這幾支是輸出/不接軌，接到電源軌反而是錯的
#    出處：011-power-tree.md §3.1
T113_MUST_NOT_BE_RAIL = {
    "LDOA-OUT": "內建 LDOA 輸出 —— 本板不使用，只掛 2.2µF。接到 +1V8_SOC 等於兩顆穩壓器並聯",
    "LDOB-OUT": "內建 LDOB 輸出 —— 本板不使用，只掛 2.2µF",
    "VRA1": "內部參考電壓輸出，不可接電源軌",
    "VRA2": "內部參考電壓輸出，不可接電源軌",
}

# ── ADV7511 電源腳 ──────────────────────────────────────────
#    出處：011-power-tree.md §5 / ADV7511 HW Guide Figure 23
ADV7511_POWER_NETS = {
    "1": "+1V8_DVDD", "19": "+1V8_DVDD", "49": "+1V8_DVDD",
    "76": "+1V8_DVDD", "77": "+1V8_DVDD",
    "29": "+1V8_AVDD", "34": "+1V8_AVDD", "41": "+1V8_AVDD",
    "24": "+1V8_AVDD", "25": "+1V8_AVDD",
    "21": "+1V8_PLVDD", "26": "+1V8_PLVDD",
    "47": "+3V3",
}
ADV7511_GND_PINS = ["18", "20", "22", "23", "27", "31", "37", "44", "75", "99", "100"]

# ── RGB666 接線：T113 LCD0-D → ADV7511 pin ──────────────────
#    出處：002-display.md §3.2 腳位級接線表
RGB_WIRING = {
    # T113 pin : (訊號, ADV7511 pin)
    "74": ("LCD0-D23 / R5", "69"), "73": ("LCD0-D22 / R4", "70"),
    "72": ("LCD0-D21 / R3", "71"), "71": ("LCD0-D20 / R2", "72"),
    "69": ("LCD0-D19 / R1", "73"), "70": ("LCD0-D18 / R0", "74"),
    "68": ("LCD0-D15 / G5", "81"), "67": ("LCD0-D14 / G4", "82"),
    "64": ("LCD0-D13 / G3", "83"), "63": ("LCD0-D12 / G2", "84"),
    "62": ("LCD0-D11 / G1", "85"), "61": ("LCD0-D10 / G0", "86"),
    "60": ("LCD0-D7 / B5", "89"), "59": ("LCD0-D6 / B4", "90"),
    "58": ("LCD0-D5 / B3", "91"), "57": ("LCD0-D4 / B2", "92"),
    "56": ("LCD0-D3 / B1", "93"), "55": ("LCD0-D2 / B0", "94"),
}

# ADV7511 未用輸入應接 GND
#    出處：002-display.md §3.2
ADV7511_TIE_GND = ["78", "80", "87", "88", "95", "96"] + [str(p) for p in range(57, 69)]

# ── 必備的離散元件（值要對）─────────────────────────────────
REQUIRED_PARTS = [
    # (描述, 值的正規表示式, 出處)
    (r"DZQ 校準電阻", r"^240\s*[RΩ]?$", "011-power-tree.md §6.1 / MangoPi R42"),
    (r"ADV7511 R_EXT", r"^887\s*[RΩ]?$", "011-power-tree.md §6.2 / ADV7511 §7.6"),
]


def load_t113_pins():
    rows = list(csv.DictReader(io.open(PINMAP_CSV, encoding="utf-8")))
    by_name = {r["name"]: r["pin"] for r in rows}
    by_pin = {r["pin"]: r["name"] for r in rows}
    return by_name, by_pin


def find_refs(comps, pattern):
    import re
    return [r for r, c in comps.items() if re.search(pattern, c.get("value", ""), re.I)]


def run(comps, nets, pinmap, norm):
    """回傳 [(級別, 規則名, 訊息), ...]"""
    out = []
    by_name, by_pin = load_t113_pins()

    t113 = find_refs(comps, r"^T113-S3$")
    adv = find_refs(comps, r"ADV7511")

    # ── T113 電源腳 ────────────────────────────────────────
    if t113:
        ref = t113[0]
        if len(t113) > 1:
            out.append(("WARN", "T113-重複", f"找到 {len(t113)} 個 T113-S3 符號：{t113}"))
        connected = 0
        for sig, want in T113_POWER_NETS.items():
            pin = by_name.get(sig)
            if pin is None:
                continue
            got = pinmap.get((ref, pin))
            if got is None:
                out.append(("ERR", "電源腳未接", f"{ref} pin {pin} ({sig}) 浮接 —— 應接 {want}"))
                continue
            connected += 1
            if norm(got) != want:
                out.append(("ERR", "電源軌錯誤",
                            f"{ref} pin {pin} ({sig}) 接到 {norm(got)}，應為 {want}"
                            f"　〔011-power-tree.md §1〕"))
        if connected:
            out.append(("INFO", "電源腳", f"{ref} 已接 {connected}/{len(T113_POWER_NETS)} 支電源腳"))

        for sig, why in T113_MUST_NOT_BE_RAIL.items():
            pin = by_name.get(sig)
            got = pinmap.get((ref, pin)) if pin else None
            if got and norm(got) in ("+1V8_SOC", "+1V8_HDMI", "+3V3", "+1V5", "+0V9"):
                out.append(("ERR", "不該接電源軌",
                            f"{ref} pin {pin} ({sig}) 接到 {norm(got)} —— {why}"))

        # 非連號陷阱：確認使用者沒有把 PD12/PD13 當成連號
        #   符號本身是對的，這裡檢查「接到 ADV7511 的對應腳」
        if adv:
            a = adv[0]
            for tp, (sigdesc, ap) in RGB_WIRING.items():
                tn = pinmap.get((ref, tp))
                an = pinmap.get((a, ap))
                if tn is None or an is None:
                    continue
                if norm(tn) != norm(an):
                    out.append(("ERR", "RGB 接線",
                                f"T113 pin {tp} ({sigdesc}) 在 {norm(tn)}，"
                                f"但 ADV7511 pin {ap} 在 {norm(an)} —— 兩者應同一條 net"
                                f"　〔002-display.md §3.2〕"))

    # ── ADV7511 電源腳 ────────────────────────────────────
    if adv:
        a = adv[0]
        for pin, want in ADV7511_POWER_NETS.items():
            got = pinmap.get((a, pin))
            if got is None:
                out.append(("ERR", "ADV 電源未接", f"{a} pin {pin} 浮接 —— 應接 {want}"))
            elif norm(got) != want:
                out.append(("ERR", "ADV 電源軌錯誤",
                            f"{a} pin {pin} 接到 {norm(got)}，應為 {want}"
                            f"　〔011-power-tree.md §5〕"))
        for pin in ADV7511_GND_PINS:
            got = pinmap.get((a, pin))
            if got is not None and norm(got) != "GND":
                out.append(("ERR", "ADV GND", f"{a} pin {pin} 接到 {norm(got)}，應為 GND"))
        for pin in ADV7511_TIE_GND:
            got = pinmap.get((a, pin))
            if got is not None and norm(got) != "GND":
                out.append(("WARN", "ADV 未用輸入",
                            f"{a} pin {pin} 接到 {norm(got)} —— RGB666 未用的輸入建議接 GND"
                            f"　〔002-display.md §3.2〕"))

    # ── 必備離散元件 ──────────────────────────────────────
    import re
    for desc, valpat, src in REQUIRED_PARTS:
        hit = [r for r, c in comps.items() if re.match(valpat, c.get("value", "").strip(), re.I)]
        if not hit:
            out.append(("WARN", "缺元件", f"找不到{desc}（值應符合 {valpat}）　〔{src}〕"))

    # ── 單腳 net（多半是漏接）───────────────────────────────
    for n, pins in nets.items():
        if len(pins) == 1 and not n.startswith("unconnected-"):
            ref, pin = pins[0]
            out.append(("WARN", "單腳 net", f"net {norm(n)} 只接了 {ref} pin {pin} —— 可能漏接"))

    return out
