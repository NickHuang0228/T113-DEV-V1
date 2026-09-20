# ADV7511KSTZ —— 從原廠文件抽出的規格

**來源**：`ADV7511 Hardware User's Guide, Rev. D, July 2011`（58 頁）
`https://www.analog.com/media/en/technical-documentation/user-guides/ADV7511_Hardware_Users_Guide.pdf`

**抽取方式**：ADI 官網封鎖 curl / PowerShell / WebFetch（HTTP 000 或連線重置），
PDF 檔本身無法自動存檔。改用瀏覽器載入頁面後注入 pdf.js 抽取文字層。
**頁碼為該 PDF 的頁碼，數字逐字照抄。**

⚠ **這份是文字抽取，不是原始機構圖。** 依專案規則（ROADMAP 風險 ①），
進 layout 前仍要取得原始 PDF 目視核對機構圖，特別是焊盤幾何。

---

## ⚠ 最重要的更正：ADV7511KSTZ **沒有** Exposed Pad

先前文件寫「LQFP-100 14×14 **含 EPAD**」是**錯的** —— 那是拿 **ADV7511W** 的資料套上來。
兩者是不同的封裝：

| | ADV7511**KSTZ**（本專案採用） | ADV7511**W**BSWZ |
|---|---|---|
| 封裝 | **100-lead LQFP** | 64-lead **LQFP_EP** |
| 封裝代號 | **ST-100** | SW-64-2 |
| JEDEC | **MS-026-BED** | MS-026-BCD-HD |
| 本體 | **14 × 14 mm** | 10 × 10 mm |
| Exposed Pad | **無** | 有，5.00 SQ |
| 視訊輸入 | **D[35:0]** | D[23:0] |
| LCSC | **C179459，有貨** | 無此料 |

**後果：ADV7511KSTZ 的地是靠一般接腳，不是 EPAD → 可以手焊、可以目視檢查。**

---

## 1. 機構圖數字

`(HW User's Guide §5.1, p.21, Figure 7)`

```
Figure 7  100-lead Low-Profile Quad Flat Pack [LQFP]
COMPLIANT TO JEDEC STANDARDS MS-026-BED
14 mm × 14 mm × 1.4 mm (ST-100)

本體 D1/E1      13.80  /  14.00 SQ  /  14.20
含腳 D/E        15.80  /  16.00 SQ  /  16.20
pitch e         0.50 BSC
腳寬 b          0.17   /  0.22      /  0.27
腳長 L          0.45   /  0.60      /  0.75
總高 A          1.60 MAX
本體厚 A2       1.35   /  1.40      /  1.45
站立高 A1       0.05   /  0.15
腳厚            0.09   /  0.20
共面度          0.08
腳角            0° / 3.5° / 7°
```

⚠ **沒有 D2/E2（exposed pad）欄位** —— 對照 ADV7511W 的機構圖明確列有
`5.10 / 5.00 SQ / 4.90` 的 EXPOSED PAD，本封裝沒有。

### 與 T113-S3 的對照

```
T113-S3    eLQFP128  MS-026-BEE  本體 14.00  含腳 16.00  pitch 0.40  + EPAD 5.72
ADV7511    LQFP-100  MS-026-BED  本體 14.00  含腳 16.00  pitch 0.50  無 EPAD
```

**同一個 JEDEC 家族（MS-026），同樣 14mm 本體 / 16mm 含腳，只差 pitch 與 EPAD。**
KiCad 候選件：`LQFP-100_14x14mm_P0.5mm`（待 1:1 列印比對）。

---

## 2. 電氣規格（Table 1，明確標示 ADV7511KSTZ/ADV7511KSTZ-P）

`(HW User's Guide §4, p.12-13)`

### 2.1 數位輸入（Video / Audio / CEC_CLK）

```
VIH   Input Voltage High     Min 1.35    Max 3.5    V
VIL   Input Voltage Low      Min -0.3    Max 0.7    V
      Input Capacitance      Typ 1.0     Max 1.5    pF
```

**→ 3.3V CMOS 可直接驅動（VIH 上限 3.5V）。VCC-PD = 3.3V 確定沒問題。**

**→ 輸入電容 1.5 pF max** —— 這是 002-display.md §1.1 待確認的數字。
IT66121 約 5 pF，**ADV7511 只有 1/3，掛在 MIPI 分支上的負載小得多。**

### 2.2 I2C 與 CEC

```
I2C (DDCSDA/DDCSCL/SDA/SCL)   VIH 1.19 ~ 5.5 V   VIL -0.3 ~ 0.8 V
CEC                            VIH 2.0 V
```

