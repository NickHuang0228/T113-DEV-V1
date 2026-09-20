# 011 · 電源樹定案

版本：v0.1 · 2026-09-21

本文件把 [001-power.md](001-power.md) 的分析收斂成**可以直接畫原理圖的數字**：
每條軌的來源、元件料號、分壓值、時序電路、去耦。

---

## 1. 電源樹

```
Type-C VBUS  +5V_VBUS
  │
  ├─ RY1303 CH3 ──▶ +3V3        VCC-IO · VCC-PD · VCC-PE · VCC-PG · VCC-TVOUT
  │                              LDO-IN · RTL8201F · CH340N · ADV7511 MVDD
  │                              兩顆 1.8V LDO 的輸入 · 上拉與 LED
  │
  ├─ RY1303 CH2 ──▶ +1V5        VCC-DRAM0/1
  │
  ├─ RY1303 CH1 ──▶ +0V9        VDD-CORE0/1 · VDD-SYS0/1/2
  │
  ├─ +3V3 ─[LDO1]─▶ +1V8_SOC    VCC-PLL · VCC-RTC · VCC-LVDS · VCC-TVIN
  │                              AVCC · HPVCC · VDD18-DRAM
  │
  ├─ +3V3 ─[LDO2]─▶ +1V8_HDMI   ADV7511 專屬，再分 3 組（見 §5）
  │                    ├─[10µH+10µF]─▶ +1V8_DVDD    pin 1,19,49,76,77
  │                    ├─[10µH+10µF]─▶ +1V8_AVDD    pin 29,34,41 + 24,25
  │                    └─[10µH+10µF]─▶ +1V8_PLVDD   pin 21 + 26
  │
  └─ +5V_VBUS ─[TPS2051B]─▶ +5V_USB   USB-A Host（限流）
```

### 1.1 Net 命名

```
+5V_VBUS · +5V_USB · +5V_HDMI
+3V3
+1V8_SOC · +1V8_HDMI · +1V8_DVDD · +1V8_AVDD · +1V8_PLVDD
+1V5 · +0V9
GND
```

⚠ **+5V_HDMI 是 HDMI 座上的 +5V（DDC 上拉用），與 +5V_VBUS 分開命名** ——
它接到外部螢幕，要獨立看待。

---

## 2. RY1303 三路 DC-DC

`(RY1303 Datasheet V1.0.x，已取得：docs/reference/peripherals/RY1303_datasheet.pdf)`

```
LCSC C370881 · QFN20-3×3 · 庫存 23,969 · $0.20
Vin          2.7 ~ 5.5 V
每通道電流    0 ~ 2 A
⚠ 三通道總輸出功率必須 < 6 W
FB 電壓      0.585 / 0.600 / 0.615 V   (±2.5%)
切換頻率      1.2 MHz 固定
EN 上升閾值   1.2 V (min)   下降閾值 0.6 V (max)
軟啟動        1 ms typ
UVLO         喚醒 2.5~2.6 V，關閉 1.8~1.9 V
上管電流限制   3 A
熱關斷        160 °C
θJA          43.7 °C/W
pin 21       EP，必須焊到大片銅箔
```

### 2.1 ⚠ 更正 001-power.md 的一個錯誤

001-power.md §2.3 的比較表寫 RY1303 的優點是「**EN1/EN2/EN3 內建順序**」。

**錯的。** datasheet 寫的是：

```
"the independent enable control makes the designer have the greatest flexibility
 to optimize timing for power sequencing purposes"
```

**EN 是三支獨立輸入，沒有任何內建順序。** 時序要自己做（見 §4）。

> 這條錯誤的來源是把「有三支 EN 腳」當成「有排序功能」。
> **零件的彈性不等於零件幫你做事。**

### 2.2 腳位

```
1  GND3     2  FB3      3  FB2      4  GNDA     5  GNDB
6  SW2      7  VIN2     8  EN2      9  EN1     10  VIN1
11 SW1     12  GND1A   13  GND1B   14  FB1     15  AGNDA
16 NC      17  AGNDB   18  EN3     19  VIN3    20  SW3
21 EP（GND）
```

