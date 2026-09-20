# 002 · 顯示介面：MIPI DSI 與 RGB→HDMI

版本：v0.6 · 2026-09-20（原始 PDF 入庫,補完整腳位表與 §7 layout 建議）

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
ADV7511 RGB 輸入  ┘
```

**軟體切換不能把電氣負載切掉。** 跑 MIPI 模式時，ADV7511 的輸入電容
加上到 ADV7511 的走線，會變成掛在 1 Gbps 差分線上的 stub。

```
ADV7511 Input Capacitance   Typ 1.0 pF   Max 1.5 pF   (HW Guide Table 1, p.12)
IT66121（原方案）            約 5 pF
```

✅ **換料的意外好處：輸入電容只有原本的 1/3。** 掛在 MIPI 分支上的負載小得多。
但 §1.3 的「0Ω 貼著主幹」規則**不因此放寬** —— stub 長度的問題來自走線本身，不是電容。

而 §2.1 的規則已經寫得很清楚：**MIPI 不能有 stub。**

反過來看則寬鬆得多：跑 RGB 模式時，MIPI FPC 座的走線是掛在 148 MHz 單端線上的 stub，
短一點就沒事。**這個衝突是不對稱的 —— MIPI 受害，RGB 不受害。**

### 1.2 解法：PD0~PD9 用 0Ω 隔離，MIPI 直通

```
SoC PD0~PD9  ═══════════════════════════════▶  MIPI FPC 座   （直通，阻抗控制）
                   ║
                   ╚═[0Ω × 10]══════════════▶  ADV7511 低位輸入

SoC PD10~PD21 ─────────────────────────────▶  ADV7511        （不衝突，直接接）
```

```
要跑 MIPI    0Ω 不焊  →  ADV7511 輸入斷開，MIPI 線上乾淨
要跑 HDMI    0Ω 焊上  →  RGB 全部接通
```

**ADV7511 本體照樣上件**，只是輸入被 0Ω 斷開。
（ADV7511KSTZ **沒有 EPAD**，是可手焊的 0.5mm pitch 有腳封裝 —— 見 008-footprint.md §4A）
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

### 1.4 ADV7511 在 MIPI 模式要關掉

0Ω 拆掉後 ADV7511 的輸入浮接。**必須用 GPIO 控制它的 reset（或電源），
在 MIPI 模式時讓它保持 reset**，避免它亂驅動或耗電。

```
[ ] 原理圖上 ADV7511 的 RESET# 接一支 GPIO，不要直接上拉
[ ] 確認 ADV7511 的 reset 腳名稱與極性（回 datasheet Pin Description）
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
        └──▶ PD10~PD21 ───────────┴──▶ ADV7511 ──▶ HDMI Type-A
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

## 3. RGB 並列 → ADV7511 → HDMI

### 3.1 橋接晶片：IT66121 → **ADV7511**（v0.4 更換）

#### 換掉的理由：IT66121 原廠停產

```
IT66121FN   LCSC C2684803   庫存 0   "This product is no longer manufactured."
```

不是缺貨，是停產。完整盤點見 [009-bom.md](009-bom.md) §3。
並列 RGB 輸入 + 有貨 + 有 mainline driver 的候選只剩兩顆（ADV7511 / TFP410），
外加一顆有貨但無 mainline 的（MS7210）。

#### ⚠ 選型判準已經改變

v0.3 之前的判準是「**第一塊板不在 driver 上冒險**」—— 所以挑 driver 最省事的。

**這條判準對本專案已不適用。** 新的目標是累積 **HDMI/DP kernel driver porting
與 IC 驗證**的實作經驗（對應 MediaTek HDMI 軟韌體工程師職缺的工作內容），
**driver 工作本身就是要練的東西，省事等於沒練到。**

