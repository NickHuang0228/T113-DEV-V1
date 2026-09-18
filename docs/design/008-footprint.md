# 008 · Footprint 驗算

版本：v0.1 · 2026-09-19

**這是這塊板唯一「錯了整批報廢、且無法補救」的項目**（ROADMAP §3.2 風險 ①）。
所有數字一律以 datasheet 機構圖為準，不信任任何二手來源。

---

## 1. T113-S3 機構圖實測

`(DS §7.2 Figure 7-2 Package Dimension, 紙本 p.78 = PDF p.88)`

### 1.1 尺寸表（單位 mm）

| Symbol | Min | Nom | Max | 意義 |
|---|---|---|---|---|
| A | — | — | 1.60 | 總高 |
| A1 | 0.025 | — | 0.127 | 站立高度（seating plane 到本體底部） |
| A2 | 1.35 | **1.40** | 1.45 | 本體厚度 |
| **b** | 0.13 | **0.18** | 0.23 | **腳寬** |
| b1 | 0.13 | 0.16 | 0.19 | 腳寬（base metal，不含鍍層） |
| c | 0.09 | 0.14 | 0.20 | 腳厚 |
| c1 | 0.09 | 0.12 | 0.16 | 腳厚（base metal） |
| **D** | 15.85 | **16.00** | 16.15 | **含腳總長** |
| **D1** | 13.90 | **14.00** | 14.10 | **本體長** |
| **E** | 15.85 | **16.00** | 16.15 | **含腳總寬** |
| **E1** | 13.90 | **14.00** | 14.10 | **本體寬** |
| **e** | — | **0.40 BSC** | — | **pitch** |
| **L** | 0.45 | **0.60** | 0.75 | **腳可焊長度** |
| L1 | — | 1.00 REF | — | 腳總長 |
| R1 / R2 | 0.08 | — | — | 腳彎折半徑 |
| S | 0.20 | — | — | |
| θ | 0° | 3.5° | 7° | 腳外張角 |
| θ1 | 0° | — | — | |
| θ2 / θ3 | 11° | 12° | 13° | |
| **ccc** | — | **0.08** | — | **共面度（焊接良率關鍵）** |

`NOTE 8: REFERENCE DOCUMENT : JEDEC MS-026`

### 1.2 ⚠ 元件佔位是 16×16mm，不是 14×14mm

```
DS §2.12 / §7.1 寫「eLQFP128, 14 mm x 14 mm」  →  那是 D1 / E1（本體）
實際 placement 要留的是 D / E = 16.00mm        →  含伸出來的腳
KiCad footprint 的焊盤外緣還要再外擴 → 實際約 16.8mm
```

**placement 草圖上 T113-S3 要畫 17×17mm 的佔位**，不是 14×14。

---

## 2. Exposed Pad：原廠 CAUTION 與一個陷阱

### 2.1 原文

```
CAUTION
Make sure to use the second set of exposed pad size (D3/E3: 5.72 mm REF or
0.225 mm REF) to design the PCB footprint because the T113-S3 package is
designed according to this size.
```

### 2.2 機構圖上其實有 **六組**選項，不是兩組

| L/F | D3/E3 (mm) | D3/E3 (inch) |
|---|---|---|
| ① | 3.61 REF | 0.142 REF |
| **②** | **5.72 REF** | **0.225 REF** | ← **CAUTION 指定這組** |
| ③ | 8.00 REF | 0.315 REF |
| ④ | 7.75 / 6.60 REF | 0.305 / 0.260 REF |
| ⑤ | 5.60 / 5.20 REF | 0.221 / 0.205 REF |
| ⑥ | 5.72 / 5.46 REF | 0.225 / 0.215 REF | ← ⚠ **陷阱** |

### 2.3 ⚠ 陷阱：②和⑥都是 5.72 開頭

```
②  5.72 REF          正方形   5.72 × 5.72
⑥  5.72 / 5.46 REF   長方形   5.72 × 5.46
```

**只看到「5.72」就選，有 50% 機率拿到長方形的 ⑥，短邊差 0.26mm。**

怎麼分辨：CAUTION 的文字是 **「5.72 mm REF **or** 0.225 mm REF」** ——
`or` 連接的是「同一個值的 mm 與 inch 兩種寫法」，而不是兩個不同的邊長。
只有 ② 是單一值（5.72 mm = 0.225 inch）。⑥ 會寫成 `5.72 / 5.46`。

### 2.4 結論

```
EPAD = 5.72 × 5.72 mm 正方形
```

**EPAD 是這顆晶片唯一的數位地**（128 隻腳裡只有 1 支 AGND），必焊。
見 [001-power.md](001-power.md) §7。

