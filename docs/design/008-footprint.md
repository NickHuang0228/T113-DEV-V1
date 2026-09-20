# 008 · Footprint 驗算

版本：v0.4 · 2026-09-20（ADV7511 機構圖數字已取得；**它沒有 EPAD**，先前寫「含 EPAD」是誤用 W 版資料）

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

## 4. ~~IT66121FN（QFN-64）~~ —— ⚠ 已作廢，零件停產

> **IT66121FN 原廠停產**（LCSC `C2684803` 庫存 0），v0.4 改用 **ADV7511**。
> 以下數字保留作為紀錄，**不要用於 layout**。新晶片的 footprint 待辦見 §4A。

<details>
<summary>（已作廢）IT66121FN QFN-64 機構圖數字</summary>


`(IT66121FN datasheet v1.02, Figure 17, p.40/40)`

| Symbol | Min | Nom | Max | 意義 |
|---|---|---|---|---|
| A | 0.80 | 0.90 | 1.00 | 總高 |
| A1 | 0.00 | 0.02 | 0.05 | 站立高度 |
| A3 | — | 0.20 REF | — | 底部金屬厚 |
| **b** | 0.18 | **0.25** | 0.30 | 焊盤寬 |
| **D / E** | 8.90 | **9.00** | 9.10 | 本體 |
| **D2 / E2** | 3.58 | **3.78** | 3.98 | **EPAD** |
| **e** | — | **0.50 BSC** | — | pitch |
| L | 0.30 | 0.40 | 0.50 | 焊盤長 |
| y | — | — | 0.08 | 共面度 |

**QFN-64，9 × 9 mm，pitch 0.5 mm，EPAD 3.78 × 3.78 mm（pin 65 = GND PAD）。**
KiCad 對應件為 `QFN-64-1EP_9x9mm_P0.5mm_EP3.8x3.8mm_ThermalVias`。

</details>

---

## 4A. ADV7511KSTZ（LQFP-100）

`LCSC C179459 · Analog Devices · ST-100 · JEDEC MS-026-BED`

**來源**：`ADV7511 Hardware User's Guide Rev.D §5.1 p.21 Figure 7`
完整抽取見 [../reference/peripherals/ADV7511KSTZ_extracted.md](../reference/peripherals/ADV7511KSTZ_extracted.md)

### ⚠ 先更正一個錯誤：它**沒有** Exposed Pad

v0.3 寫「LQFP-100 14×14 **含 EPAD**」是錯的 —— 那是拿 **ADV7511W** 的資料套上來的。

| | ADV7511**KSTZ**（本專案） | ADV7511**W**BSWZ |
|---|---|---|
| 封裝 | **100-lead LQFP** | 64-lead **LQFP_EP** |
| 代號 | **ST-100** | SW-64-2 |
| JEDEC | **MS-026-BED** | MS-026-BCD-HD |
| 本體 | 14 × 14 | 10 × 10 |
| EPAD | **無** | 有，5.00 SQ |
| 視訊輸入 | D[35:0] | D[23:0] |
| LCSC | C179459 有貨 | 無此料 |

分辨依據：Figure 7 的標題是 `100-lead Low-Profile Quad Flat Pack [LQFP]`（不是 `[LQFP_EP]`），
機構圖**沒有 D2/E2 欄位**，而 W 版的機構圖明確列著 `5.10 / 5.00 SQ / 4.90` 的 EXPOSED PAD。
p.18 的腳位圖也顯示 **GND 是一般接腳，有多支**。

> **這是本專案第五次踩「拿欄位字面值／鄰近型號當實際幾何」。**
> 前四次是 J1 custom pad、ESP32 模組自轉 270°、T113 的六組 EPAD、RTL8201F 的三種封裝章節。
> 這次的變形是 **料號尾碼差一個字母就是不同封裝** —— 和 RTL8201F/FL/FN 完全同型。

### 機構圖數字

```
本體 D1/E1      13.80  /  14.00 SQ  /  14.20
含腳 D/E        15.80  /  16.00 SQ  /  16.20
pitch e         0.50 BSC
腳寬 b          0.17   /  0.22      /  0.27
腳長 L          0.45   /  0.60      /  0.75
總高 A          1.60 MAX
本體厚 A2       1.35   /  1.40      /  1.45
站立高 A1       0.05   /  0.15
共面度          0.08
```

### 與 T113-S3 是同一個 JEDEC 家族

```
T113-S3    eLQFP128  MS-026-BEE  本體 14.00  含腳 16.00  pitch 0.40  + EPAD 5.72
ADV7511    LQFP-100  MS-026-BED  本體 14.00  含腳 16.00  pitch 0.50  無 EPAD
```

**兩顆的本體與含腳尺寸完全相同，只差 pitch 與 EPAD。**
placement 佔位一樣按 **16.8mm** 抓（含焊盤外緣）。

### KiCad 對應件

```
候選：LQFP-100_14x14mm_P0.5mm
  body 14mm · pitch 0.50 · 100 腳 · 本體厚 1.40 —— 四項與機構圖相符
  ⚠ KiCad 該件的 descr 是否標 MS-026-BED 要開檔確認
  ⚠ 沒有 EPAD → 不需要像 T113 那樣自加，直接用標準件
```

**→ 這顆不用自建 footprint。** 全板需要自建的仍然只有 T113-S3 一顆。

### ⚠ 仍未完成的一步