| | ADV7511 | TFP410 | MS7210 |
|---|---|---|---|
| driver porting | mainline `adv7511`，接到 sunxi TCON 是完整的 bridge 移植 | `ti-tfp410.c` 是啞橋接，**連 I2C 都沒有**，只有一支 power-down GPIO | 無上游，要從零寫（無暫存器文件） |
| 可驗證的項目 | EDID/DDC · HPD · HDCP · audio I2S + N/CTS · AVI/Audio InfoFrame · CEC · CSC | 只有 HPD + DDC 直通 | 功能齊，但驗的是自己寫的 driver |
| 價格 | $13.75 | $6.28 | $1.75 |
| 封裝 | LQFP-100 14×14 +EPAD | HTQFP-64 10×10 | QFN-64-EP 9×9 |

**選 ADV7511。** TFP410 是 DVI serializer，HDMI 協定層幾乎什麼都沒有，練不到東西；
MS7210 要從零寫 driver，沒有上游可對照，第一塊板風險過高且經驗不易轉移。

#### 這條路確實走得通

`(drivers/gpu/drm/sun4i/sun4i_rgb.c, torvalds/linux master, 2026-09-20)`

```c
drm_of_find_panel_or_bridge(tcon->dev->of_node, 1, 0, &rgb->panel, &rgb->bridge);
drm_bridge_attach(encoder, rgb->bridge, NULL, 0);
```

**sunxi TCON 的並列 RGB 輸出原生支援掛外部 `drm_bridge`。**
所以「把 bridge driver 接到新 SoC 的顯示輸出」有骨架可循，不是從虛空開始。

⚠ 但 `sun4i_rgb.c` 是 **panel 或 bridge 二選一**，不能同時掛。

#### 額外紅利：同一份 driver 也涵蓋 DSI 輸入

mainline `drivers/gpu/drm/bridge/adv7511/` 目錄同時含 **adv7533 / adv7535（MIPI DSI → HDMI）**。
這塊板本來就有 MIPI DSI —— **同一份 codebase 可以練兩條輸入路徑。**

#### ⚠ 缺口：DP 這塊板給不了

T113-S3 沒有 DP 輸出，三個方案都補不了。
DP 要靠 [ROADMAP](../ROADMAP.md) §6 的第 3 塊板（高速差分／DP 轉接板），
**該板的優先序應往上提。**

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

ADV7511 的視訊輸入腳叫 `D[35:0]`（24-bit 模式用 D[23:0]），同樣是 high-aligned。
**所以按 D 編號 1:1 接就對了，不必經過顏色名稱。** 完整接線見 §3.2.1。

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

### ✅ pixel clock 上限：SoC 200 MHz，橋接晶片 165 MHz —— 瓶頸在橋接晶片

`(DS §5.11.1 Table 5-18 LCD HV_IF Interface Timing Constants, p.61)`

```
DCLK cycle time    tDCLK    Min 5 ns    →   DCLK max = 200 MHz
```

```
T113-S3 TCON_LCD    200 MHz      (DS Table 5-18)
ADV7511             165 MHz      (ADI 產品頁：input up to 165 MHz / output 225 MHz)
1080p@60 所需        148.5 MHz    CEA-861
                    ───────────
瓶頸                 橋接晶片，不是 SoC
```

> 巧合：IT66121 的上限也是 165 MHz，**換晶片沒有改變這個結論。**

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

### ✅ ADV7511 的視訊輸入 AC 規格（已取得）

`(ADV7511 HW User's Guide Rev.D Table 1, p.13 —— 表頭標示 ADV7511KSTZ)`

```
Input Video Clock Frequency          Max 165    MHz
Input Video Data Setup   tVSU        Min 1.0    ns
Input Video Data Hold    tVHLD       Min 0.7    ns

TMDS Output Clock Frequency          20 ~ 225   MHz
TMDS Output Clock Duty Cycle         48 ~ 52    %
TMDS Differential Swing              800 / 1000 / 1200 mV
VSYNC/HSYNC Delay from DE Falling    1 UI
```

對照原方案：