---

## 3. Footprint 怎麼做

### 3.1 好消息：KiCad 內建件對得上

```
/share/kicad/footprints/Package_QFP.pretty/LQFP-128_14x14mm_P0.4mm.kicad_mod

descr: "LQFP, 128 Pin (JEDEC MS-026 variation BEE, 1.40mm body thickness ...)"
```

**datasheet NOTE 8 寫 `JEDEC MS-026`，KiCad 這顆標的是 `MS-026 variation BEE`，完全對上。**
body 14mm、pitch 0.4mm、128 腳、本體厚 1.40mm 四項全部相符。

焊盤參數（實測自 `.kicad_mod`）：

```
pad 數      128（無 EPAD）
pad 尺寸    1.475 × 0.25 mm  roundrect
pad 間距    0.40 mm          （pad1 y=-6.2、pad2 y=-5.8 → 0.4 ✓）
pad 外緣跨距  16.80 mm        （vs D max 16.15 → toe fillet 0.325mm）
pad 內緣跨距  13.85 mm        （vs D1 min 13.90 → heel 剛好在本體邊內）
```

對照 datasheet：`b max = 0.23` vs pad 寬 `0.25` → 側邊留 0.01mm；`L nom = 0.60` vs pad 長 1.475 → 前後加 fillet。**符合 IPC-7351。**

### 3.2 要自己做的只有 EPAD

```
KiCad 標準件沒有 EPAD  →  自己加 pad "129"
尺寸    5.72 × 5.72 mm（見 §2.4）
位置    置中
網路    GND
```

⚠ **EPAD 與最內側訊號焊盤的間隙**：

```
訊號 pad 內緣  6.925 mm（半徑）
EPAD 半寬      2.86 mm
間隙           4.065 mm    → 非常寬鬆，無短路風險
```

### 3.3 Thermal via

```
陣列     5 × 5 = 25 顆，間距 1.2mm，對 EPAD 置中
鑽孔     0.3mm（JLCPCB 4 層標準）
連到     內層 GND 平面
```

⚠ **必須 plugged 或至少背面 tented**，否則回流時錫從 via 漏到背面 → 晶片被墊高 → 128 隻腳同時虛焊（目視完全正常，只有 X-ray 看得到）。

```
[ ] 查 JLCPCB：via 背面 tented 是否免費？resin plugged 要加多少錢？
    （tented 通常免費且對 ≤0.4mm via 夠用；resin plugged 要加價）
```

**本專案採用「鋼網 + 錫膏 + 回流」路線（見 [006-assembly.md](006-assembly.md) §6），
所以 via 必須塞住 —— 不保留「背面補焊」那條路。**

### 3.4 錫膏開口

```
EPAD 的鋼網開口做成網格狀（不是一整塊大開口）
錫膏覆蓋率 50~70%
```

一整塊開口會放太多錫 → 晶片浮起。這是業界對 exposed pad 的標準做法。

⚠ 本專案 EPAD 交給 JLCPCB 貼裝，**鋼網開口由他們處理**，但 KiCad 裡的 `F.Paste` 層
仍要自己畫成網格，否則他們照著做出一整塊開口。

---

## 4. 驗收

```
[ ] KiCad footprint 的 128 焊盤用 LQFP-128_14x14mm_P0.4mm（MS-026 BEE）
[ ] EPAD (pad 129) = 5.72 × 5.72 mm，置中，網路 GND
    ⚠ 不是 5.72 × 5.46（那是機構圖第 ⑥ 組，不是 CAUTION 指定的第 ② 組）
[ ] EPAD 的 F.Paste 層畫成網格，覆蓋率 50~70%
[ ] Thermal via 5×5、0.3mm、間距 1.2mm，設為 plugged/tented
[ ] placement 佔位按 16.8mm（不是 14mm）
[ ] 1:1 列印，把實體零件壓上去比對
[ ] IT66121 (QFN64 9×9) 的 land pattern —— 公開版 datasheet 無機構圖，須另尋來源
[ ] RTL8201F (QFN32) 的 land pattern —— datasheet 67 頁版本應有，待查
```

---

## 5. 還沒解的

```
[ ] IT66121 機構圖：公開版只有 8 頁，無 package dimension
     替代來源：KiCad 內建 QFN-64 9×9 標準件比對 / LCSC 產品頁 land pattern
[ ] RTL8201F 機構圖：datasheet v1.4（67 頁）應有，未查
[ ] 接頭類：RJ45 HR911105A / Type-C / microSD / FPC 座（畫 PCB 前）
```
