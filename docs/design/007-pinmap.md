# 007 · 腳位分配與 bank 策略

版本：v0.2 · 2026-09-19（WiFi footprint 移除，PG bank 全部給排針）

**資料來源**：`T113-S3_Datasheet_v1.6` Table 4-2（Pin Characteristics）與 Table 4-3（Pin Multiplexing）。

⚠ 以下腳位表由 `pdftotext` 抽取後整理，**Table 4-2 的欄位在抽取時會錯位**。
進原理圖前每一支腳都要回 `p.77 Figure 7-1 Pin Map` 目視核對。

---

## 1. 為什麼先做 pin map 才畫原理圖

腳位分配不是電氣問題，是**平面配置問題**：

```
RGB bank 在晶片哪一側  →  IT66121 就得放哪一側
RMII bank 在哪一側     →  RJ45 就得放哪一側
```

**填 pin map 的同時，其實已經把 100×100mm 上的元件位置決定掉了。**
所以 pin map 要和一張手繪 placement 草圖一起迭代 —— 畫不出合理配置就回頭改 pin map，
這時候改是免費的。

---

## 2. Bank 是什麼，以及為什麼它決定災損範圍

一個 bank 共用三件事：

```
① IO 電源域       整個 bank 的 IO buffer 吃同一條 VCC
② 控制暫存器       同一組 CFG / DATA / DRV / PULL / EINT
③ ★ die 上的物理位置   同一 bank 的 IO cell 在晶片邊緣是連在一起的一段
```

**第三項才是「燒一支死一片」的原因。**

### 2.1 三種連坐機制

**① ESD 二極體燒穿 → 拉垮整條 VCC**

```
        VCC_bank
           │
          ─┴─ ▲   上箝位二極體
   PIN ────┼──┤
          ─┬─ ▲   下箝位二極體
           │
          GND
```

外部灌入超過 `VCC + 0.3V` 時上二極體導通（正常保護），但電流太大會燒成短路 ——
那支腳就變成 VCC 對外的低阻通路，**整條 VCC_bank 被拉低，該 bank 全滅**。

**② Latch-up 燒掉 die 上一整段（最惡性）**

CMOS IO 裡有寄生 SCR。過壓觸發後在 VCC/GND 間形成自我維持的低阻通路，
電流可達數百 mA 且集中在一小塊區域 → 金屬連線熔斷。

**熔掉的不是一個點，是那一段 IO ring。** 災損邊界剛好落在 bank 上，
不是因為設計者分組，是因為**物理上它們本來就擠在一起**。

**③ 控制邏輯區受損** —— 少見，但整個 bank 的 mux 會失效。

### 2.2 高速介面的資料線不在 bank，但控制線一定在

```
不在 GPIO bank（專用 PHY pad）
  MIPI D0±/CK±、HDMI TMDS、USB DP/DM

在 GPIO bank（一般 IO mux）
  面板 RESET、背光 EN、PWM 調光、觸控 INT/RST
  HDMI HPD / CEC / DDC(I2C) / 5V EN
  USB VBUS EN / OTG ID / 過流 OC
  PHY RESET / MDC / MDIO
```

**所以一個 bank 死掉，會讓一堆「資料通道其實好好的」介面全部初始化失敗。**
這是設計時要刻意打散控制訊號的理由。

---

## 3. T113-S3 的 bank 地圖與災損半徑

`(DS Table 4-2 的 Power Supply 欄實測)`

| Bank | 電源域 | 電壓 | 這塊板拿來做什麼 | **燒了會怎樣** |
|---|---|---|---|---|
| PB | VCC-IO | 3.3V 固定 | UART0 log、I2S 音訊 | **失去 console** |
| PC | VCC-IO | 3.3V 固定 | SPI0 → SPI NOR | **失去備援開機** |
| PF | VCC-IO | 3.3V 固定 | SDC0 → microSD | **失去主要開機** |
| PD | VCC-PD | 1.8 / 3.3V 可選 | MIPI DSI + RGB666 | 顯示全失 |
| PE | VCC-PE | 1.8 / 2.8 / 3.3V | RMII → RTL8201F | **失去 TFTP/NFS 開發循環** |
| PG | VCC-PG | 1.8 / 3.3V 可選 | **全部給排針**（WiFi 已移除） | **幾乎無損失** |