⚠ **EN 腳不可浮接**（datasheet 明寫 "Don't leave this pin floating"）。

### 2.3 分壓電阻（用公式算，不抄）

```
V_out = 0.6 × (1 + R_top / R_bot)      R_bot 統一用 51.0 K 1%
```

| 軌 | R_top | R_bot | 算出 V_out | 晶片容許範圍 | |
|---|---|---|---|---|---|
| **+3V3** | **232 K** | 51.0 K | 0.6×(1+4.5490) = **3.329 V** | VCC-IO 2.97 ~ 3.63 | ✓ |
| **+1V5** | **76.8 K** | 51.0 K | 0.6×(1+1.5059) = **1.504 V** | VCC-DRAM 1.425 ~ 1.575 | ✓ |
| **+0V9** | **25.5 K** | 51.0 K | 0.6×(1+0.5000) = **0.900 V** | VDD-CORE TBD（標稱 0.9） | ✓ |

三個 R_top 都是 **E96 1%** 的現成值（232K / 76.8K / 25.5K）。

#### 含容差的最壞情況

FB 本身 ±2.5%，加上電阻 1%，合計約 ±3.5%：

```
+3V3   3.21 ~ 3.45 V     VCC-IO 2.97~3.63       ✓ 兩側都有餘裕
+1V5   1.45 ~ 1.56 V     VCC-DRAM 1.425~1.575   ✓ 但只剩 ~25 mV，最緊的一條
+0V9   0.869 ~ 0.932 V   標稱 0.9（DS 未給 min/max）
```

⚠ **+1V5 是三條裡容差最緊的** —— DDR3 的 ±5% 幾乎被 FB 容差吃光。
bring-up 時這條要優先量。

```
[ ] 若量到偏離超過 2%，考慮把 R_bot 改 0.5% 或微調 R_top
```

### 2.4 電感與電容

照 datasheet 典型應用電路：

```
CH3 (+3V3)   L = 2.2 µH      C_out = 22 µF
CH2 (+1V5)   L = 1.5 µH      C_out = 22 µF
CH1 (+0V9)   L = 1.0 µH      C_out = 22 µF
每個 VIN     C_in = 10 µF MLCC，緊貼該通道的 VIN 腳
```

⚠ **DC bias**：22 µF X7R 0805 在 3.3V 偏壓下實際約 17.6 µF（掉 20%）。
1.5V / 0.9V 軌偏壓低，衰減較小。**選料時要看 DC bias 曲線，不能只看標稱值。**

```
[ ] 電感選型：飽和電流要 > 該通道峰值電流 + 漣波的一半
     +3V3 估 0.82 A → 選 ≥1.5 A 飽和
     [ ] 查 LCSC 料況
```

### 2.5 ⚠ 6 W 總功率上限的帳

```
+3V3   約 0.82 A × 3.3 V = 2.71 W    ← 最壞情況（GPIO 全速翻轉）
+1V5   估 0.30 A × 1.5 V = 0.45 W    ⚠ VCC-DRAM 電流 datasheet 是 TBD
+0V9   估 1.00 A × 0.9 V = 0.90 W    ⚠ VDD-CORE 電流 datasheet 是 TBD
                          ─────────
                          約 4.06 W   < 6 W  ✓
```

**餘裕約 32%，但兩項是估值。** 實際 GPIO 不會同時全速翻轉，真實值會低不少。

```
[ ] bring-up 時量三軌實際電流，回填本表
```

---

## 3. 兩顆 1.8V LDO

| | LDO1（SoC 側） | LDO2（ADV7511 專屬） |
|---|---|---|
| 料號 | **AP2112K-1.8TRG1** | **AP2112K-1.8TRG1** |
| LCSC | `C176944` | `C176944` |
| 封裝 | SOT-25 | SOT-25 |
| 輸入 | +3V3 | +3V3 |
| 輸出 | +1V8_SOC | +1V8_HDMI |
| 負載 | 約 52 mA + TBD | 約 180 mA |
| 壓降功耗 | (3.3−1.8)×0.10 ≈ 0.15 W | (3.3−1.8)×0.18 ≈ 0.27 W |

