# 001 · 電源樹與上電時序

版本：v0.8 · 2026-09-21（RY1303 datasheet 取得:**EN 沒有內建順序**,那是我寫錯的;數值定案移到 011)

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
| **1.8 V** | **ADV7511** DVdd / AVdd / PVdd / PLVdd / BGVdd | **HDMI 橋接晶片**，約 180 mA（見 §1.2） |
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
         PD10~PD21 = RGB666 其餘         →  必須與 ADV7511 的輸入電平相容
VCC-PE   PE bank  = RMII / CSI     →  必須與 RTL8201F 的 IO 電平相容
VCC-PG   PG bank  = SDIO / 其他
```

MangoPi 原理圖在 PE bank 旁註記了各家 PHY 的電平需求：

```
LAN8720   1.8 ~ 3.3 V
IP101GR   2.5 / 3.3 V
```

#### ✅ v0.3 定案

| Bank | 電壓 | 依據 |
|---|---|---|
| **VCC-PE** | **3.3 V** | RTL8201F 的數位 IO 只吃 `DVDD33 = 3.3V±10%`，**沒有獨立 VDDIO 腳**，1.8V 會過不了 VIH `(RTL8201F DS §9.1.2 Table 47, p.44)` |
| **VCC-PD** | **3.3 V** | ADV7511 的視訊輸入腳支援 1.8V~3.3V CMOS，對電壓無要求；MIPI D-PHY 的類比電源是 VCC-LVDS 而非 VCC-PD（見 §2.2.2），所以 MIPI 側也不綁。選 3.3V 取最大雜訊餘裕，並與排針借用的 PD10~PD13 電平一致 |
| **VCC-PG** | **3.3 V** | 已於 007-pinmap.md v0.2 定案 |

```
[ ] 殘留風險：VCC-PD = 3.3V 時 MIPI 模式是否仍正常
     推論依據是「D-PHY 吃 VCC-LVDS」，datasheet 沒有明文
     → 找一份真的有接 DSI 面板的 T113/D1 參考設計核對 VCC-PD 接法
