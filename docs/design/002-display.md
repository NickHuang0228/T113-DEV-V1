# 002 · 顯示介面：MIPI DSI 與 RGB→HDMI

版本：v0.2 · 2026-09-18（查完 pin mux 表後重寫架構，v0.1 的假設是錯的）

**專案優先序：MIPI DSI > RGB/HDMI。** 長期目標是 DSI layout 經驗，HDMI 是附帶。

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

### ⚠ T113-S3 的 RGB 最多只到 RGB666，沒有 RGB888

`(DS Table 4-3 Pin Multiplexing, PD bank)`

```
LCD0-D2  ~ D7    PD0  ~ PD5    R[7:2]   6 bit
LCD0-D10 ~ D15   PD6  ~ PD11   G[7:2]   6 bit
LCD0-D18 ~ D23   PD12 ~ PD17   B[7:2]   6 bit
LCD0-CLK         PD18
LCD0-DE          PD19
LCD0-HSYNC       PD20
LCD0-VSYNC       PD21
```

**LCD0-D0 / D1 / D8 / D9 / D16 / D17 在 PD bank 上不存在。**
`(DS §2.6.1 p.6 也只寫 "RGB666 and RGB565 with dither function")`
MangoPi 原理圖自己的註記也是 `RGB666=PD0~PD21`。

```
v0.1 寫    24 資料 + 4 控制 = 28 條單端      ✗
實際       18 資料 + 4 控制 = 22 條單端      ✓
```

**後果：HDMI 輸出的顏色深度是 RGB666（26 萬色），不是 RGB888（1670 萬色）。**
漸層會有可見的 banding。IT66121 支援 RGB666 輸入，功能上沒問題，
T113 的 DE 也有 dither 可以緩解。

**這也是「MIPI 優先」的另一個理由 —— MIPI DSI 支援 RGB888，RGB 並列不支援。**

```
訊號數       18 資料 + HS + VS + DE + CK = 22 條單端
pixel clock  1080p@60 約 148.5 MHz（⚠ 待確認 T113 與 IT66121 的上限）
解析度上限   RGB 1920×1080@60  /  MIPI DSI 4-lane 1920×1200@60   (DS §2.6 p.6)
```

**skew budget 比直覺寬鬆**：

```
148.5 MHz → 週期 6.73 ns
扣掉 setup/hold 各約 1 ns → 約 4.7 ns 給 jitter + skew
FR4 傳播延遲 ~6.7 ps/mm
→ 等長容忍約 ±100mm（遠比 DDR3 的 ±0.6mm 寬鬆）
```

**真正的殺手是 SSO noise（Simultaneous Switching Output）**：24 條線同時翻轉造成的地彈與 EMI。

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
| 單端線 | 0 | **28** |
| 額外零件 | FPC 座 | IT66121 + 28 顆阻尼電阻 + ESD |
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
[ ] IT66121 的 RGB 輸入時脈上限 ≥ 目標解析度所需
```