> ⚠ **PB / PC / PF 三個 bank 綁在同一條 VCC-IO 上。**
> 那條軌上掛著：主要開機裝置 + 備援開機裝置 + 唯一的 log 輸出。
> **VCC-IO 是這塊板的命脈，一掛就變成無法診斷的磚。**

**PG 是唯一「燒了也不痛」的 bank。** 所有對外接點優先放這裡。

> **v0.2 決定：移除 WiFi footprint，PG 16 支全部給排針。**
> 原本 WiFi 的 SDIO1 佔 PG0~PG5，等於一個永遠不焊的模組吃掉最安全 bank 的 37%。
> 見 [003-network.md](003-network.md) §6。

---

## 4. 四條設計規則

### 規則 ① 對外的腳絕對不放 VCC-IO（PB / PC / PF）

排針是全板最容易燒的地方 —— 手滑短路、接錯模組、熱插拔、外部電源倒灌。

```
排針放 PB/PC/PF  →  燒了同時失去 SD 開機 + NOR 開機 + UART log  →  變磚
排針放 PG        →  燒了只失去排針本身
```

### 規則 ② 每支對外訊號串限流電阻

```
GPIO / UART / SPI     330Ω
I2C                   100Ω   （太大會拖慢上升沿）
電源與 GND            不串
```

```
對功能幾乎無影響   CMOS 輸入阻抗 MΩ 級，串 330Ω 不影響準位
對保護影響很大     誤接 5V 時電流從「無限大」變成 (5-3.3)/330 ≈ 5 mA
                  ESD 二極體撐得住 5mA，撐不住 500mA
```

**約 20 顆 0603 電阻換整個 bank 的命。**

### 規則 ③ 關鍵控制訊號刻意打散到不同 bank

```
不要   面板 RESET、IT66121 SYSRSTN、PHY RESET、USB VBUS EN 全放同一個 bank
要     刻意分散
```

⚠ 這跟 layout 的「就近原則」直接衝突。**取捨原則：控制訊號本來就慢，走遠一點沒差，
優先分散；只有高速訊號才照就近原則。**

### 規則 ④ 先定 bank 電壓，再分配腳位

```
VCC-PD 因 MIPI 而選 1.8V  →  PD bank 上所有腳都是 1.8V
→ 排針若放 PD，外接 3.3V 模組就電平不相容
```

---

## 5. 已確認的衝突

| 衝突 | 腳位 | 處理 |
|---|---|---|
| MIPI DSI ↔ RGB(HDMI) | PD0 ~ PD9 | 10 顆 0Ω 隔離，MIPI 直通。見 [002-display.md](002-display.md) §1 |
| Parallel CSI ↔ RMII | PE0 ~ PE9 | **砍掉 CSI**，攝影機走 USB UVC |
| SPI1 ↔ RGB | PD10 ~ PD15 | SPI1 **只在 MIPI 模式可用** |
| SPI0 ↔ SPI NOR | PC2 ~ PC7 | SPI0 是備援開機裝置，**不可拉到排針** |
| **UART0 ↔ SDC0 / RMII** | **PF2 / PF4** | **2 顆 0Ω 分支到 CH340N**，見 §5.2 |
| **SPI0 ↔ BOOT-SEL strap** | **PC4 / PC5** | 上下拉電阻決定開機來源，見 §5.3 |
| **JTAG ↔ SDC0** | PF0 / PF1 / PF3 / PF5 | 放棄 JTAG，改留 4 個測試點（成本 $0） |