```
              tSU      tHD      備註
IT66121       1.5 ns   0.7 ns   另有 TPJ 2.0 ns 的 jitter 上限
ADV7511       1.0 ns   0.7 ns   ⚠ datasheet 未給輸入時脈的 jitter 容許值
```

**ADV7511 的 setup 比 IT66121 寬鬆 0.5 ns，hold 相同。**

⚠ **ADV7511 沒有公布輸入 PCLK 的 jitter 容許值**（IT66121 給 2.0 ns）。
這一項無法直接比較 —— SSO 的影響仍要當成主要風險看待。

### skew budget（用 ADV7511 的真實數字）

```
148.5 MHz → Tpixel = 6.734 ns
扣 tVSU 1.0 ns + tVHLD 0.7 ns            → 剩 5.03 ns
給 T113 輸出 skew + 時脈 jitter 留 4.0 ns（保守，因為 T113 DS 沒給 Tco）
→ 剩 ~1 ns 給 PCB
FR4 傳播延遲 ~6.7 ps/mm
→ 1000 ps / 6.7 ps/mm ≈ 149 mm
```

**在 100×100mm 的板子上，兩條走線最多也差不到 149mm —— 等長在物理上不可能成為瓶頸。**
實作時對 CK 等長做到 ±10mm 即可，那是整齊，不是需求。

> **v0.5 已用 ADV7511 的實際 tVSU/tVHLD 重跑。** 結論不變，而且餘裕還多了 0.5 ns。
> 這一步不能省 —— 專案規則是「不把 A 晶片的數字掛到 B 晶片上」。

> ROADMAP 風險 ⑤ 把「RGB 並列等長」列為主要風險，**這個定性要下修**。
> 等長不是風險，SSO 與 jitter 才是。

**真正的殺手是 SSO noise（Simultaneous Switching Output）**：22 條線同時翻轉造成的地彈與 EMI。
地彈會直接吃掉橋接晶片的 jitter 預算 —— 這才是 148.5 MHz 下會出事的路徑。
**而 ADV7511 沒有公布輸入 jitter 容許值，等於這條風險沒有數字可以驗算。**

緩解手段：

```
串聯阻尼電阻   每條 22~33Ω，靠近驅動端（ADV7511 側或 SoC 側）
slew rate      SoC 端若可設定，降到剛好夠用
GND 回流       走線下方必須是完整 GND 平面
分組           資料線分成幾組，中間穿插 GND 走線
```

⚠ 22 條線加上串聯電阻 = **22 顆 0402 電阻**，再加 §1.2 的 **10 顆 0Ω 隔離**，
共 32 顆電阻要預留擺放空間。

⚠ PD0~PD9 那 10 條的阻尼電阻要放在 **0Ω 之後、靠 ADV7511 那側**，
不能放在主幹上 —— 主幹是 MIPI 的路徑，不能串任何東西。

### 3.2.1 ADV7511 的電源與電平

`(ADV7511 Hardware User's Guide Rev.D §4 Table 1, p.12-13 —— 表頭明確標示 ADV7511KSTZ)`

```
1.8V   DVdd / AVdd / PVdd / PLVdd / BGVdd     1.71 / 1.80 / 1.90 V    ← 五個域
3.3V   MVdd                                   3.15 / 3.30 / 3.45 V

雜訊上限   DVdd 64 mV RMS · PVdd 64 mV RMS · BGVdd 64 mV RMS
           AVdd / PLVdd 見 HW Guide §7.1（類比，更嚴）

功耗   326 mW 總計（1.8V = 325 mW → 約 180 mA，3.3V = 1 mW）
       條件 1080p / 36-bit；本板用 RGB666 會更低，但照最壞情況設計
待機   Power-Down L1 20 mA · L2 300 µA
```

⚠ **是五個 1.8V 域不是四個** —— v0.4 寫四個是抄 ADV7511W 的。
KSTZ 多一個 **PLVdd（HDMI PLL – Analog）**，而且 3.3V 那條叫 **MVdd** 不是 `DVDD_3V`。