**兩顆用同一個料號** —— 省一個 BOM 品項，且 600 mA 對兩邊都有餘裕。

⚠ **為什麼不共用一顆**：ADI §6.8 要求 ADV7511 有自己專屬的 1.8V LDO。
理由是 Figure 24 —— AVDD/PLVDD 在 200 kHz~1 MHz 只容許 1.3 mV rms，
共用的話 SoC 側的負載跳變會打進這個頻段。詳見 001-power.md §1.2。

### 3.1 ⚠ 內建 LDOA / LDOB 不使用

```
pin 29  LDO-IN     ← +3V3        （讓內部 LDO 有輸入，供晶片內部區塊）
pin 28  LDOA-OUT   → 2.2 µF 到地，★ 不接任何電源軌
pin 30  LDOB-OUT   → 2.2 µF 到地，★ 不接任何電源軌
```

**理由：避免兩個穩壓器並聯打架。** 1.8V 全部由外部 LDO1 供。

```
[ ] 原理圖上放一顆 DNP 的 0Ω，連 LDOA-OUT 與 +1V8_SOC
     ⚠ 這是 bring-up 的實驗選項，正常情況下不焊 ——
        焊了等於兩顆穩壓器並聯，只在「想驗證 LDOA 夠不夠」時短暫使用
```

---

## 4. 上電時序電路

### 4.1 datasheet 的實際要求（文字，不是圖）

`(DS §5.12.1, p.73)`

```
• 下一步要等前一步穩定在標稱值的 90~110% 才開始
• VCC-RTC must be ramped no later than other power rails
• VCC-IO must be ramped before VDD-SYS and VDD-CORE with a minimum delay of 2 ms
• VCC-DRAM needs be stable before SDRAM driver initialization
• RESET 全程拉低，直到所有電源軌（24MHz 除外）穩定超過 64 ms
• 24 MHz 在 RESET 釋放後才開始振盪
```

⚠ **文字比 Figure 5-28 寬鬆。** 圖上 VCC-DRAM 畫在第一群組（T1 之前），
但文字只要求它「在 SDRAM driver 初始化前穩定」——**那是軟體層，不是硬體順序約束。**

**只看圖會多綁一條不存在的限制。** 圖是 example，文字才是 requirement。

### 4.2 實作

```
EN3 (+3V3) ──┬── +5V_VBUS      直接接，靠 RY1303 自己的 UVLO(2.5V) 把關
EN2 (+1V5) ──┘                  與 3.3V 同時啟動（無硬體順序要求）

EN1 (+0V9) ──[47 K]── +3V3
                 │
               [220 nF]
                 │
                GND
```

延遲驗算：

```
τ = 47 K × 220 nF = 10.34 ms
EN 上升閾值 1.2 V（min），從 3.3 V 充電：
t = −τ × ln(1 − 1.2/3.3) = −10.34 × ln(0.6364) = 4.67 ms

T1 = 4.67 ms  >  2 ms  ✓  餘裕 2.3 倍
```

⚠ EN 閾值 datasheet 只給 min 1.2 V，沒給 max。**閾值若更高，延遲只會更長**，
對 T1 只有好處。但要確認 EN 的漏電流不會讓 47K 上拉的終值掉下來。

```
[ ] 待確認：RY1303 的 EN 輸入漏電流（datasheet 未列）
     47 K 上拉時，1 µA 漏電只掉 47 mV，可接受；10 µA 就掉 0.47 V，要換小電阻
```

### 4.3 RESET —— 用 supervisor，不用 RC

```
APX803-29SAG-7    LCSC C460551 ($0.25, 庫存 835)
  閾值      2.93 V（監測 +3V3）
  延遲      200 ms typ        ★ 遠超 64 ms 要求
  輸出      open-drain，低有效
  封裝      SOT-23 三腳，無需外部元件
  消耗      30 µA typ
```

接法：