### 5.1 ⚠ PB0 / PB1 在 eLQFP128 上不存在

從 `tools/t113s3_pins.csv`（Table 4-2 實抽）確認：

```
GPIOB 只有 6 支   79:PB7  80:PB6  82:PB5  84:PB4  85:PB3  86:PB2
```

**沒有 PB0、PB1。** §6.3 原本寫的「PB0~PB1 → UART0 → CH340N（console）⚠ 腳位待確認」
不是待確認，是**那兩支腳沒有被引出來**。

### 5.2 UART0 沒有獨立腳位 —— 這塊板的生命線衝突

Table 4-3 裡 UART0 只有兩組 mux，兩組都撞到別人：

```
PE2 / PE3   UART0-TX/RX  ←→  RGMII-RXD1 / RGMII-TXCK (RMII)   撞乙太網路
PF2 / PF4   UART0-TX/RX  ←→  SDC0-CLK / SDC0-D3              撞 microSD
```

**而 BROM 的 debug log 寫死走 UART0**，改不了。004-usb-boot.md 把它列為 bring-up 生命線。

**決定：走 PF2 / PF4，用 2 顆 0Ω 分支到 CH340N。**

理由是這兩個功能**在時間上本來就不重疊**：

```
BROM 階段      PF2/PF4 = UART0    印開機 log     ← CH340N 收得到
切到 SD 讀卡    PF2/PF4 = SDC0     跑 50MHz 時脈  ← CH340N 收到亂碼（正常，非故障）
Linux 起來後    console 改用 UART1（PG13/PG15 或 PG7/PG8）
```

0Ω 的作用是**必要時能完全斷開**：CH340N 的輸入電容（~5~10pF）掛在 50MHz 的 SDC0-CLK 上，
理論上 SD 高速模式可能受影響。SD 跑不穩時拆掉 0Ω 即可定位。

⚠ 0Ω 焊盤距主幹 **≤0.5mm**，與 PD0~PD9 那 10 顆同一條規則（見 005-stackup.md §3）。

**不選 PE2/PE3 的理由**：RMII 需要 PE0~PE9 連續 7 條訊號 + MDC/MDIO，抽掉兩條就不能用，
而乙太網路是 TFTP+NFS 開發循環的基礎（003-network.md §1）。

**為什麼不把 microSD 移到 SDC1（PG0~PG5）**：

```
SDC0   PF0~PF5    ← BROM 原生開機裝置
SDC1   PG0~PG5    ← 通常給 SDIO 週邊，BROM 一般不從這裡開機
SDC2   PC2~PC7    ← 與 SPI0 共用，已給 SPI NOR
```

把 SD 移到 PG 會同時失去「BROM 能開機」和「排針 6 支腳」，兩頭皆輸。

### 5.3 PC4 / PC5 同時是 BOOT-SEL strap

```
PC4   SPI0-MOSI   SDC2-D2   BOOT-SEL0
PC5   SPI0-MISO   SDC2-D1   BOOT-SEL1
```

**SPI NOR 的 MOSI/MISO 腳同時是開機來源的 strap pin。** BROM 上電時讀這兩支的電平
決定從哪個裝置開機，之後才切成 SPI 功能。

⚠ 原理圖階段必須確認：SPI NOR 本身的輸入阻抗、以及是否需要外加上下拉電阻，
才能保證 strap 電平正確。**這是「上電瞬間的電平」問題，不是「訊號完整性」問題** ——
量測時要抓上電那一刻，不是穩態。

### 5.4 JTAG 讓給 SD 卡

```
PF0 = JTAG-MS    PF1 = JTAG-DI    PF3 = JTAG-DO    PF5 = JTAG-CK
```

PF bank 給 SDC0 之後 JTAG 就沒了。**對 Linux 板影響不大**（靠 UART + FEL 就能除錯，
JTAG 還要額外的 debugger 硬體）。