#### ✅ 視訊輸入腳 3.3V 可直接驅動

```
Data Inputs – Video / Audio / CEC_CLK
  VIH   Min 1.35   Max 3.5 V
  VIL   Min -0.3   Max 0.7 V
```

**VIH 上限 3.5V → 3.3V CMOS 直接驅動沒問題。**
VCC-PD = 3.3V 的決定不必推翻，22 條 RGB 線不需要電平轉換。

#### ⚠ 但 1.8V 軌要加大

```
001-power.md §2.2 原本的 1.8V 已知負載      約  52 mA
ADV7511                                    約 180 mA
                                           ──────────
                                           約 232 mA
晶片內建 LDOA 上限                             260 mA   ← 貼滿，且 VDD18-DRAM 仍是 TBD
```

**外部 1.8V LDO 變成必須，且不能用 XC6206（典型僅 200 mA）。**
改用 **AP2112K-1.8TRG1**（`C176944`，600 mA）。

五個 1.8V 域各有雜訊上限（DVdd/PVdd/BGVdd 各 64 mV RMS，AVdd/PLVdd 更嚴），
**要分組並各自用磁珠或 LC 從幹線隔開**，PLL 那兩支（PVdd/PLVdd）最敏感。

```
[ ] 取 HW Guide §7.1 的去耦與分域建議（目前只有 Table 1 的雜訊上限數字）
```

#### 電源域淨變化：5 組回到 4 組

```
IT66121 方案   3.3 / 1.5 / 0.9 / 1.8 / 1.2   5 組
ADV7511 方案   3.3 / 1.5 / 0.9 / 1.8          4 組   ← 1.2V 消失，1.8V 加大
```

#### RGB666 接到 ADV7511 的 D[23:18] / D[15:10] / D[7:2]

ADV7511 的輸入腳是 `D[35:0]`（最寬支援 36-bit deep color），
**24-bit 模式用 D[23:0]，與 T113 的 `LCD0-D[23:0]` 同樣 high-aligned。**

```
T113 LCD0-D23..D18  →  ADV7511 D23..D18      （R5..R0）
T113 LCD0-D15..D10  →  ADV7511 D15..D10      （G5..G0）
T113 LCD0-D7..D2    →  ADV7511 D7..D2        （B5..B0）

ADV7511 D17/D16 · D9/D8 · D1/D0  →  GND
ADV7511 D35..D24                 →  GND（deep color 未用）
```

`(HW Guide Table 3, p.19)`

```
D[35:0]   pin 57-74, 78, 80-96      CLK  pin 79
DE  pin 97      HSYNC  pin 98      VSYNC  pin 2
```

⚠ **pin 79 (CLK) 夾在 D 的兩段腳號中間** —— D 索引與腳號的對應要開
Figure 6 (p.18) 的腳位圖核對，Table 3 只給範圍。

```
[ ] 開 Figure 6 確認 D[35:0] 的索引↔腳號對應
[ ] 未用的 D[35:24] 與 D[17:16]/D[9:8]/D[1:0] 的處置（datasheet 未明說，
     慣例是接 GND；要確認 ADI 有無反對）
```

### 3.2.2 ★ 原理圖必備的外部元件（§7, p.52-54）

這些是 datasheet 明列的**硬性要求**，漏一個就可能不動或不穩：

```
R_EXT (pin 28)      887 Ω ±1% 接地            ★ 設定內部參考電流
                    走線越短越好
                    ⚠ 特別點名 LRCLK（含 via）不可靠近 pin 28

DDCSDA / DDCSCL     1.5k ~ 2kΩ ±5% 上拉到 HDMI +5V    ★ 原文寫 "is required"
SDA / SCL           2 kΩ ±5% 上拉到 1.8V 或 3.3V
INT (pin 45)        2 kΩ ±10% 上拉到 MCU 的 IO 電源（本板 = 3.3V）

CEC (pin 48)        27 kΩ 上拉到 3.3V，漏電流 < 1.8 µA
CEC_CLK (pin 50)    ⚠ 需要外部振盪器：預設 12 MHz，3~100 MHz ±2%
```

