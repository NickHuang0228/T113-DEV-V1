# 001 · 電源樹與上電時序

版本：v0.2 · 2026-09-18（依 datasheet 重寫，取代 v0.1 的估算值）

**資料來源**：`T113-S3_Datasheet_v1.6_20220303.pdf`，以下標註格式為 `(DS §5.3 p.45)`。
交叉驗證對象：`MangoPi_MQ-R_sch_v1.6.pdf`（分壓值已驗算，見 §2.4）。

---

## 1. 電源軌清單

`(DS §5.3 Recommended Operating Conditions, p.45-46)`

| 電壓 (Typ) | 電源軌 | 用途 |
|---|---|---|
| **0.9 V** | VDD-CORE0/1 | CPU 與系統 |
| | VDD-SYS0/1/2 | 系統 |
| **1.5 V** | VCC-DRAM0/1 | DRAM IO 與 DDR3 本體（Max 1.575） |
| **1.8 V** | VCC-RTC | RTC |
| | VCC-PLL | System PLL |
| | VCC-LVDS | LVDS |
| | VCC-TVIN | CVBS 輸入 |
| | VDD18-DRAM | DRAM Controller（Max 1.95） |
| | AVCC / HPVCC | 音訊類比 / 耳機 |
| **3.3 V** | VCC-IO | 數位 IO |
| | VCC-TVOUT | CVBS 輸出 |
| | LDO-IN | 內部 LDOA/B 的輸入（Max 3.6） |
| **1.8 或 3.3 V** | VCC-PD / VCC-PE / VCC-PG | GPIO bank，**可選**（VCC-PE 另支援 2.8V） |
| **5 V** | — | USB-A Host 直通（含限流） |

> ⚠ v0.1 寫的 `VDD_CPU / VDD_SYS = 1.1V` 是錯的，datasheet Typ 是 **0.9 V**。
> 照 1.1V 設計等於超壓 22%。Table 5-2 的 Max 欄位全是 `TBD`，所以 1.1V 沒有任何依據。
>
> ⚠ v0.1 完全漏掉 **1.5V 的 VCC-DRAM**。「內建 DDR3」不等於「不用供電給 DDR3」——
> SIP 把 die 封進去了，電源軌還是要從外面進。

### 1.1 GPIO bank 電壓是設計決策

VCC-PD / VCC-PE / VCC-PG 可選 1.8V 或 3.3V，**這決定該 bank 上所有訊號的電平**：

```
VCC-PD   PD0~PD9  = MIPI DSI / RGB 共用  →  ★ MIPI 優先，電平以 MIPI 為準
         PD10~PD21 = RGB666 其餘         →  必須與 IT66121 的輸入電平相容
VCC-PE   PE bank  = RMII / CSI     →  必須與 RTL8201F 的 IO 電平相容
VCC-PG   PG bank  = SDIO / 其他
```

MangoPi 原理圖在 PE bank 旁註記了各家 PHY 的電平需求：

```
LAN8720   1.8 ~ 3.3 V
IP101GR   2.5 / 3.3 V
```

**決策歸屬 002-display.md 與 003-network.md，但必須在畫原理圖前定案。**

---

## 2. 供電架構

### 2.1 晶片內建兩顆 LDO —— 1.8V 可以不用外部電源

`(DS §5.3 p.46；MangoPi sch pin 28/29/30)`

```
pin 29  LDO-IN     ←  3.3 V
pin 28  LDOA-OUT   →  1.8 V  @ 0.26 A          供類比裝置與 IO
pin 30  LDOB-OUT   →  1.35 V（預設）/ 1.5 V 可設  @ 0.4 A   供 VCC-DRAM
```

MangoPi 的實際做法：

```
LDOA-OUT  →  VCC-PLL (pin 20)、pin 65、32.768K 振盪電路
          →  再經 LC 濾波 →  AVCC1.8（音訊類比）
LDOB-OUT  →  只掛 2.2 µF 電容，未用於 VCC-DRAM
VCC-DRAM  →  由外部 DC-DC 供 1.5 V
```

MangoPi 的 1.8V 群**同時用了內建 LDOA 與外部 XC6206 LDO**（見 §2.2.1），不是只靠內建。

VCC-DRAM 選外部而非內部 LDOB 的理由：datasheet §5.3 的工作溫度欄位顯示，
內部 LDO 供電時 3.3V→1.35V 的壓降全在晶片裡發熱，溫度範圍會被壓縮。
**照抄 MangoPi：外部 1.5V。**