```
+3V3 ──▶ APX803 VCC
         APX803 GND ── GND
         APX803 RESET# ──┬──▶ T113 pin 27 RESET
                         │
                      [10 K]
                         │
                    +1V8_SOC        ★ 上拉到 1.8V，不是 3.3V
```

⚠ **上拉必須接 +1V8_SOC** —— T113 的 RESET 是 1.8V 域輸入
（MangoPi 原理圖 R74 10K 上拉到 LDOA-OUT = 1.8V，可佐證）。
APX803 是 open-drain，只負責拉低，高電位由上拉電阻決定，**所以電平相容沒問題**。

時序驗算：

```
t=0       VBUS 有效，EN3/EN2 拉高
t≈1 ms    +3V3 與 +1V5 到位（軟啟動 1 ms）
t≈4.7 ms  EN1 越過 1.2 V
t≈5.7 ms  +0V9 到位  ← 最後一條軌
t≈201 ms  APX803 釋放 RESET（從 +3V3 越過 2.93V 起算 200 ms）

T2 = 201 − 5.7 ≈ 195 ms  >  64 ms  ✓  餘裕 3 倍
```

### 4.4 ⚠ 為什麼不照抄 MangoPi

MangoPi 的 RESET 只有 **R74 10K 上拉 LDOA-OUT + C84 0.1 µF 到地**（原理圖 p.3 已目視確認）。

```
RC = 10 K × 0.1 µF = 1 ms
要從 0 充到 T113 的 RESET 高電位閾值，大約 1~2 ms
```

**T2 要求 64 ms，MangoPi 給了約 1 ms —— 差了 60 倍。**

001-power.md §3.4 當時的推測（「靠 soft-start 湊出來，或根本沒滿足但恰好能開機」）
現在有了確切數字佐證：**它確實沒滿足規格。**

```
→ 不照抄。多一顆 $0.25 的 supervisor，把 64 ms 變成確定的事。
```

### 4.5 ⚠ 一個沒有完美解的取捨：VCC-RTC 的順序

規格寫 **"VCC-RTC must be ramped no later than other power rails"**。

但我們的 +1V8_SOC 是從 +3V3 經 LDO 產生的，**所以 VCC-RTC 必然晚於 VCC-IO**
（差一個 LDO 的啟動時間，約數百 µs）。

考慮過的替代方案：

| 方案 | 問題 |
|---|---|
| 1.8V LDO 改吃 +5V_VBUS | (5−1.8)×0.18 = 0.58 W 在 SOT-25 裡，θJA 約 250°C/W → ΔT 145°C，**太燙** |
| 用 RY1303 第四通道 | 沒有第四通道，三路已用完 |
| 加第四顆 DC-DC | 為了數百 µs 的順序多一顆 IC，不划算 |

**採用：接受這個落差。**

依據：**MangoPi 也是這樣接的** —— 它的 VCC-RTC 來自 LDOA-OUT，
而 LDOA 的輸入 LDO-IN 是 +3V3。所以 MangoPi 的 VCC-RTC 同樣晚於 VCC-IO，**而它能開機。**

```
[ ] bring-up 時用示波器抓 +3V3 與 +1V8_SOC 的上升沿，量實際落差
[ ] 若懷疑與開機失敗有關，可暫時把 +1V8_SOC 改由外部電源先供，排除這個變因
```

**這一條記在這裡，是為了萬一開不了機時，記得它是個嫌疑犯。**

---

## 5. ADV7511 的三組 1.8V

`(ADV7511 HW User's Guide §6.8 Figure 23, p.50 / §7.1, p.52)`

```
+1V8_HDMI ──┬──[10 µH]──┬──▶ +1V8_DVDD    pin 1, 19, 49, 76, 77
            │           └─[10 µF]─ GND
            │
            ├──[10 µH]──┬──▶ +1V8_AVDD    pin 29, 34, 41（AVDD）
            │           │                  pin 24, 25（PVDD）
            │           └─[10 µF]─ GND
            │
            └──[10 µH]──┬──▶ +1V8_PLVDD   pin 21（PLVDD）
                        │                  pin 26（BGVDD）
                        └─[10 µF]─ GND

每一支電源腳再加 0.1 µF 到 GND plane，貼近腳位（相鄰腳可共用）
ADV7511 的 11 支 GND 各自用 via 下 GND plane
```

