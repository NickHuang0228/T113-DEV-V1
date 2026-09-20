# ADV7511KSTZ —— 從原廠文件抽出的規格

**來源**：`ADV7511 Hardware User's Guide, Rev. D, July 2011`（58 頁）
`https://www.analog.com/media/en/technical-documentation/user-guides/ADV7511_Hardware_Users_Guide.pdf`

✅ **原始 PDF 已在本目錄**：`ADV7511_Hardware_Users_Guide.pdf`
（846,967 bytes，58 頁，Rev D，2011-07；由使用者手動下載 ——
ADI 封鎖所有自動下載，經過見本檔附錄）

**本檔是那份 PDF 的中文摘要與索引**，方便設計文件引用；
**數字逐字照抄，頁碼為該 PDF 的頁碼。有疑義一律以 PDF 原檔為準。**

⚠ 機構圖（Figure 7, p.21）仍應**開原檔目視**再進 layout ——
文字層給得出數字，給不出圖形。

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

## 3. 完整腳位表（Table 3, p.19-20）

### 3.1 視訊輸入

```
D[35:0]     pin 57-74, 78, 80-96    Video Data Input（RGB 或 YCbCr）
CLK         pin 79                   Video Clock Input
DE          pin 97
HSYNC       pin 98
VSYNC       pin 2
```

**全部「Supports typical CMOS logic levels from 1.8V up to 3.3V」。**

#### ✅ D[35:0] 的索引↔腳號（開 Figure 6, p.18 目視抄出）

**右側（pin 57→74，D 索引遞減）**

```
57 D35   58 D34   59 D33   60 D32   61 D31   62 D30
63 D29   64 D28   65 D27   66 D26   67 D25   68 D24
69 D23   70 D22   71 D21   72 D20   73 D19   74 D18
```

**頂側（pin 78→96，D 索引遞減；79 是 CLK，不是 D）**

```
78 D17   79 CLK   80 D16   81 D15   82 D14   83 D13
84 D12   85 D11   86 D10   87 D9    88 D8    89 D7
90 D6    91 D5    92 D4    93 D3    94 D2    95 D1    96 D0
```

**四邊完整對照**

```
左 (1-25)    1 DVDD · 2 VSYNC · 3-8 DSD0~DSD5 · 9 DSD_CLK · 10 SPDIF · 11 MCLK
             12-15 I2S0~I2S3 · 16 SCLK · 17 LRCLK · 18 GND · 19 DVDD · 20 GND
             21 PLVDD · 22 GND · 23 GND · 24 PVDD · 25 PVDD

下 (26-50)   26 BGVDD · 27 GND · 28 R_EXT · 29 AVDD · 30 HPD · 31 GND
             32 TXC- · 33 TXC+ · 34 AVDD · 35 TX0- · 36 TX0+ · 37 GND · 38 PD
             39 TX1- · 40 TX1+ · 41 AVDD · 42 TX2- · 43 TX2+ · 44 GND · 45 INT
             46 SPDIF_OUT · 47 MVDD · 48 CEC · 49 DVDD · 50 CEC_CLK

右 (51-75)   51 HEAC- · 52 HEAC+ · 53 DDCSCL · 54 DDCSDA · 55 SCL · 56 SDA
             57-74 D35~D18 · 75 GND

頂 (76-100)  76 DVDD · 77 DVDD · 78 D17 · 79 CLK · 80-96 D16~D0
             97 DE · 98 HSYNC · 99 GND · 100 GND
```

⚠ **VSYNC (pin 2) 在左側，DE/HSYNC (97/98) 在頂側** —— 四條同步訊號不在同一邊。
⚠ **未用的 D[35:24] 正好是 pin 57~68，右側連續 12 支** —— 接 GND 很好走線。

### 3.2 電源與地

```
AVDD    1.8V   pin 29, 34, 41             TMDS 輸出類比
DVDD    1.8V   pin 1, 19, 49, 76, 77      數位與 IO —— "should be filtered and as quiet as possible"
PVDD    1.8V   pin 24, 25                 PLL 數位 —— "quiet, noise-free"
PLVDD   1.8V   pin 21                     PLL 類比（VCO）—— "the most sensitive portion of the ADV7511"
BGVDD   1.8V   pin 26                     Band Gap
MVDD    3.3V   pin 47
GND            pin 18,20,22,23,27,31,37,44,75,99,100    ← 11 支，確認無 EPAD
```

> GND 說明：`"recommended that the ADV7511 be assembled on a single, solid ground plane
> with careful attention given to ground current paths"`

### 3.3 TMDS 輸出

```
TxC-/TxC+   pin 32, 33    時脈
Tx2-/Tx2+   pin 42, 43    紅（pixel clock × 10）
Tx1-/Tx1+   pin 39, 40    綠
Tx0-/Tx0+   pin 35, 36    藍
```

### 3.4 控制與 HDMI