**做法：在這 4 支腳旁放 4 個測試點**，需要時飛線接。成本 $0，保留退路。

---

## 6. Bank 分配（草案）

### 6.1 PD bank — 顯示（VCC-PD）

```
PD0 ~ PD9     MIPI DSI 4-lane + CLK   ★ 優先
              ／ RGB666 低 10 位（經 0Ω）
PD10 ~ PD17   RGB666 其餘 8 位
PD18 ~ PD21   LCD0-CLK / DE / HSYNC / VSYNC
PD22          OWA-OUT / IR-RX / UART1-RX / GPIO
```

**MIPI 模式下 PD10~PD21 閒置**，其中 PD10~PD13 借給排針當 SPI1（見 §7.3）。
PD14~PD21 保持閒置，不對外 —— PG 的 GPIO 已經夠用，不必增加 VCC-PD 的暴露面。

⚠ VCC-PD 電壓待定：要同時滿足 MIPI 與 IT66121 的 OVDD（1.8 / 2.5 / 3.3V 皆可）。

### 6.2 PE bank — 乙太網路（VCC-PE）

```
PE0   RMII-CRS-DV        PE5   RMII-TXD1
PE1   RMII-RXD0          PE6   RMII-TX-EN
PE2   RMII-RXD1          PE8   MDC
PE3   RMII-REF-CLK       PE9   MDIO
PE4   RMII-TXD0          PE10  EPHY-25M（或 PHY RESET）
                         PE11 ~ PE13  空
```

CSI 砍掉後 PE bank 單純化。**PE11~PE13 保留為 PHY RESET / LED 控制，不對外。**

### 6.3 VCC-IO bank（PB / PC / PF）— 命脈，全部不對外

```
PF0 ~ PF5    SDC0 → microSD（主要開機）
             ├ PF2 / PF4 另經 2 顆 0Ω 分支到 CH340N（UART0 console）  → §5.2
             └ PF0 / PF1 / PF3 / PF5 旁放 4 個 JTAG 測試點           → §5.4
PF6          備用
PC2 ~ PC7    SPI0 → SPI NOR 16MB（備援開機）
             └ ⚠ PC4 / PC5 同時是 BOOT-SEL strap                    → §5.3
PB2 ~ PB7    I2S2 音訊 codec / TWI 備用
             └ ⚠ 沒有 PB0 / PB1，此封裝未引出                       → §5.1
```

### 6.4 PG bank — 全部給排針（VCC-PG）

```
PG0 ~ PG15   ★ 排針區，16 支全可用（WiFi footprint 已移除）
```

VCC-PG 不再被 SDIO 電平綁住 → **選 3.3V**，配合外接模組。

**PG bank 的 mux 資源意外地好：**

```
PG7  / PG8    TWI2-SCK / TWI2-SDA    ← 完整 I2C
PG9  / PG10   TWI1-SCK / TWI1-SDA    ← 完整 I2C
PG11 / PG12   TWI3-SCK / TWI3-SDA    ← 完整 I2C
PG13 / PG15   TWI0-SCK / TWI0-SDA    ← 完整 I2C
PG13 / PG15   也可當 UART1-TX / RX
PG7  / PG8    也可當 UART1-TX / RX
PG6, PG14     純 GPIO（mux 選項少）
```

**四組完整 I2C，SPEC 只要兩組 → 綽綽有餘。**

⚠ **但 PG bank 上完全沒有 SPI mux。** 排針的 SPI 只能從 PD 的 SPI1 借。

---

## 7. 排針規格（草案）

### 7.1 能提供多少

```
GPIO        10 支  ✓ 隨時可用   PG0~PG6, PG11, PG12, PG14
I2C          2 組  ✓ 隨時可用   PG7/PG8 (TWI2)、PG9/PG10 (TWI1)
UART 備援    1 組  ✓ 隨時可用   PG13/PG15 (UART1)
SPI          1 組  ⚠ 僅 MIPI 模式   PD10~PD13 (SPI1)
```

