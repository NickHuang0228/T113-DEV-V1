# 002 · 顯示介面：MIPI DSI 與 RGB→HDMI

版本：v0.3 · 2026-09-20（查完 UM §5 TCON 章節與 IT66121 電氣規格；v0.2 的 R/B 標反、「沒有 RGB888」的說法也不對）

**專案優先序：MIPI DSI > RGB/HDMI。** 長期目標是 DSI layout 經驗，HDMI 是附帶。

---

## 0. TCON 有兩組，但給面板的只有一組

階段 0 的待確認項「TCON 數量」查完了。

`(UM §5 Video Output Interfaces, p.397 起；CCU §3.3.6.92 / §3.3.6.94, p.140-142)`

```
§5.1  TCON LCD   暫存器 0x0B60 TCONLCD_CLK_REG   →  RGB 並列 / LVDS / MIPI DSI
§5.2  TCON TV    暫存器 0x0B80 TCONTV_CLK_REG    →  TV Encoder（CVBS OUT）
```

**RGB、LVDS、MIPI DSI 三者掛在同一個 TCON_LCD 下**（MIPI DSI 是 UM §5.1.3.12，
編在 TCON LCD 章節裡面），所以：

```
v0.1 的「共用同一組 TCON，dts 二選一」  →  ✓ 成立
§1 的「連接腳也共用」                   →  ✓ 也成立，而且更嚴格
```

CVBS 有自己的 TCON_TV，理論上可與面板同時輸出（DE 有 main + aux 兩組顯示通道
`(DS §2.5.1 p.5)`）。**本板不做 CVBS**，這一條只是記錄，免得日後誤以為「只有一個 TCON」。

---

## 1. 必須先講清楚的事實：MIPI 與 RGB 共用同一組實體接腳

v0.1 寫「兩者共用同一組 TCON，dts 二選一」—— **不只是共用 TCON，是共用接腳。**

`(DS Table 4-3 Pin Multiplexing, PD bank)`

```
PD0   LCD0-D2    LVDS0-V0P   DSI-D0P     ┐
PD1   LCD0-D3    LVDS0-V0N   DSI-D0N     │
PD2   LCD0-D4    LVDS0-V1P   DSI-D1P     │
PD3   LCD0-D5    LVDS0-V1N   DSI-D1N     │
PD4   LCD0-D6    LVDS0-V2P   DSI-CKP     ├─ MIPI 用這 10 支（5 對）
PD5   LCD0-D7    LVDS0-V2N   DSI-CKN     │  RGB 也用這 10 支
PD6   LCD0-D10   LVDS0-CKP   DSI-D2P     │
PD7   LCD0-D11   LVDS0-CKN   DSI-D2N     │
PD8   LCD0-D12   LVDS0-V3P   DSI-D3P     │
PD9   LCD0-D13   LVDS0-V3N   DSI-D3N     ┘
PD10  LCD0-D14   LVDS1-V0P   SPI1-CS     ┐
 ...                                     ├─ 只有 RGB 用，不衝突
PD21  LCD0-VSYNC TWI2-SDA    UART1-TX    ┘
```

```
MIPI DSI   PD0 ~ PD9    10 支（4 lane + 1 clock = 5 對）
RGB 並列   PD0 ~ PD21   22 支
重疊區     PD0 ~ PD9    完全重疊
```

### 1.1 為什麼這是問題，而不只是「dts 二選一」

如果兩組接頭都直接拉線到 PD0~PD9：

```
MIPI FPC 座       ┐
                  ├─ 兩者的走線都永遠掛在同一支腳上
IT66121 RGB 輸入  ┘
```

**軟體切換不能把電氣負載切掉。** 跑 MIPI 模式時，IT66121 的輸入電容（每支約 5 pF）
加上到 IT66121 的走線，會變成掛在 1 Gbps 差分線上的 stub。

而 §2.1 的規則已經寫得很清楚：**MIPI 不能有 stub。**

反過來看則寬鬆得多：跑 RGB 模式時，MIPI FPC 座的走線是掛在 148 MHz 單端線上的 stub，
短一點就沒事。**這個衝突是不對稱的 —— MIPI 受害，RGB 不受害。**

### 1.2 解法：PD0~PD9 用 0Ω 隔離，MIPI 直通