```
SDA        pin 56    1.8~3.3V CMOS
SCL        pin 55    1.8~3.3V CMOS
DDCSDA     pin 54    5V tolerant，接 HDMI 座
DDCSCL     pin 53    5V tolerant，接 HDMI 座
HPD        pin 30    1.8V ~ 5.0V CMOS
INT        pin 45    輸出，建議 2kΩ(±10%) 上拉到 MCU 的 IO 電源
CEC        pin 48    1.8~5V CMOS
CEC_CLK    pin 50    3~100 MHz 外部時脈輸入
HEAC+/-    pin 52/51 ARC 差分對
R_EXT      pin 28    ★ 887Ω ±1% 接地
PD/AD      pin 38    Power-Down 控制 **兼** I2C 位址選擇
```

⚠ **PD/AD (pin 38) 一腳兩用**：
`"The I2C address and the PD polarity are set by the PD/AD pin state when the supplies are applied"`
—— **上電當下的腳位狀態同時決定 I2C 位址與 PD 極性**，原理圖上要明確定義。

### 3.5 音訊

```
SPDIF       pin 10          輸入
SPDIF_OUT   pin 46          ARC 接收輸出，3.3V CMOS
MCLK        pin 11          128/256/384/512 × fS
I2S[3:0]    pin 15-12
SCLK        pin 16
LRCLK       pin 17
DSD[5:0]    pin 8-3
DSD_CLK     pin 9           2.8224 MHz
```

---

## 3A. PCB Layout 建議（§7, p.52-54）—— 全部是硬性設計輸入

### §7.1 電源濾波

#### ✅ Figure 23 (p.50) 的三組怎麼分 —— 不是一個名字一組

```
1.8V LDO ──┬──[10 µH]──┬── DVDD    pin 1, 19, 49, 76, 77
           │           └─[10 µF]─GND
           │
           ├──[10 µH]──┬── AVDD    pin 29, 34, 41
           │           │   PVDD    pin 24, 25          ← AVDD 與 PVDD 同一組
           │           └─[10 µF]─GND
           │
           └──[10 µH]──┬── PLVDD   pin 21
                       │   BGVDD   pin 26              ← PLVDD 與 BGVDD 同一組
                       └─[10 µF]─GND

所有 bypass 電容 0.1 µF（每支電源腳一顆，相鄰腳可共用）
GND 腳用 via 接到 GND plane
```

#### ⚠ §6.8 (p.50)：ADI 建議 ADV7511 用**自己專屬**的 1.8V LDO

```
"It is recommended that the ADV7511 has its own designated 1.8V linear regulator
 and that the AVDD, DVDD and PLVDD PCB power domains be segregated using inductors."
```

**不是與 SoC 共用 1.8V。** 這會再改一次電源樹 —— 見 001-power.md。

#### ✅ §6.8.1 (p.50)：ADV7511 沒有上電時序要求

```
"There is no required sequence for turning on or turning off the power domains;
 all should be fully powered up or down within 1 second of the others."
```

**與 T113-S3 的 T1>2ms / T2>64ms 不同，ADV7511 這邊完全不用排序。**

#### ✅ Figure 24 (p.52)：AVDD / PLVDD 的雜訊上限曲線

目視讀值（Max rms noise vs frequency, DC~10 MHz）：

```
1 ~ 20 kHz        約 28.5 mV      平坦
~25-30 kHz        約 29 mV        小峰
30 k → 200 kHz    急降
100 kHz           約 9.5 mV
200 k ~ 300 kHz   約 1.3 mV       ★ 最嚴的一段
300 k ~ 1 MHz     約 1.5 ~ 1.7 mV
1 M ~ 5 MHz       約 1.8 ~ 3 mV   緩升
10 MHz            約 5.5 mV
```

⚠⚠ **最嚴的 1.3 mV rms 落在 200 kHz ~ 1 MHz —— 正好是切換式電源的基頻與低階諧波。**
RY1303 這類 DC-DC 的切換頻率就在這個區間。
**這就是為什麼一定要 LDO + LC，而不是直接從 DC-DC 拉 1.8V 過來。**

#### ✅ Table 22 (p.51)：可關掉的功能方塊

```
CSC                 Max 25 mW   Typ 16 mW
HDCP                Max 30 mW   Typ 25 mW
CEC                 < 1 mW
SPDIF 高功耗模式     40 mW（192 kHz）   ← 內部產生 MCLK
SPDIF 低功耗模式     10 mW（32 kHz）    ← 外部供 MCLK
```

§6.8.2 說 326 mW 這個數字是 **1080p、CSC off** 的條件。
本板不用 HDCP / CEC / SPDIF 的話還能再省約 70 mW。

### §7.2 視訊時脈與資料 ★

```
"Any noise coupled onto the CLK input trace will add jitter to the system."
→ CLK (pin 79) 走線要做阻抗控制
→ 走線下方用完整 GND 或電源參考面，確保全長阻抗一致
→ CLK 走線盡量短，旁邊不要走數位或高頻訊號
→ "Make sure to match the length of the input data signals to optimize data capture
   especially for Double Data Rate (DDR) input formats"
```