⚠ **CEC 不是免費的** —— 要多一顆振盪器。
SPEC 原本就決定「CEC 可選，V1 不做」，現在有了明確理由：**省一顆料。**
CEC_CLK 不接時要確認 ADV7511 的行為（CEC 功能停用即可）。

#### ⚠ PD/AD (pin 38) 一腳兩用 —— 原理圖上必須明確定義

```
"The I2C address and the PD polarity are set by the PD/AD pin state
 when the supplies are applied to the ADV7511."
```

**上電當下的腳位狀態同時決定 I2C 位址與 Power-Down 極性。**
不能只當成一般 GPIO 隨便接 —— 要嘛固定上/下拉，要嘛接 GPIO 但確保上電時的準位確定。

```
[ ] 決定 PD/AD 的接法，並在原理圖上標註它決定的 I2C 位址
```

### 3.2.3 ★ CLK 要做阻抗控制（新增的 layout 需求）

`(§7.2, p.53)`

```
"Any noise that is coupled onto the CLK input trace will add jitter to the system.
 It is recommended to control the impedance of the CLK trace."
→ 走線下方用完整 GND 或電源參考面，確保全長阻抗一致
→ CLK (pin 79) 走線盡量短
→ 旁邊不要走數位或其他高頻訊號
```

⚠ **這是單端訊號的阻抗控制需求。** 005-stackup.md 原本只規劃了
13 對差分的阻抗控制，**LCD0-CLK 這條單端線要另外列入**。

#### 關於資料線等長：ADI 的說法要照做

```
"Make sure to match the length of the input data signals to optimize data capture
 especially for Double Data Rate (DDR) input formats."
```

我們在 §3.2 算出 PCB skew 有 ~149mm 餘裕、結論是「等長不是瓶頸」——
**那個計算仍然成立**（本板是 SDR 單邊緣，比 DDR 寬鬆得多）。
但**原廠明確建議等長，所以照做** —— 做到對 CK ±10mm 本來就是免費的。

**計算說明的是「做不到也不會死」，不是「可以不做」。**

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
| 額外零件 | FPC 座 | ADV7511 + 22 顆阻尼電阻 + 10 顆 0Ω + ESD |
| 板面積 | 小 | **大** |
| 驗證難度 | 高（要有面板、要調參數） | **低（插螢幕就能看）** |

**bring-up 順序建議：先驗 HDMI，再驗 MIPI。**
HDMI 只要 driver 起來就有畫面，是最快能確認「顯示鏈路通了」的路徑。
MIPI 還要對面板 timing、init sequence、lane 設定，變因多得多。

---

## 5. 驗收