```
SoC PD0~PD9  ═══════════════════════════════▶  MIPI FPC 座   （直通，阻抗控制）
                   ║
                   ╚═[0Ω × 10]══════════════▶  IT66121 低位輸入

SoC PD10~PD21 ─────────────────────────────▶  IT66121        （不衝突，直接接）
```

```
要跑 MIPI    0Ω 不焊  →  IT66121 輸入斷開，MIPI 線上乾淨
要跑 HDMI    0Ω 焊上  →  RGB 全部接通
```

**IT66121 本體照樣上件**（交給 PCBA，QFN64 不手焊），只是輸入被 0Ω 斷開。
切換要動烙鐵，但 0402 0Ω 拆焊很容易。

⚠ 這不違反 §2.1「MIPI 不能加串聯電阻」的規則 ——
**0Ω 不在 MIPI 路徑上，它在分支上。** MIPI 是直通，不經過任何電阻。

### 1.3 ⚠ layout 關鍵規則：0Ω 必須貼著主幹

不焊 0Ω 時，MIPI 線上剩下的 stub = 從主幹到 0Ω 第一個焊盤的距離。

```
MIPI HS 上升時間  ~200 ps
FR4 傳播延遲      ~6.7 ps/mm
臨界長度          ~200ps / 6.7ps/mm / 6 ≈ 5 mm

規則：0Ω 焊盤邊緣距離主幹走線 ≤ 0.5 mm
```

放遠了就白做 —— stub 還在，只是換了個位置。

### 1.4 IT66121 在 MIPI 模式要關掉

0Ω 拆掉後 IT66121 的輸入浮接。**必須用 GPIO 控制它的 `SYSRSTN`（或電源），
在 MIPI 模式時讓它保持 reset**，避免它亂驅動或耗電。

```
[ ] 原理圖上 IT66121 的 SYSRSTN 接一支 GPIO，不要直接上拉
```

---

## 1.5 架構圖（修正後）

```
T113-S3 Display Engine
        │
      TCON
        │
        ├──▶ PD0~PD9   ──┬──▶ MIPI DSI 4-lane ──▶ FPC 座 ──▶ 面板   ★ 優先
        │                 └─[0Ω]──┐
        └──▶ PD10~PD21 ───────────┴──▶ IT66121 ──▶ HDMI Type-A
```

---

## 2. MIPI DSI

### 2.1 電氣特性 —— 為什麼 MIPI 比想像中難

D-PHY 的同一對線上有**兩種完全不同的訊號模式**：

| 模式 | 擺幅 | 型態 | 用途 |
|---|---|---|---|
| **HS**（High Speed） | **200 mV** 差分 | 差分，終端 100Ω | 傳像素資料 |
| **LP**（Low Power） | **1.2 V** 單端 | 單端，無終端 | 傳命令、進出低功耗 |

```
同一對銅線，一下子要當 200mV 的差分傳輸線，
一下子要當 1.2V 的單端訊號。
```

這代表 layout 上：

- **不能加任何串聯電阻或 AC 耦合電容** —— 那會破壞 LP 模式的直流準位
- **不能有 stub** —— HS 的上升時間很快，任何分支都會反射
- 走線要短、要直、要對稱

### 2.2 走線規則

```
阻抗          100Ω 差分（±10%）
對內等長      ±0.1mm
對間等長      各資料對相對 clock 對，±0.5mm
間距          對與對之間 ≥ 3× 線寬（避免串擾）
參考層        全程走在完整 GND 平面上方，不跨分割
換層          盡量不換；必須換時旁邊加 GND via
```

**「不跨分割」是最容易踩的坑** —— 差分對經過電源平面的縫隙時，回流路徑被打斷，共模雜訊暴增。

### 2.3 接頭

```
FPC 0.5mm pitch，30~40 pin（依目標面板）
腳位定義必須對照面板 datasheet，不能假設
```

⚠ 面板 FPC 的 pin 定義各家不同，**下單前務必用實體面板比對**。

### 2.4 面板電源

MIPI 面板不是接上 3.3V 就會亮的。典型需求：

```
VSP   +5.5V      正電源
VSN   −5.5V      負電源
VGH   +15V       閘極高壓
VGL   −10V       閘極低壓
IOVCC 1.8/3.3V   介面電壓
```