```
[ ] 取得原始 PDF 目視核對 Figure 7 的「圖形」
     目前數字來自 pdf.js 文字層抽取,ADI 封鎖了 PDF 的自動存檔
     專案規則「定位靠文字,定案靠看圖」—— 這裡只完成了前半
[ ] 開 KiCad 的 LQFP-100_14x14mm_P0.5mm 核對焊盤尺寸與 b/L 的相容性
[ ] 1:1 列印比對實體零件
```

### 換料對 placement 的連帶影響

```
IT66121   QFN-64   本體 9 × 9    含腳約 9mm
ADV7511   LQFP-100 本體 14 × 14  含腳 16.00（機構圖實值）
```

**橋接晶片的佔位從 9mm 級跳到 16mm 級，和 T113-S3 一樣大。**
100×100mm 上要塞兩顆 16.8mm 見方的佔位 —— placement 草圖要重畫，
見 [005-stackup.md](005-stackup.md)。

**直接用，不必自建。**

---

## 5. RTL8201F（QFN-32）

`(RTL8201F/FL/FN datasheet v1.4 §10.1, p.55)`

| Symbol | Min | Nom | Max | 意義 |
|---|---|---|---|---|
| A | 0.75 | 0.85 | 1.00 | 總高 |
| A1 | 0.00 | 0.02 | 0.05 | 站立高度 |
| A3 | — | 0.20 REF | — | 底部金屬厚 |
| **b** | 0.18 | **0.25** | 0.30 | 焊盤寬 |
| c | — | — | 0.6 | |
| **D / E** | — | **5.00 BSC** | — | 本體 |
| **D2 / E2** | 3.10 | **3.35** | 3.60 | **EPAD** |
| **e** | — | **0.50 BSC** | — | pitch |
| L | 0.30 | 0.40 | 0.50 | 焊盤長 |

`Note 2: REFERENCE DOCUMENT: JEDEC MO-220`

**QFN-32，5 × 5 mm，pitch 0.5 mm，EPAD 3.35 × 3.35 mm。**

⚠ **這份 datasheet 涵蓋三種封裝，別拿錯章節：**

```
§10.1  p.55   RTL8201F   QFN-32    ← 本專案用這個
§10.2  p.56   RTL8201FL  LQFP-48
§10.3  p.57   RTL8201FN  QFN-48
```

### KiCad 對應件

```
QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias
  焊盤  0.875 × 0.25 mm     ✓
  pitch 0.50 mm             ✓
  EPAD  3.3 × 3.3           vs  datasheet 3.35 nom
```

**選 EP3.3 而非 EP3.45**：EPAD 的 land 取略小於封裝標稱值比較安全
（大於標稱會往 max 3.60 靠，增加與週邊焊盤橋接的風險）。

---

## 6. 驗收

```
[ ] KiCad footprint 的 128 焊盤用 LQFP-128_14x14mm_P0.4mm（MS-026 BEE）
[ ] EPAD (pad 129) = 5.72 × 5.72 mm，置中，網路 GND
    ⚠ 不是 5.72 × 5.46（那是機構圖第 ⑥ 組，不是 CAUTION 指定的第 ② 組）
[ ] EPAD 的 F.Paste 層畫成網格，覆蓋率 50~70%
[ ] Thermal via 5×5、0.3mm、間距 1.2mm，設為 plugged/tented
[ ] placement 佔位按 16.8mm（不是 14mm）
[ ] 1:1 列印，把實體零件壓上去比對
[ ] ADV7511 用 `LQFP-100_14x14mm_P0.5mm`（MS-026-BED，**無 EPAD，不需自建**）（見 §4A）
[ ] RTL8201F 用 `QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias`（見 §5）
    ⚠ 確認用的是 datasheet §10.1 QFN-32，不是 §10.2 LQFP-48 或 §10.3 QFN-48
```

---

## 7. 三顆主 IC 總表

| 元件 | 封裝 | 本體 | pitch | EPAD | KiCad 標準件 |
|---|---|---|---|---|---|
| T113-S3 | eLQFP128 | 14×14（含腳 16×16） | 0.40 | **5.72×5.72** | `LQFP-128_14x14mm_P0.4mm` + **自加 EPAD** |
| **ADV7511KSTZ** | LQFP-100 | 14×14（含腳 16×16） | 0.50 | **無** | `LQFP-100_14x14mm_P0.5mm`（MS-026-BED） |
| RTL8201F | QFN-32 | 5×5 | 0.50 | 3.35×3.35 | `QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias` |

### ⚠ EPAD 的狀況變了

```
T113-S3    有 EPAD（5.72×5.72，唯一的數位地）  → 必須 PCBA
ADV7511    無 EPAD                             → 可手焊、可目視檢查
RTL8201F   有 EPAD（3.35×3.35）                → 建議 PCBA
```

**換掉 IT66121 之後，三顆不再是「全部有 EPAD」。**
ADV7511 是 0.5mm pitch 的有腳封裝，難度等同上一塊板焊過的 LQFP ——
**它從「必須交給 PCBA」變成「可以自己焊」**，見 [006-assembly.md](006-assembly.md)。

v0.2 的結論「只有 T113-S3 需要自建 footprint」**仍然成立**，
而且比原本更好：ADV7511 連 EPAD 都不用自己加。

---

## 8. 還沒解的

```
[ ] 接頭類機構圖：RJ45 HR911105A / Type-C / microSD / FPC 座（畫 PCB 前，須先定料號）
[ ] SPI NOR (XT25F128B) 封裝
[ ] 電源 IC（RY1303 或分離式）封裝
```