### 7.2 帳怎麼算的

```
PG 總共 16 支（WiFi footprint 已移除，全部可用）
  − 4 支  I2C ×2
  − 2 支  UART 備援
  = 10 支 純 GPIO
```

**PG bank 沒有任何 SPI mux**，所以 SPI 只能從 PD 的 SPI1 借（§7.3）。

**不再需要借 PD14~PD21 當 GPIO** —— PG 的 10 支已經夠用，
少借 8 支就少 8 條掛在 VCC-PD 上的對外風險。

### 7.3 借用 PD10~PD13（SPI1）的條件與風險

```
可行   MIPI 模式下 PD10~PD13 完全閒置
       這些是 RGB 線（148MHz 單端），不是 MIPI 差分線（PD0~PD9）
       加 330Ω 後，排針分支的電容被隔離，對 RGB 影響可忽略

風險   排針短路若燒掉 VCC-PD → 連 MIPI 一起失去
緩解   330Ω 串聯，誤接 5V 時只有 5mA，ESD 二極體撐得住
限制   HDMI 模式下 PD10~PD13 被 RGB 佔用，排針上的 SPI 失效
       （GPIO 不受影響，全部在 PG）
```

### 7.4 排針配置（草案）

```
 1  3.3V          2  5V
 3  GND           4  GND
 5  I2C1-SCL      6  I2C1-SDA      PG7  / PG8    100Ω
 7  I2C2-SCL      8  I2C2-SDA      PG9  / PG10   100Ω
 9  UART-TX      10  UART-RX       PG13 / PG15   330Ω
11  SPI-CS       12  SPI-CLK       PD10 / PD11   330Ω  ⚠ 僅 MIPI 模式
13  SPI-MOSI     14  SPI-MISO      PD12 / PD13   330Ω  ⚠ 僅 MIPI 模式
15  GPIO0        16  GPIO1         PG0  / PG1    330Ω
17  GPIO2        18  GPIO3         PG2  / PG3    330Ω
19  GPIO4        20  GPIO5         PG4  / PG5    330Ω
21  GPIO6        22  GPIO7         PG6  / PG11   330Ω
23  GPIO8        24  GPIO9         PG12 / PG14   330Ω
25  3.3V         26  GND
27  GND          28  GND
```

```
28 pin (2×14)，2.54mm 排針，長度約 35.6mm
訊號 20 支 + 電源/地 8 支
限流電阻 20 顆 0603（I2C 用 100Ω ×4，其餘 330Ω ×16）
```

---

## 8. 待決事項

```
[ ] VCC-PD 電壓：1.8V 或 3.3V（要同時滿足 MIPI 與 IT66121 OVDD）
[ ] VCC-PE 電壓：1.8 / 2.8 / 3.3V（要滿足 RTL8201F 的 IO 電平）
[x] VCC-PG 電壓 → **3.3V**（WiFi 移除後不再被 SDIO 綁住，配合外接模組）
[x] WiFi footprint → **移除**，PG0~PG5 釋放給排針（2026-09-19 決定）
[ ] UART0 (console) 的實際腳位（PB bank，待 p.77 核對）
[ ] 各介面控制訊號的分散配置（面板 RST、IT66121 SYSRSTN、PHY RST、USB VBUS EN）
[ ] 全部腳位回 p.77 Figure 7-1 目視核對
[ ] 手繪 placement 草圖，與本表一起迭代
```

---

## 9. 驗收

```
[ ] 13 對差分的走向在 placement 草圖上不交叉
[ ] RGB 22 條不需要跨過晶片到對側
[ ] 對外訊號全部有限流電阻，且不在 VCC-IO bank
[ ] 關鍵控制訊號分散於 ≥3 個 bank
[ ] 每支腳的 mux 功能有 datasheet 出處（Table 4-3）
```