### 2.2 ⚠ 但 LDOA 只有 260 mA —— 這筆帳必須先算

已知的 1.8V 負載 `(DS Table 5-3, p.47-48)`：

```
VCC-PLL (24MHz 振盪)      2 mA      Max
VCC-RTC                   0.01 mA   Max
VCC-LVDS (700MHz 雙鏈路)   50 mA     Max
VCC-TVIN                  TBD
AVCC / HPVCC (音訊)        TBD
VDD18-DRAM                TBD       ← 關鍵未知數，DRAM controller 的電源不會小
```

已知合計約 **52 mA**，但三項 TBD。

```
[ ] 待確認：MangoPi 原理圖 pin 50 (VDD18-DRAM) 實際接 LDOA-OUT 還是外部 1.8V？
[ ] 待確認：MIPI DSI D-PHY 的電源軌是哪一支、4-lane 工作時多少電流？
```

### 2.2.1 已查證：MangoPi 本身就有外部 LDO，不是只靠內建 LDOA

原理圖上找得到 **XC6206 系列 LDO 至少三顆**（以標註字串出現）：

```
XC6206-1.8V    1.8 V
XC6206-2.8     2.8 V   （給 OV2640 / OV5640 攝影機的 AVDD2V8）
XC6206-1.2     1.2 V
```

**所以「板上只有 RY1303 三路，1.8V 只可能來自 LDOA」的排除法不成立** ——
MangoPi 另外放了外部 1.8V LDO。

**結論：本專案也保留一組外部 1.8V。**

```
理由   LDOA 只有 260 mA，而 VDD18-DRAM、AVCC、VCC-TVIN 三項在 datasheet 裡是 TBD
       XC6206 或同級 SOT-23 LDO 約 $0.05，多一顆換掉一個未知數
       算不出來的東西不要賭
```

```
[ ] 仍待目視確認：MangoPi 的 pin 50 (VDD18-DRAM) 究竟接 LDOA-OUT 還是 XC6206-1.8V
     （抽取文字的網路對應會飄，必須開 PDF 原頁）
```

### 2.2.2 MIPI D-PHY 的電源軌

MIPI DSI 走 PD0~PD9，該 bank 的 **IO buffer 電源是 VCC-PD** `(DS Table 4-2 Power Supply 欄)`。

D-PHY 的類比電源推測是 **VCC-LVDS（1.8V，Max 50 mA）** —— 因為 LVDS0 與 DSI
共用同一組腳、同一個 PHY 區塊，且 Table 5-3 只有 VCC-LVDS 這一項與該 PHY 相關。

```
[ ] 待確認：開 p.77 Pin Map 目視，確認 VCC-LVDS 的腳位位置與 PD bank 的關係
```

### 2.3 電源 IC：三種選擇

v0.1 的立場是「分離式，不用 PMIC」。查完 MangoPi 後發現中間還有一格：

| | 分離式 ×3 | **三路 DC-DC（如 RY1303）** | PMIC（AXP 系列） |
|---|---|---|---|
| 可觀測性 | 每軌獨立量測 | **三組電感與 feedback 都在外面，照樣量得到** | 黑盒子 |
| 上電時序 | EN 腳自己串 | **EN1/EN2/EN3 內建順序** | 內部狀態機，改不了 |
| 板面積 | 大 | 中 | 小 |
| 故障處理 | 換單顆 | 換整顆（三路一起沒） | 換整顆 |
| 料況 | 通用料 | ⚠ **中國小廠料，須查 LCSC** | 專用料 |

**排除 PMIC 的理由依然成立**（內部時序看不見），但**三路 DC-DC 沒有那個問題**——
三個電感、三組分壓電阻都露在板子上，探棒照樣量。

```
[ ] 待決策：查 LCSC 的 RY1303 料況（Basic/Extended、庫存、價格）
             買得到 → 三路，省面積省 BOM
             買不到 → 退回分離式 ×3
```

### 2.4 MangoPi 的分壓值驗算（示範方法）

RY1303 的 feedback 參考電壓 `VF = 0.6V`（原理圖上有註記）：

```
V_out = 0.6 × (1 + R_top / R_bot)

3.3V   680K / 150K = 4.53  →  0.6 × 5.53 = 3.32 V   ✓
1.5V   226K / 150K = 1.51  →  0.6 × 2.51 = 1.51 V   ✓
0.9V    75K / 150K = 0.50  →  0.6 × 1.50 = 0.90 V   ✓
```