### 2.3 電源

```
1.8V  DVdd / AVdd / PVdd / PLVdd / BGVdd     1.71 / 1.80 / 1.90 V     ← 五個域
3.3V  MVdd                                   3.15 / 3.30 / 3.45 V

雜訊上限   DVdd   64 mV RMS
           PVdd   64 mV RMS
           BGVdd  64 mV RMS
           AVdd / PLVdd   見 §7.1（類比，更嚴）
```

⚠ **是五個 1.8V 域不是四個**（ADV7511W 才是四個：DVDD/AVDD/PVDD/BGVDD）。
ADV7511KSTZ 多一個 **PLVdd（HDMI PLL – Analog）**。

⚠ 3.3V 那條在 KSTZ 叫 **MVdd**，不是 W 版的 `DVDD_3V`。

### 2.4 功耗

```
Transmitter Total Power   326 mW   （1.8V = 325 mW，3.3V = 1 mW）
                                   條件：1080p，36 bit，typical random pattern
Power-Down Current L1      20 mA
Power-Down Current L2     300 µA
```

**1.8V 的 325 mW → 約 180 mA。** 本專案用 RGB666（18-bit）而非 36-bit，
實際會低於此值，但電源照最壞情況設計。

### 2.5 AC 規格 —— 視訊輸入

```
Input Video Clock Frequency          Max 165    MHz
Input Video Data Setup  tVSU         Min 1.0    ns
Input Video Data Hold   tVHLD        Min 0.7    ns

TMDS Output Clock Frequency          20 ~ 225   MHz
TMDS Output Clock Duty Cycle         48 ~ 52    %
TMDS Differential Swing              800 / 1000 / 1200 mV
Output Low-to-High Transition        75 / 95    ps
Output High-to-Low Transition        75 / 95    ps
VSYNC/HSYNC Delay from DE Falling    1 UI
VSYNC/HSYNC Delay to DE Rising       1 UI
```

### 2.6 音訊 AC

```
I2S[3:0] / SPDIF / DSD[5:0]  Setup tASU   2 ns
                             Hold  tAHLD  2 ns
LRCLK                        Setup / Hold 2 ns
SCLK Duty Cycle   N/2 偶數 40~60% ／ N/2 奇數 49~51%
```

---

## 3. 腳位（Figure 6, p.18）

100-lead LQFP，文字層可辨識的腳位群：

```
視訊資料   D0 ~ D35
同步       HSYNC · VSYNC · DE
音訊       I2S0~I2S3 · SCLK · LRCLK · MCLK · SPDIF · DSD0/DSD1 · DSD_CLK
HDMI       DDCSDA · DDCSCL · HEAC+ · HEAC-
控制       SCL · SDA
電源       PLVdd · PVdd · DVdd · MVdd · AVdd · BGVdd
地         GND ×多支（一般接腳，非 EPAD）
```

```
[ ] 完整腳位表要回原始 PDF p.18-20 核對，本節只是文字層抽取的片段
```

---

## 4. 尚未取得

```
[ ] 原始 PDF 檔本身（ADI 封鎖自動下載，見本檔頁首）
[ ] Figure 7 的機構圖「圖形」—— 目前只有文字層的數字
[ ] 完整腳位表（p.19-20）
[ ] §7.1 的 AVdd / PLVdd 雜訊上限與去耦建議
[ ] ADV7511 Programming Guide（2.8 MB，暫未取）
```

---

## 附錄 · 為什麼這份檔案存在

ADI 對自動化下載的封鎖相當徹底，六條路全部失敗：

```
curl（多種 UA / Referer）          HTTP 000（連線被重置）
PowerShell Invoke-WebRequest       請求送出即失敗 / 逾時
WebFetch                           ECONNRESET / 逾時
鏡像站（DigiKey / Mouser / LCSC / Farnell / RS / alldatasheet）
                                   403 / 404 / 回傳 HTML / 拿到別顆料
Chrome PDF viewer 下載鈕 + Ctrl+S  檔案不落地
頁內 blob + <a download>           被靜默阻擋
```

**唯一可行的是：用瀏覽器載入頁面後注入 pdf.js 抽文字層。**
`fetch()` 在 analog.com 自己的頁面裡是同源的，回傳 200 與正確位元組數，
但那些位元組沒有辦法存到磁碟。

**所以這份 .md 是原始 PDF 的替代品，不是它的等價物。**
機構圖是向量圖 —— 文字層給得出數字，給不出圖形。
專案規則「定位靠文字，定案靠看圖」在這裡只完成了前半。