需要專用的 LCD bias IC（如 TPS65132，雙通道正負輸出）。

⚠ **V1 先不做面板電源**，FPC 上只拉訊號 + IOVCC，正負高壓由外部提供或留空。理由：

1. 第一版目標是「HDMI 出畫面」，MIPI 是加分項
2. 高壓 charge pump 的開關雜訊會耦合到 200mV 的 HS 訊號，是額外風險
3. 留 V2 專門做面板電源，才有餘裕做隔離

---

## 3. RGB 並列 → IT66121 → HDMI

### 3.1 為什麼選 IT66121

```
drivers/gpu/drm/bridge/ite-it66121.c   ← mainline 就有
QFN64 9×9mm + 底部 GND pad             ⚠ 非 LQFP，手焊高風險，交給 PCBA
Allwinner 生態常用                      ← 有人踩過坑
```

LT8618SX 在 Linux 上通常要靠廠商 blob 或自己寫 driver。**第一塊板不在 driver 上冒險。**

### 3.2 RGB 並列走線

### ⚠ v0.2 這一節有兩個錯誤，先更正

**錯誤 1：R 與 B 標反了。** v0.2 寫 `PD0~PD5 = R`、`PD12~PD17 = B`，實際相反。

**錯誤 2：「T113-S3 沒有 RGB888」不成立。** 晶片有，只是要多借 6 支 PB 腳。

#### 正確對應（兩張表交叉而來）

`(UM §5.1.3.1 Table 5-2 The Correspondence between LCD and RGB, p.399)`
`(DS Table 4-3 Pin Multiplexing, p.30-31)`

Table 5-2 明講 **parallel RGB 的資料是 high-aligned**（高位對齊），所以：

```
LCD0-D23..D18  =  R5..R0      LCD0-D15..D10  =  G5..G0      LCD0-D7..D2  =  B5..B0
```

再套 Table 4-3 的 PD bank Function2：

```
PD0  = D2  = B0        PD6  = D10 = G0        PD12 = D18 = R0
PD1  = D3  = B1        PD7  = D11 = G1        PD13 = D19 = R1
PD2  = D4  = B2        PD8  = D12 = G2        PD14 = D20 = R2
PD3  = D5  = B3        PD9  = D13 = G3        PD15 = D21 = R3
PD4  = D6  = B4        PD10 = D14 = G4        PD16 = D22 = R4
PD5  = D7  = B5        PD11 = D15 = G5        PD17 = D23 = R5

PD18 = LCD0-CLK    PD19 = LCD0-DE    PD20 = LCD0-HSYNC    PD21 = LCD0-VSYNC
```

```
PD0  ~ PD5    B[5:0]     ← v0.2 寫成 R，錯
PD6  ~ PD11   G[5:0]
PD12 ~ PD17   R[5:0]     ← v0.2 寫成 B，錯
```

⚠ 注意 bit 順序也反了：**PD0 是 B0（LSB），PD5 才是 B5（MSB）**，
v0.2 的 `R[7:2]` 寫法暗示 PD0 是 MSB，也是錯的。

#### 但接線時不會踩到這個坑 —— 因為兩顆晶片用同一套 D 索引

IT66121 的視訊輸入腳就叫 `D[23:0]` `(IT66121 DS p.6 Digital Video Input Pins)`，
而且同樣是 high-aligned。**所以按 D 編號 1:1 接就對了，不必經過顏色名稱：**

```
T113 LCD0-D23 ──▶ IT66121 D23        （R5）
T113 LCD0-D18 ──▶ IT66121 D18        （R0）
T113 LCD0-D15 ──▶ IT66121 D15        （G5）
   ...
T113 LCD0-D2  ──▶ IT66121 D2         （B0）

IT66121 D17 / D16 / D9 / D8 / D1 / D0  ──▶ GND
```

**用顏色名稱接線才會出錯，用 D 索引接線不會。** 原理圖上一律標 D 編號。

⚠ 6 支 LSB 接 GND 的代價：全白只到 `0xFC/0xFF` = 98.8% 滿刻度，實務上看不出來。
（另一種做法是把 MSB 複製到 LSB 取得真正的 0xFF，但那要在 6 條 RGB 線上多掛分支，
為了 1.2% 的亮度增加 stub —— 不划算，接 GND。）