三組全部對得上 → 這份參考原理圖可信。

**這就是驗收清單裡「分壓值用公式驗算，不靠標籤」的實際做法。**
換成自己的電源 IC 時，VF 值要改成該顆的規格。

---

## 3. 上電與關機時序

### 3.1 上電要求（只有兩個時間常數）

`(DS §5.12.1 Power-On Sequence, p.73, Figure 5-28)`

```
① 每一步要等前一步穩定在標稱值的 90~110% 才開始
② VCC-RTC 不得晚於其他電源軌
③ VCC-IO 必須早於 VDD-SYS 與 VDD-CORE，最小延遲  T1 > 2 ms
④ VCC-DRAM 必須在 SDRAM driver 初始化前穩定
⑤ RESET 全程拉低，直到所有電源軌（24MHz CLK 除外）穩定超過  T2 > 64 ms
⑥ 24 MHz 在 RESET 釋放後才開始振盪
```

MangoPi 原理圖上直接寫了一行註記：`PWR-ON Sequence wait 2ms` —— 對應 ③。

### 3.2 關機要求：沒有

`(DS §5.12.2, p.74)`

```
RESET 拉低後，24 MHz 停止振盪。
"No special restrictions for other power rails."
```

**關機完全不用設計。** 掉電順序隨意。

### 3.3 實作方式

只有兩個時間常數 → **不需要 sequencer IC**。

```
T1 > 2 ms    EN 鏈：3.3V 穩定後的 PG（或輸出經 RC 延遲）驅動 0.9V 的 EN
             三路 DC-DC 的話 EN1/EN2/EN3 本來就有順序，確認內建延遲 ≥ 2ms 即可

T2 > 64 ms   RESET 延遲
```

### 3.4 ⚠ RESET 的 64 ms 不要照抄 MangoPi

MangoPi 原理圖上**找不到 reset supervisor IC**（沒有 MAX809 / APX803 之類），
RESET 只看到 R74 10K 上拉到 LDOA-OUT。

```
10K 上拉要做到 64 ms，需要約 6.4 µF 的電容 —— 這不是常見的 RESET RC 值
```

**推測 MangoPi 是靠 RY1303 的 soft-start 時間湊出來的，或根本沒滿足但恰好能開機。**

```
[ ] 待確認：開 MangoPi 原理圖原頁，看 RESET 腳實際有無電容、多大
[ ] 決策傾向：放一顆 reset supervisor（~$0.1），把 64ms 做成確定的事
              第一塊板不在「恰好能開機」上冒險
```

### 3.5 驗證方式

**bring-up 第一天用四通道示波器同時抓 3.3V / 1.5V / 0.9V / RESET**：

```
3.3V 到 0.9V 的間隔       > 2 ms
最後一軌穩定到 RESET 釋放  > 64 ms
```

---

## 4. 去耦電容

```
每一支電源腳     0.1 µF  X7R  0402，緊貼腳位
每一組電源軌     10 µF   X7R  0805，靠近進入點
整板輸入端       100 µF  電解或鉭質
PLL / 類比軌     磁珠或串聯電阻隔離 + 0.1 µF + 10 µF
LDOA-OUT        2.2 µF（MangoPi C44）
LDOB-OUT        2.2 µF（即使不使用也要掛，MangoPi C50）
```

MangoPi 在 AVCC1.8 上用了 **75R 串聯電阻 + LC** 做類比隔離，值得抄。

**注意 DC bias**：上一塊板學到的教訓 —— MLCC 在偏壓下容值會掉。

```
22 µF X7R 0805 @3.3V → 實際約 17.6 µF（掉 20%）
```

**1.5V 與 0.9V 軌的偏壓低，容值衰減比 3.3V 軌小**，但仍要查 DC bias 曲線。

---

## 5. 功耗估算

### 5.1 datasheet 實際數字

`(DS Table 5-3 Power Consumption Parameters, p.47-48)`