```

### 1.2 ⚠ 橋接晶片換成 ADV7511 之後：1.2V 取消，1.8V 變成瓶頸

v0.3 查出 IT66121 需要 1.2V，把電源域從 4 組改成 5 組。
**v0.4 因為 IT66121 停產改用 ADV7511，那條 1.2V 軌又消失了** —— 但換來新的問題。

`(ADV7511 Hardware User's Guide Rev.D §4 Table 1, p.12-13 —— 表頭標示 ADV7511KSTZ)`

```
1.8V   DVdd    HDMI 數位核心          雜訊上限  64 mV RMS
       AVdd    HDMI 類比              見 §7.1（更嚴）
       PVdd    HDMI PLL – 數位        雜訊上限  64 mV RMS
       PLVdd   HDMI PLL – 類比        見 §7.1（更嚴）
       BGVdd   band-gap               雜訊上限  64 mV RMS
       範圍 1.71 / 1.80 / 1.90 V

3.3V   MVdd    範圍 3.15 / 3.30 / 3.45 V

功耗   326 mW 總計（1.8V = 325 mW → 約 180 mA，3.3V = 1 mW）
       條件 1080p / 36-bit；本板 RGB666 會更低，但照最壞情況設計
待機   Power-Down L1 20 mA · L2 300 µA
```

⚠ **是五個 1.8V 域不是四個。** v0.4 寫四個是抄 **ADV7511W**（64 腳版）的，
KSTZ 多一個 **PLVdd**，而且 3.3V 那條叫 **MVdd** 不是 `DVDD_3V`。
**同系列不同尾碼就是不同晶片 —— 這是本專案第五次踩同型的坑。**

#### 1.8V 的帳重算

```
原有已知負載（VCC-PLL 2 + VCC-RTC 0.01 + VCC-LVDS 50）   約  52 mA
ADV7511                                                 約 180 mA
                                                        ──────────
                                                        約 232 mA
晶片內建 LDOA 上限                                          260 mA
```

**只剩 28 mA 餘裕，而 VDD18-DRAM / AVCC / VCC-TVIN 在 datasheet 裡還是 TBD。**

```
→ 外部 1.8V LDO 從「保險」變成「必須」
→ 而且不能用 XC6206（典型僅 200 mA）
→ 改用 AP2112K-1.8TRG1（C176944，600 mA，$0.17，庫存 47,449）
```

⚠ 這是一個**反轉**：v0.3 的 §2.2.1 說「多一顆 $0.05 的 XC6206 換掉一個未知數」，
現在那顆 XC6206 **容量不夠**，要換成貴 8 倍但足量的 AP2112K。
**負載變了，元件選擇就要跟著重算 —— 不能因為上一版已經選好就沿用。**

#### ⚠⚠ ADI 要求 ADV7511 用**自己專屬**的 1.8V LDO

`(HW User's Guide §6.8 Power Domains, p.50)`

```
"It is recommended that the ADV7511 has its own designated 1.8V linear regulator
 and that the AVDD, DVDD and PLVDD PCB power domains be segregated using inductors."
```

**不是與 SoC 共用 1.8V。** 所以 1.8V 要拆成兩顆 LDO：

```
3.3V ──┬──[LDO #1]──▶ 1.8V-SOC   VCC-PLL / VCC-RTC / VCC-LVDS / AVCC / VDD18-DRAM
       │                          約 52 mA + 幾項 TBD
       │
       └──[LDO #2]──▶ 1.8V-HDMI  ADV7511 專屬，約 180 mA
                                  再分成 3 組，各加 10µH + 10µF（見下）
```

**這反而讓選料變簡單了** —— v0.4 為了「一顆 LDO 撐 232 mA」選了 600 mA 的 AP2112K，
現在兩顆各自負載小很多：

| | 負載 | 選料 |
|---|---|---|
| **LDO #1（SoC 1.8V）** | ~52 mA + TBD | 內建 LDOA（260 mA）夠用，或外掛 XC6206 當備援 |
| **LDO #2（ADV7511 專屬）** | ~180 mA | **AP2112K-1.8TRG1**（`C176944`，600 mA，$0.17） |

⚠ 但 §6.8 只說「recommended」。**若為了省一顆 LDO 而共用，風險是 SoC 側的
負載跳變（例如 DDR 或 GPIO 大量翻轉）會耦合到 ADV7511 的 PLL 電源** ——
而 Figure 24 顯示 PLL 電源在 200kHz~1MHz 只容許 1.3 mV rms。
**第一塊板不省這 $0.17。**

```
[ ] 電源樹圖要改成兩條 1.8V，SPEC §5 一併更新
```

#### 1.8V 要分成 3 組，各加 LC —— ADI 有明確規格

`(HW User's Guide §7.1, p.52)`

```
"It is recommended to combine the five 1.8 volt power domains of the ADV7511
 into 3 separate PCB power domains ... An LC filter on the output of the power
 supply is recommended ... An effective LC filter for this is a 10 μH inductor
 and a 10 μF capacitor ... This filter scheme will reduce any noise component
 over 20KHz to effectively 0."
```

```
每組 1.8V 域：10 µH 電感 + 10 µF 電容，盡量靠近 ADV7511
每一支電源腳：0.1 µF 到 GND plane，貼近腳位（相鄰電源腳可共用）
GND 腳：各自用 via 接到 GND plane
```

電源腳位 `(Table 3, p.19-20)`：

```
AVDD    1.8V   pin 29, 34, 41          TMDS 輸出類比
DVDD    1.8V   pin 1, 19, 49, 76, 77   數位與 IO（"filtered and as quiet as possible"）
PVDD    1.8V   pin 24, 25              PLL 數位（"quiet, noise-free"）
PLVDD   1.8V   pin 21                  PLL 類比 VCO —— "the most sensitive portion"
BGVDD   1.8V   pin 26                  Band Gap
MVDD    3.3V   pin 47
GND            pin 18,20,22,23,27,31,37,44,75,99,100   ← 11 支，確認無 EPAD
```

#### ✅ Figure 23 (p.50) 的實際分法 —— 不是一個名字一組

```
1.8V-HDMI LDO ──┬──[10 µH]──┬── DVDD    pin 1, 19, 49, 76, 77
                │           └─[10 µF]─GND
                │
                ├──[10 µH]──┬── AVDD    pin 29, 34, 41
                │           │   PVDD    pin 24, 25        ← AVDD 與 PVDD 併一組
                │           └─[10 µF]─GND
                │
                └──[10 µH]──┬── PLVDD   pin 21
                            │   BGVDD   pin 26            ← PLVDD 與 BGVDD 併一組
                            └─[10 µF]─GND

所有 bypass 0.1 µF（每支電源腳一顆，相鄰腳可共用）
GND 腳（11 支）各自用 via 下 GND plane
```

#### ⚠⚠ Figure 24 (p.52)：最嚴的雜訊上限落在 DC-DC 的切換頻段

AVDD / PLVDD 的 Max rms noise vs frequency，目視讀值：

```
1 ~ 20 kHz      約 28.5 mV     平坦
~25-30 kHz      約 29 mV       小峰
100 kHz         約 9.5 mV
200 k ~ 300 kHz 約 1.3 mV      ★ 最嚴
300 k ~ 1 MHz   約 1.5 ~ 1.7 mV
1 M ~ 5 MHz     約 1.8 ~ 3 mV
10 MHz          約 5.5 mV
```

**1.3 mV rms @ 200kHz~1MHz —— 正好是 RY1303 這類 DC-DC 的切換基頻與低階諧波。**

```
→ 這就是「LDO 不是 DC-DC」+「再加 LC」的理由,兩層都不能省
→ 也是 §6.8 要求專屬 LDO 的理由:共用的話 SoC 側的負載跳變會打進這個頻段
```

#### ✅ §6.8.1 (p.50)：ADV7511 沒有上電時序要求

```
"There is no required sequence for turning on or turning off the power domains;
 all should be fully powered up or down within 1 second of the others."
```

**與 T113-S3 的 T1>2ms / T2>64ms 不同 —— ADV7511 這邊不用排序**，
1.8V-HDMI 可以直接掛在 3.3V 穩定之後，不必進 §3 的時序鏈。

**三組 LC（3 顆 10µH + 3 顆 10µF）加上約 11 顆 0.1µF，要在 placement 階段就留位置。**
10µH 的電感體積不小，不是 0402 能放的。

#### 視訊輸入腳的電平：3.3V 直接可用

`(同上 Table 1, p.12 —— Data Inputs: Video, Audio and CEC_CLK)`

```
VIH   Min 1.35   Max 3.5   V
VIL   Min -0.3   Max 0.7   V
      Input Capacitance    Typ 1.0 / Max 1.5 pF
```

**VIH 上限 3.5V → 3.3V CMOS 直接驅動。§1.1 的 VCC-PD = 3.3V 不必推翻，
22 條 RGB 線不需要電平轉換。**

✅ 輸入電容 1.5 pF max（IT66121 約 5 pF）—— 掛在 MIPI 分支上的負載只有 1/3。

```
[ ] 原始 PDF 仍未存檔（ADI 封鎖自動下載）。數字來自 pdf.js 文字層抽取，
     整理於 ../reference/peripherals/ADV7511KSTZ_extracted.md
```

### 1.3 RTL8201F 不需要額外電源軌

`(RTL8201F DS §8.8 p.38)`

```
核心 1.1V 由晶片內建 LDO 從 3.3V 產生
"The external 1.05V power supply is not suggested ... the internal regulators cannot be disabled"
→ DVDD10 / DVDD10OUT / AVDD10OUT 只掛 0.1µF X5R 低 ESR 電容，不外接電源
```

**RTL8201F 全板只吃 3.3V。** 與 ADV7511 相反（後者要 1.8V + 3.3V）——
同樣是周邊 IC，一顆自帶 LDO，一顆沒有。**每顆都要開 Power/Ground Pins 那頁逐腳看。**

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
XC6206-1.2     1.2 V   （本專案用不到——ADV7511 不需要 1.2V）
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

D-PHY 的類比電源推測是 **VCC-LVDS（1.8V，Max 50 mA）**。v0.3 補上兩項佐證：

**① 整顆晶片的電源腳裡沒有任何 DSI 專用軌** `(DS Table 4-2, p.34-37)`

```
AVCC · VCC-DRAM0/1 · VCC-IO · VCC-LVDS · VCC-PD · VCC-PE · VCC-PG · VCC-RTC · VDD18-DRAM
（另有 VDD-CORE / VDD-SYS / VCC-PLL / VCC-TVOUT / VCC-TVIN）
```

沒有 `VCC-DSI` / `VDD-MIPI`。DSI 與 LVDS 共用 PD0~PD9 的實體 pad，
**VCC-LVDS 是唯一可能的類比供電來源。**

**② VCC-LVDS 是獨立的腳位（pin 65），不是 VCC-PD 的一部分**

```
DS Table 4-2         PD22 之後緊接 pin 65 = VCC-LVDS
MangoPi sch v1.6     pin 64 = PD9 ／ pin 65 標示 "LVDS1.8" ／ pin 66 = VCC-PD
```

**推論：MIPI D-PHY 吃 VCC-LVDS (1.8V)，VCC-PD 只供 RGB 模式的數位 IO buffer。**
所以 VCC-PD 可以選 3.3V 而不影響 MIPI —— 這是 §1.1 定案的依據。

```
[ ] 仍待確認：此推論 datasheet 無明文，找一份真接 DSI 面板的 T113/D1 參考設計核對
[ ] 待確認：4-lane 全速時 VCC-LVDS 實際電流（Table 5-3 只給「700MHz 雙鏈路 LVDS」的 50 mA）
```

### 2.3 電源 IC：三種選擇

v0.1 的立場是「分離式，不用 PMIC」。查完 MangoPi 後發現中間還有一格：

| | 分離式 ×3 | **三路 DC-DC（如 RY1303）** | PMIC（AXP 系列） |
|---|---|---|---|
| 可觀測性 | 每軌獨立量測 | **三組電感與 feedback 都在外面，照樣量得到** | 黑盒子 |
| 上電時序 | EN 腳自己串 | EN1/EN2/EN3 **獨立控制**（要自己做時序） | 內部狀態機，改不了 |
| 板面積 | 大 | 中 | 小 |
| 故障處理 | 換單顆 | 換整顆（三路一起沒） | 換整顆 |
| 料況 | 通用料 | ⚠ **中國小廠料，須查 LCSC** | 專用料 |

**排除 PMIC 的理由依然成立**（內部時序看不見），但**三路 DC-DC 沒有那個問題**——
三個電感、三組分壓電阻都露在板子上，探棒照樣量。

> ⚠ **v0.8 更正**：上表原本寫 RY1303 的優點是「EN1/EN2/EN3 **內建順序**」。
> **錯的。** datasheet 寫的是
> `"the independent enable control makes the designer have the greatest flexibility
> to optimize timing for power sequencing purposes"` ——
> **三支 EN 是獨立輸入，沒有任何內建排序功能，時序要自己做。**
>
> 錯誤來源是把「有三支 EN 腳」當成「有排序功能」。
> **零件的彈性不等於零件幫你做事。**

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

**ADV7511 的 1.8V 另有專門要求** `(ADV7511W HW Guide p.41 Figure 21)`：

```
四個 1.8V 域 (DVDD/AVDD/PVDD/BGVDD) 分成 3 組獨立 PCB 電源域，各加 LC 濾波
每支電源腳 0.1µF，盡量貼近腳位
PVDD（PLL）最敏感
```

```
TMDS Differential Swing  800 / 1000 / 1200 mV   (Table 1, p.13)
★ R_EXT (pin 28)  887 Ω ±1% 接地  —— 設定內部參考電流  (Table 3 p.19 / §7.6 p.54)
  走線越短越好；⚠ LRCLK（含 via）不可靠近 pin 28
```

⚠ 與 IT66121 的 REXT 5.6kΩ **值完全不同**，不可沿用。

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
ADV7511（HDMI 工作中）         ~0.33 W → 5V 端約 80 mA   (1.8V 325mW + 3.3V 1mW)
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
[x] VDD18-DRAM (pin 50) → **MangoPi 接 LDOA-OUT**（原理圖 p.3 目視確認）
     本板改接外部 +1V8_SOC，內建 LDOA 不使用（見 011-power-tree.md §3.1）
[ ] MIPI DSI D-PHY 的電源軌與 4-lane 電流
[ ] 上兩項合計是否超過 LDOA 的 260 mA → 決定要不要外部 1.8V
[x] RY1303 料況 → 庫存 23,969、$0.20、datasheet 已取得 → **採用三路 DC-DC**
[x] MangoPi 的 RESET → **R74 10K 上拉 LDOA-OUT + C84 0.1µF**，RC 僅 1 ms
     規格要 64 ms，**差 60 倍 → 確認它沒滿足規格,本板加 APX803 supervisor**
[x] VCC-PD / VCC-PE / VCC-PG 各選 1.8V 還是 3.3V → **三者全選 3.3V**（見 §1.1）
[x] 1.8V LDO 選型 → **AP2112K-1.8TRG1 (C176944, 600mA)**，XC6206 的 200mA 不夠
[x] ADV7511 五個 1.8V 域 → **3 組**：DVDD ／ AVDD+PVDD ／ PLVDD+BGVDD，各加 10µH+10µF
[x] ADV7511 要**自己專屬的 1.8V LDO**（§6.8）→ 1.8V 拆成兩條
[x] 電源樹數值全部定案 → **見 [011-power-tree.md](011-power-tree.md)**
[ ] VCC-PD = 3.3V 時 MIPI 是否正常 —— 找有接 DSI 面板的參考設計核對
[ ] Table 5-2 / 5-3 的數字回 p.45-48 原頁目視核對（pdftotext 欄位有錯位）
```

---

## 9. 量測清單（bring-up 第一天）

```
[ ] 上電前先量各軌對地電阻，確認沒有短路
[ ] 3.3V / 1.5V / 0.9V 三軌電壓，誤差 <±3%
[ ] 若用內部 LDOA，量 LDOA-OUT (pin 28) 是否為 1.8V
[ ] ADV7511 的 1.8V 軌電壓與漣波：DVdd/PVdd/BGVdd 各 <64 mV RMS，AVdd/PLVdd 更嚴
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