#### 為什麼選 RGB666 —— 是取捨，不是晶片限制

缺的 6 個 bit（D0/D1/D8/D9/D16/D17）**在 PD bank 上確實不存在**，
但它們在 **PB2~PB7 的 Function2** 上 `(DS Table 4-3, p.30)`：

```
PB2 = LCD0-D0 (B0)     PB4 = LCD0-D8  (G0)     PB6 = LCD0-D16 (R0)
PB3 = LCD0-D1 (B1)     PB5 = LCD0-D9  (G1)     PB7 = LCD0-D17 (R1)
```

UM Table 5-2 有完整的 RGB888 欄，Table 5-4 也寫 `D[23..0] 24-bit RGB output`，
DS Table 5-18 的註 (5) 同樣是 `LD[23..0]: 24Bit RGB/YUV output from input FIFO for panel`。
**所以 T113-S3 支援 RGB888，代價是 PD0~PD21 之外再吃掉 PB2~PB7。**

本專案仍選 RGB666，理由是 bank 風險而非晶片能力：

```
PB 在 VCC-IO 上 —— 那條軌同時掛著 microSD、SPI NOR、UART0 console
把 6 條 148MHz 的 RGB 線拉進命脈 bank，換 1.2% 的色深 → 不划算
（PB2~PB7 已配給 I2S2 音訊，見 007-pinmap.md §6.3）
```

**後果：HDMI 輸出是 RGB666（26 萬色）。** 漸層會有可見 banding，
T113 的 DE 有 dither 可緩解 `(DS §2.6.1 p.6 "RGB666 and RGB565 with dither function")`。

```
v0.1 寫    24 資料 + 4 控制 = 28 條單端      ✗
實際       18 資料 + 4 控制 = 22 條單端      ✓
```

**MIPI 優先的理由之一仍然成立 —— MIPI DSI 在本板配置下能跑 RGB888，RGB 並列只到 RGB666。**

```
訊號數       18 資料 + HS + VS + DE + CK = 22 條單端
解析度上限   RGB 1920×1080@60  /  MIPI DSI 4-lane 1920×1200@60   (DS §2.6 p.6)
```

### ✅ pixel clock 上限：SoC 200 MHz，IT66121 165 MHz —— 瓶頸在橋接晶片

`(DS §5.11.1 Table 5-18 LCD HV_IF Interface Timing Constants, p.61)`

```
DCLK cycle time    tDCLK    Min 5 ns    →   DCLK max = 200 MHz
```

```
T113-S3 TCON_LCD    200 MHz      (DS Table 5-18)
IT66121FN           165 MHz      (IT66121 DS p.17 Fpixel max)
1080p@60 所需        148.5 MHz    CEA-861
                    ───────────
瓶頸                 IT66121，不是 SoC
```

功能面的 `up to 1920 x 1080@60fps` `(DS §2.6.1 p.6 / UM §5.1.1 p.397)` 是頻寬結論，
**接腳時序本身容許到 200 MHz。** 兩個數字不衝突，但引用時要分清楚。

#### ⚠ 陷阱：不要把 148.5 MHz 當成 LCD 的數字

全文搜 `MHz`，148.5 只在三處命中，**全部都是視訊輸入**：

```
DS §2.7.1 Parallel CSI, p.7                    "Maximum pixel clock of 148.5 MHz"
DS §5.11.2 Table 5-19 CSI Interface, p.62      Pclk frequency max 148.5 MHz
UM §6.1 CSIC, p.499                            同一句
```

LCD 的數字在 **Table 5-18**，CSI 的在 **Table 5-19**，兩張表連在一起。
**grep 先撞到的是 CSI 那張** —— 因為 LCD 那張只寫 `5 ns`，沒有 `MHz` 字樣。

> 這是專案規則「抽出來的文字用來定位，不用來定案」的第四次命中，而且是新的一種：
> **搜尋關鍵字本身有偏差 —— 用 `MHz` 去找時脈上限，會漏掉用 `ns` 表示的那一張表。**

時脈鏈的可調範圍 `(UM §3.3.6.92 p.140)`：

```
TCONLCD_CLK = Clock Source / M / N
Source ∈ { PLL_VIDEO0(1X/4X), PLL_VIDEO1(1X/4X), PLL_PERI(2X), PLL_AUDIO1(DIV2) }
PLL_VIDEO0(4X) 預設 1188 MHz   (UM §3.3.6.4 p.76)
```