```
通則：Imax = N × 6 mA      N = 該 bank 使用中的 GPIO 數量

VCC-IO    N=19   Max 114 mA     (3.3V)
VCC-PD    N=23   Max 138 mA     (3.3V)   ← RGB666 的 22 條就在這個 bank
VCC-PE    N=14   Max  84 mA     (3.3V)
VCC-PG    N=16   Max  96 mA     (3.3V)
                 ───────────────────
3.3V GPIO 合計   Max 432 mA

VCC-LVDS         Max  50 mA     (1.8V, 700MHz 雙鏈路)
VCC-PLL          Max   2 mA     (1.8V, 24MHz 振盪)
VCC-RTC          Max 0.01 mA    (1.8V)
USB (VCC-IO)     Max  35 mA     (3.3V, 2 埠)

VDD-CORE / VDD-SYS / VCC-DRAM / VCC-TVIN / AVCC   全部 TBD
```

> ⚠ 核心電流（VDD-CORE、VDD-SYS）與 DRAM 電流在 datasheet 裡是 **TBD** —— 全志沒填。
> 這是這份 datasheet 最大的缺口。**0.9V 軌的電流只能靠估算，或從參考設計的電感與
> 電源 IC 規格反推。**

### 5.2 整板估算

```
T113-S3 全速（2×A7 @1.2GHz）  ~1.5 W  → 5V 端約 350 mA（效率 85%）  ⚠ 估算，datasheet TBD
3.3V GPIO（最壞情況全切換）     432 mA @3.3V = 1.43 W → 5V 端約 340 mA
IT66121（HDMI 工作中）         ~0.5 W  → 5V 端約 120 mA
RTL8201F（100M link up）       ~0.3 W  → 5V 端約  70 mA
SD / SPI NOR / 被動            ~0.2 W  → 約 50 mA
USB-A Host 對外                5V × 500 mA = 2.5 W
```

**3.3V 那組從 v0.1 的 400 mA 上修到 432 mA（datasheet 最壞值）。**
實際上 24 條 RGB 不會同時全速翻轉，真實值會低不少，但**電源照最壞情況設計**。

Type-C 5V/3A = 15W，仍有餘裕。

⚠ 只用 5.1k CC 電阻時，實際可取電流取決於電源端：

```
標準 Type-C 充電器      可到 3A
USB-A 轉 C 線接電腦     可能只有 500 mA  ← 推 USB Host 時會不夠
```

**緩解**：USB-A Host 的 5V 加限流開關（如 TPS2051），過流時只斷 Host 不影響主板。

---

## 6. 熱

### 6.1 datasheet 實際數字

`(DS Table 6-1 Package Thermal Characteristics, p.76；Tj max 見 Table 5-2, p.45)`

```
θJA  Junction-to-Ambient   20.36 °C/W      ← 比 v0.1 估的 30~50 好很多
θJB  Junction-to-Board      7.43 °C/W
θJC  Junction-to-Case       5.52 °C/W

Tj max = 110 °C
公式    Tj max = Ta max + (PD max × θJA)
```

### 6.2 驗算

```
PD = 1.5 W，Ta = 25 °C
Tj = 25 + 1.5 × 20.36 = 55.5 °C       餘裕 54.5 °C   ✓ 非常寬鬆

PD = 1.5 W，Ta = 45 °C（機殼內）
Tj = 45 + 30.5 = 75.5 °C              餘裕 34.5 °C   ✓
```

**熱不是這塊板的風險，不需要散熱片。**

（datasheet §5.3 提到「VCC-DRAM 外部供電 + SoC 加散熱片」時工作溫度範圍才是 -25~85°C，
不加散熱片是 25~75°C。桌面使用不受影響。）

### 6.3 ⚠ 但 θJB = 7.43 °C/W 有前提

Junction-to-Board 只有 7.43 —— 代表**熱主要透過 EPAD 往板子走**。
這個數字只有在 **EPAD 確實焊到一片良好的散熱銅箔**時才成立。

```
EPAD 沒焊好 → θJA 遠大於 20.36 → §6.2 的驗算全部失效
```

見 §7。

### 6.4 熱阻模型（layout 用）

```
R = L / (k × A)      銅 k=385 W/(m·K)，FR4 k=0.30
走線與 via 是串聯，再與「垂直穿 prepreg 到 GND 平面」並聯
```

**驗證**：bring-up 時用熱像儀或熱電偶量，跑 `stress-ng` 15 分鐘達熱平衡後讀值。
上一塊板的教訓是：WiFi 測試只跑 40 秒，沒達熱平衡，數據不能用。

---

## 7. EPAD（pin 129）—— 這顆晶片唯一的數位地

`(DS §4.1 Pin Quantity, p.23；MangoPi sch 標示 EPAD 129)`