```
[ ] ★ R_EXT = 887Ω ±1%，走線短，LRCLK 與 via 不靠近 pin 28
[ ] ★ DDCSDA/DDCSCL 上拉 1.5k~2kΩ 到 HDMI +5V（datasheet 寫 required）
[ ] ★ SDA/SCL 上拉 2kΩ、INT 上拉 2kΩ 到 3.3V
[ ] ★ PD/AD (pin 38) 接法已定義，且原理圖標註它決定的 I2C 位址
[ ] ★ LCD0-CLK 列入阻抗控制清單（單端），走線短、旁無高頻訊號
[ ] ADV7511 五個 1.8V 域分成 3 組，各加 10µH + 10µF 的 LC
[ ] 每支電源腳 0.1µF 貼近腳位；GND 腳各自用 via 下 GND plane
[ ] MIPI 5 對阻抗 100Ω，對內等長 ±0.1mm，全程不跨分割
[ ] MIPI 線上無串聯電阻、無 AC 耦合電容
[ ] TMDS 4 對阻抗 100Ω，對內等長 ±0.15mm
[ ] RGB 22 條對 CK 等長，串聯阻尼電阻已放且靠近驅動端
[ ] HDMI ESD 保護已放，電容 <1pF
[ ] DDC 上拉到 5V
[x] 橋接晶片的 RGB 輸入時脈上限 ≥ 目標解析度所需
      → ADV7511 輸入上限 165 MHz，1080p60 的 148.5 MHz 在範圍內
[ ] ADV7511 的 1.8V 域（DVDD/AVDD/PVDD/BGVDD）分成 3 組並各加 LC 濾波
[ ] 1.8V LDO 為 600mA 等級（AP2112K-1.8），不是 XC6206
[ ] ADV7511 的五個 1.8V 域（DVdd/AVdd/PVdd/PLVdd/BGVdd）分組並各自隔離
[ ] ADV7511 的 MVdd 接 3.3V
[ ] ADV7511 的 D[17:16] / D[9:8] / D[1:0] 接 GND（RGB666 未用的 6 個 LSB）
[ ] ADV7511 未用的 D[35:24] 處置已依 datasheet 確認
[ ] 原理圖上 RGB 接線一律標 LCD0-D 編號，不用顏色名稱（避免 R/B 對調）
[ ] ADV7511 的 RESET# 接 GPIO（MIPI 模式時保持 reset）
[ ] ADV7511 footprint：`LQFP-100_14x14mm_P0.5mm`（MS-026-BED，**無 EPAD**，見 008-footprint.md §4A）
```

---

## 6. ADV7511 的 driver 工作（本專案的主要學習目標之一）

### 6.1 Porting 路徑

```
drivers/gpu/drm/sun4i/sun4i_rgb.c        TCON 並列 RGB 輸出，支援掛 drm_bridge
drivers/gpu/drm/bridge/adv7511/          mainline bridge driver
  ├─ adv7511_drv.c      主體、DT binding、drm_bridge ops
  ├─ adv7511_cec.c      CEC
  ├─ adv7511_audio.c    HDMI audio（I2S → N/CTS 重生）
  └─ adv7533.c          MIPI DSI 輸入版（adv7533/adv7535）
```

DTS 大致形狀：

```dts
&tcon0_out {
    tcon0_out_adv7511: endpoint { remote-endpoint = <&adv7511_in>; };
};

&i2c1 {
    hdmi@39 {
        compatible = "adi,adv7511w";
        reg = <0x39>;
        interrupt-parent = <&pio>; interrupts = <...>;
        adi,input-depth = <8>;
        adi,input-colorspace = "rgb";
        adi,input-clock = "1x";
        ports {
            port@0 { adv7511_in: endpoint { remote-endpoint = <&tcon0_out_adv7511>; }; };
            port@1 { adv7511_out: endpoint { remote-endpoint = <&hdmi_con_in>; }; };
        };
    };
};
```

⚠ 上面是依 `Documentation/devicetree/bindings/display/bridge/adi,adv7511.txt` 的
**記憶形狀，不是抄自實機**。實作前要對著該 binding 逐欄核對。

### 6.2 IC 驗證清單（對應職缺的「HDMI IC 驗證」）

```
[ ] HPD 偵測：插拔線時 /sys/class/drm/.../status 正確變化
[ ] EDID 讀取：edid-decode 解出正確的 mode 清單
[ ] mode setting：modetest -s 切換多組解析度都出畫面
[ ] AVI InfoFrame：內容正確（色彩空間、量化範圍、aspect ratio）
[ ] HDMI vs DVI 模式切換
[ ] HDMI audio：I2S 餵進去，N/CTS 重生正確，螢幕喇叭有聲
[ ] Audio InfoFrame 正確
[ ] CEC：能收發基本訊息
[ ] HDCP：認證流程能過（若螢幕支援）
[ ] 熱插拔穩定性：反覆插拔不掉 link、不 oops
```

**這份清單就是這塊板在 driver 層面的驗收標準。**
RGB666 只有 18-bit，所以量化範圍與 deep color 那幾項的預期值要相應調整。