⚠ **Table 5-18 沒有給 LCD 輸出的 setup/hold 或 Tco**，只有 cycle time 與時序常數關係。
所以 T113 側的輸出 skew 仍是未知數 —— 下面的 budget 計算要保留餘量。

### IT66121 側的上限倒是明確

`(IT66121 DS p.2 / Video AC Timing Specification p.17)`

```
Fpixel   單邊緣取樣   25 ~ 165 MHz      ← 148.5 落在範圍內 ✓
TS       setup        1.5 ns min
TH       hold         0.7 ns min
TPJ      PCLK jitter  2.0 ns max
TPDUTY   工作週期      40% ~ 60%
```

⚠ **下限 25 MHz 也是限制**：想跑很低的解析度（例如 480i 原生 13.5 MHz）
必須靠 IT66121 的 pixel-repeat 把時脈乘上去，不能直接餵。

### skew budget（用 IT66121 的真實數字重算）

```
148.5 MHz → Tpixel = 6.734 ns
扣 TS 1.5 ns + TH 0.7 ns                 → 剩 4.53 ns
給 T113 輸出 skew + 時脈 jitter 留 3.5 ns（保守，因為 DS 沒給 Tco）
→ 剩 ~1 ns 給 PCB
FR4 傳播延遲 ~6.7 ps/mm
→ 1000 ps / 6.7 ps/mm ≈ 149 mm
```

**在 100×100mm 的板子上，兩條走線最多也差不到 149mm —— 等長在物理上不可能成為瓶頸。**
實作時對 CK 等長做到 ±10mm 即可，那是整齊，不是需求。

> ROADMAP 風險 ⑤ 把「RGB 並列等長」列為主要風險，**這個定性要下修**。
> 等長不是風險，SSO 與 jitter 才是。

**真正的殺手是 SSO noise（Simultaneous Switching Output）**：22 條線同時翻轉造成的地彈與 EMI。
地彈會直接吃掉 IT66121 那 2.0 ns 的 jitter 預算 —— 這才是 148.5 MHz 下會出事的路徑。

緩解手段：

```
串聯阻尼電阻   每條 22~33Ω，靠近驅動端（IT66121 側或 SoC 側）
slew rate      SoC 端若可設定，降到剛好夠用
GND 回流       走線下方必須是完整 GND 平面
分組           資料線分成幾組，中間穿插 GND 走線
```

⚠ 22 條線加上串聯電阻 = **22 顆 0402 電阻**，再加 §1.2 的 **10 顆 0Ω 隔離**，
共 32 顆電阻要預留擺放空間。

⚠ PD0~PD9 那 10 條的阻尼電阻要放在 **0Ω 之後、靠 IT66121 那側**，
不能放在主幹上 —— 主幹是 MIPI 的路徑，不能串任何東西。

### 3.2.1 ⚠ IT66121 要 1.2V —— 全板多一條電源軌

`(IT66121 DS p.7 Power/Ground Pins；p.14 Functional Operation Conditions)`

```
IVDD12    1.2V   pin 8, 35, 56    核心邏輯
AVCC12    1.2V   pin 23           HDMI 類比前端      ⚠ 註記要求「should be regulated」
PVCC12    1.2V   pin 18           HDMI PLL           ⚠ 同上
DVDD12    1.2V   pin 28           HDMI 數位前端
                                  ───────────────
VCC33     3.3V   pin 9            內部 ROM
PVCC33    3.3V   pin 19           HDMI PLL           ⚠ 同上
OVDD33    3.3V   pin 13           5V-tolerant IO（DDC / HPD / CEC / I2C）
OVDD      1.8 / 2.5 / 3.3V  pin 1, 34   ← RGB 輸入腳的電源，可選
```

**v0.2 之前的規格寫「4 組電源域」，漏掉了這一條。** 實際是 5 組外部電源軌。

```
Functional Operation Conditions   1.14 / 1.2 / 1.26 V
VCCNOISE                          Max 100 mVpp     ← 雜訊要求很緊
全片功耗                           < 70 mW @1080p60  (IT66121 DS p.3)
```