```
Pin Type      Quantity
I/O           102
NC              1
Power          21
Ground          1      ← ball 25 = AGND，類比地
DDR Power       3
Total         128
```

**128 隻腳裡沒有任何一支數位 GND。** 21 支電源的回流電流全部走 EPAD。

```
EPAD 不焊     沒有數位地 → 不開機。量各軌電壓全對，查不出來
EPAD 焊一半   地阻抗偏高 → 開得起來但間歇當機、DDR 出錯（DDR 在封裝內，最難查）
EPAD 錫太多   晶片被墊高 → 128 隻腳同時虛焊，但目視看起來完全正常
```

三種失敗全部**無法目視檢查**，只有 X-ray 看得到。

### 7.1 footprint ⚠ datasheet 有紅字警告

`(DS §7.2 Package Dimension, p.78)`

```
CAUTION
Make sure to use the second set of exposed pad size (D3/E3: 5.72 mm REF)
to design the PCB footprint because the T113-S3 package is designed
according to this size.
```

**機構圖裡有六組 exposed pad 尺寸，原廠明講要用第二組 → 5.72 × 5.72 mm 正方形。**

⚠ 第 ⑥ 組也是 `5.72 / 5.46`（長方形），只看到「5.72」很容易選錯。
完整機構圖數字與判讀見 [008-footprint.md](008-footprint.md)。

封裝：**eLQFP128，本體 14 × 14 × 1.4 mm，含腳 16 × 16 mm** `(DS §2.12 p.19 / §7.2 p.78)`

### 7.2 thermal via：兩種做法互斥，layout 階段就要選

```
A. 鋼網 + 錫膏 + 回流
   EPAD 開口做成網格狀（不是一整塊），錫膏覆蓋率 50~70%
   thermal via 必須 plugged，否則錫從 via 漏到背面
   → 防止晶片浮起的業界標準做法

B. 背面 via 補焊
   從板子背面用烙鐵把錫灌進 thermal via，直接焊到 EPAD
   → via 不能塞死
```

**A 與 B 不能並存。** 本專案採用 **A**（EPAD 交給 JLCPCB 貼裝，見 006-assembly.md）。

---

## 8. 待確認清單

進原理圖前必須答完：

```
[ ] VDD18-DRAM (pin 50) 接 LDOA-OUT 還是外部 1.8V？（開 MangoPi 原理圖原頁）
[ ] MIPI DSI D-PHY 的電源軌與 4-lane 電流
[ ] 上兩項合計是否超過 LDOA 的 260 mA → 決定要不要外部 1.8V
[ ] RY1303 的 LCSC 料況 → 決定三路 DC-DC 或分離式 ×3
[ ] MangoPi 的 RESET 腳實際有無電容、多大 → 決定要不要加 reset supervisor
[ ] VCC-PD / VCC-PE / VCC-PG 各選 1.8V 還是 3.3V（與 IT66121、RTL8201F 電平對齊）
[ ] Table 5-2 / 5-3 的數字回 p.45-48 原頁目視核對（pdftotext 欄位有錯位）
```

---

## 9. 量測清單（bring-up 第一天）

```
[ ] 上電前先量各軌對地電阻，確認沒有短路
[ ] 3.3V / 1.5V / 0.9V 三軌電壓，誤差 <±3%
[ ] 若用內部 LDOA，量 LDOA-OUT (pin 28) 是否為 1.8V
[ ] 四通道示波器抓上電時序：3.3V → 0.9V 間隔 > 2 ms，末軌 → RESET 釋放 > 64 ms
[ ] 各軌漣波（AC 耦合，20MHz 頻寬限制），目標 <50 mV pp
[ ] 總電流（待機 / 全速 / 插 USB 裝置）
[ ] 15 分鐘後 SoC 表面溫度，對照 §6.2 驗算值
```

---

## 附錄 · 方法論筆記

**pdftotext 對 T113 datasheet 的文字層有效，但表格欄位會錯位。**

```
Table 4-2 (Pin Characteristics)   ball# 與 pin name 對不上  → 不可用
Table 5-2 (Operating Conditions)  min/typ/max 欄位跑位      → 數字可用但要核對
原理圖 PDF                         網路標籤與腳位對應會飄    → 只能當線索
```

**規則：抽出來的文字用來「定位」，不用來「定案」。**
任何進入原理圖或 layout 的數字，一律回原頁目視確認。
這是繼 H3 那次 zlib 抽取失敗之後的第二條同類教訓。