⚠ **10 µH 電感體積不小**，三顆要在 placement 階段就留位置。

⚠ RY1303 切換頻率 **1.2 MHz**，正好落在 ADV7511 AVDD/PLVDD 雜訊上限最嚴的頻段
（200 kHz~1 MHz 只容許 1.3 mV rms，1 MHz 約 1.7 mV）。
**這就是「LDO 之後還要加 LC」不能省的原因** —— LDO 對 1.2 MHz 的 PSRR 已經不高。

---

## 6. 其他電源相關的必要元件

### 6.1 T113-S3

```
DZQ (pin 47)      240 Ω 1% 接地     ★ DDR ZQ 校準，MangoPi R42 已佐證
LDOA-OUT (28)     2.2 µF 到地
LDO-IN (29)       2.2 µF 到地，接 +3V3
LDOB-OUT (30)     2.2 µF 到地
VCC-RTC (26)      ← +1V8_SOC（MangoPi 用 0Ω 從 LDOA-OUT 接，我們直接接）
RESET (27)        ← APX803 + 10K 上拉到 +1V8_SOC
EPAD (129)        ★ 唯一的數位地，thermal via 陣列 + plugged
```

### 6.2 ADV7511

```
R_EXT (pin 28)    887 Ω ±1% 接地    ★ 走線短，LRCLK 與 via 不可靠近
MVDD (pin 47)     ← +3V3
```

### 6.3 USB-A Host 限流

```
TPS2051BDBVR   LCSC C24593 ($0.21, 庫存 38,715)
  +5V_VBUS ──▶ IN    OUT ──▶ +5V_USB
               EN ← GPIO（或直接使能）
               OC# → GPIO（過流回報）
```

**過流時只斷 Host，不影響主板** —— 這是 001-power.md §5.2 就定下的策略。

---

## 7. 去耦總表

| 位置 | 電容 |
|---|---|
| RY1303 每個 VIN | 10 µF MLCC，緊貼腳位 |
| RY1303 每個輸出 | 22 µF（⚠ 看 DC bias） |
| 兩顆 LDO 輸入/輸出 | 1 µF / 1 µF（依 AP2112K datasheet 確認） |
| T113 每支電源腳 | 0.1 µF 0402，緊貼 |
| T113 每組電源軌 | 10 µF 0805，靠近進入點 |
| ADV7511 每支電源腳 | 0.1 µF，相鄰可共用 |
| ADV7511 三組 1.8V | 各 10 µH + 10 µF |
| 整板輸入端 | 100 µF 電解或鉭質 |
| PLL / 類比軌 | 磁珠或串聯電阻隔離 + 0.1 µF + 10 µF |

```
[ ] AP2112K 的輸入/輸出電容要求回 datasheet 確認（目前是慣例值）
```

---

## 8. 待辦

```
[x] RY1303 規格與腳位 —— datasheet 已取得
[x] 分壓電阻值 —— 232K / 76.8K / 25.5K，R_bot 統一 51K，全為 E96 1%
[x] 上電時序電路 —— EN1 用 47K + 220nF（T1 = 4.67 ms）
[x] RESET —— APX803-29SAG-7，200 ms 延遲，上拉到 +1V8_SOC
[x] VDD18-DRAM 的來源 —— MangoPi 接 LDOA-OUT；本板接 +1V8_SOC
[x] DZQ 240 Ω 1%
[ ] RY1303 的 EN 輸入漏電流（datasheet 未列）→ 決定 47K 是否夠小
[ ] 三顆電感選型 + LCSC 料況（飽和電流）
[ ] AP2112K 的輸入/輸出電容要求
[ ] VCC-DRAM / VDD-CORE 實際電流 → 回填 §2.5 的 6W 帳
[ ] Table 5-2 / 5-3 的數字回 p.45-48 原頁目視核對
```