⚠ **ADI 明確要求資料線等長**，即使我們的 skew 預算計算顯示餘裕很大。
本板用 SDR（單邊緣），比 DDR 寬鬆，但**原廠建議照做**。

⚠ **CLK 要阻抗控制** —— 這是單端訊號的阻抗控制需求，
原本 005-stackup.md 只規劃了差分對的阻抗控制。

### §7.3 音訊

```
音訊資料與時脈線等長；靠近源端串 50Ω ±5% 電阻
```

### §7.4 SDA / SCL

```
各上拉 2 kΩ ±5% 到 1.8V 或 3.3V
```

### §7.5 DDCSDA / DDCSCL

```
各上拉 1.5 kΩ ~ 2 kΩ ±5% 到 HDMI 的 +5V  —— "is required"（不是建議）
```

### §7.6 R_EXT ★

```
887 Ω ±1%，接在 R_EXT (pin 28) 與地之間，走線越短越好
"strongly recommended to avoid running any high-speed AC or noisy signals next to
 the R_EXT line" —— 特別點名 LRCLK（含 via）不可靠近 pin 28
TMDS 的低準位切換雜訊影響不大
```

### §7.7 CEC

```
CEC_CLK 需要外部時脈：預設 12 MHz，3~100 MHz ±2% 皆可
CEC 線：27 kΩ 上拉到 3.3V，串一顆漏電流 < 1.8 µA 的二極體（Figure 26/27）
```

---

## 3B. Figure 27 (p.55) 參考原理圖 —— 照著接就對了

```
                        ┌─ 2kΩ → 1.8V 或 3.3V（本板 3.3V）
                 INT ───┴──────────────▶ 處理器中斷

   CEC osc. ───▶ CEC_CLK
                 CEC ────┬─[27kΩ]─ 3.3V
                         └─[二極體, 漏電 <1.8µA]──┐
   2kΩ→1.8/3.3V          DDCSDA ─[2kΩ]─ 5V       ├──▶ ESD ──▶ HDMI 座
         └── SDA         DDCSCL ─[2kΩ]─ 5V       │
             SCL                                  │
                         TMDS（HDMI data）────────┤
   Video data ──▶                                 │
   Audio data ──▶        HPD ◀─────────────────────┘

                         HEAC- ─[1µF]─┬─[50Ω]─ 1.8V
                         HEAC+ ─[1µF]─┘          （ARC，本板不做）

   R_EXT ─[887Ω 1%]─ GND
```

⚠ 圖上的 INT 與 SDA/SCL 上拉畫的是 **1.8V**，因為 ADI 的範例主機是 1.8V。
Table 3 寫「上拉到 **MCU 的 IO 電源**」，§7.4 寫「1.8V **或** 3.3V」——
**本板 T113 的 PD/PG bank 是 3.3V，所以上拉到 3.3V。**

⚠ **CEC 不是免費的** —— 要額外一顆振盪器。
SPEC 原本就寫「CEC 可選，V1 不做」，現在有了明確理由。

---

## 4. 尚未取得

```
[x] 原始 PDF —— 已在本目錄
[x] 完整腳位表（Table 3, p.19-20）
[x] §7 PCB Layout 建議（p.52-54）
[x] Figure 6 (p.18) 腳位圖 —— D[35:0] 索引↔腳號已抄（見 §3.1）
[x] Figure 23 (p.50) —— 三組分法已抄（DVDD ／ AVDD+PVDD ／ PLVDD+BGVDD）
[x] Figure 24 (p.52) —— 雜訊上限曲線已目視讀值
[x] Figure 27 (p.55) —— 參考原理圖已抄（見 §3B）
[ ] Figure 7 (p.21) 機構圖的「圖形」—— 數字已抄，1:1 列印比對時再開原檔
[ ] 未用的 D 腳處置：datasheet 未明說。它們是輸入腳（VIL -0.3~0.7V），
     接 GND 在電氣上安全，但沒有原廠背書 —— 標為判斷而非引用
[ ] ADV7511 Programming Guide（2.8 MB，暫未取；driver 移植階段才需要）
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

**最後是由使用者在瀏覽器裡手動按下下載鈕才拿到檔案的。**
下載後核對：846,967 bytes，與瀏覽器 `fetch()` 回報的位元組數完全一致，
58 頁、Rev D，內容正確。

**教訓：Chrome 不接受 CDP 合成的點擊作為觸發下載的「真人手勢」。**
自動化能把視窗叫到前景、能把分頁切過去、能點中按鈕（圖示會反白），
但最後那一下必須是真人。遇到擋下載的站，正確做法是
**先用 pdf.js 把需要的數字抽出來解除阻塞，同時請使用者按一下把檔案收進版本庫。**