功耗只有 70 mW，**1.2V 的電流很小（估 < 50 mA）**，用一顆 3.3V→1.2V 的 LDO 即可：

```
壓降 2.1V × 50 mA ≈ 105 mW     SOT-23 封裝散得掉
LDO 而非 DC-DC 的理由：VCCNOISE 只給 100 mVpp，DC-DC 的切換漣波不值得冒險
AVCC12 / PVCC12 另外用磁珠 + 0.1µF + 10µF 從 1.2V 幹線隔開（datasheet 要求 regulated）
```

詳見 [001-power.md](001-power.md) §1 與 §2.5。

#### OVDD 選 3.3V

OVDD 決定 RGB 輸入腳的電平，1.8 / 2.5 / 3.3V 皆可 `(IT66121 DS p.14)`，
**所以 IT66121 對 VCC-PD 的電壓沒有任何限制** —— 007-pinmap.md §8 的待決事項
「VCC-PD 要同時滿足 MIPI 與 IT66121」，IT66121 這一半不存在。

選 3.3V 的理由：`VIH = 2.0V min`，配 T113 的 3.3V 輸出有 1.3V 餘裕；
選 1.8V 則 `VIH = 1.2V`，餘裕只剩 0.6V，而 22 條線的 SSO 地彈就吃這個餘裕。

---

### 3.3 TMDS 差分

```
對數      4 對（D0± / D1± / D2± / CK±）
阻抗      100Ω 差分
速率      1080p@60 約 1.485 Gbps/pair
上升時間  ~250 ps → 臨界長度約 4.7mm（任何超過此長度的走線都要當傳輸線處理）
對內等長  ±0.15mm
對間等長  相對 CK 對，±0.5mm
```

**HDMI 座旁邊要放 ESD 保護**（如 SRV05-4 或專用 HDMI ESD 陣列），
且 ESD 元件的電容要低（<1pF），否則會破壞高頻特性。

### 3.4 DDC 與 HPD

```
DDC (I2C)   SCL/SDA，上拉到 5V（HDMI 規範）
HPD         Hot Plug Detect，需分壓到 SoC 可接受的準位
CEC         可選，V1 不做
```

---

## 4. 兩條路徑的取捨

| | MIPI DSI | RGB → HDMI |
|---|---|---|
| 差分對 | 5 | 4（TMDS） |
| 單端線 | 0 | **22** |
| 額外零件 | FPC 座 | IT66121 + 22 顆阻尼電阻 + 10 顆 0Ω + ESD + **1.2V LDO** |
| 板面積 | 小 | **大** |
| 驗證難度 | 高（要有面板、要調參數） | **低（插螢幕就能看）** |

**bring-up 順序建議：先驗 HDMI，再驗 MIPI。**
HDMI 只要 driver 起來就有畫面，是最快能確認「顯示鏈路通了」的路徑。
MIPI 還要對面板 timing、init sequence、lane 設定，變因多得多。

---

## 5. 驗收

```
[ ] MIPI 5 對阻抗 100Ω，對內等長 ±0.1mm，全程不跨分割
[ ] MIPI 線上無串聯電阻、無 AC 耦合電容
[ ] TMDS 4 對阻抗 100Ω，對內等長 ±0.15mm
[ ] RGB 22 條對 CK 等長，串聯阻尼電阻已放且靠近驅動端
[ ] HDMI ESD 保護已放，電容 <1pF
[ ] DDC 上拉到 5V
[x] IT66121 的 RGB 輸入時脈上限 ≥ 目標解析度所需
      → Fpixel 25~165 MHz，1080p60 的 148.5 MHz 在範圍內  (IT66121 DS p.17)
[ ] IT66121 的 1.2V 軌已放（IVDD12 / AVCC12 / PVCC12 / DVDD12），且 AVCC12 / PVCC12 有隔離
[ ] IT66121 的 OVDD 接 3.3V，OVDD33 / VCC33 / PVCC33 接 3.3V
[ ] IT66121 的 D[17:16] / D[9:8] / D[1:0] 接 GND（RGB666 未用的 6 個 LSB）
[ ] 原理圖上 RGB 接線一律標 LCD0-D 編號，不用顏色名稱（避免 R/B 對調）
[ ] ENTEST (pin 31) 經電阻接地、REXT (pin 20) 經 5.6kΩ 1% 接 AGND
```
