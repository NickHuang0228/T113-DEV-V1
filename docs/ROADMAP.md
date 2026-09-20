# 選型、風險與驗收

---

## 1. 長期目標

累積 **CSI / DSI / HDMI / DP** 四個顯示影像介面的 layout 實作經驗。

| | 板子 | 補的技能 | 狀態 |
|---|---|---|---|
| 第 1 塊 | ESP32S3-DEV-V1 | KiCad 全流程、4 層疊構、USB FS、出圖下單、bring-up | **完成** |
| **第 2 塊** | **T113-DEV-V1**（本專案） | **Linux bring up、多電壓域、13 對差分、阻抗控制、RGB 並列** | 規劃中 |
| 第 3 塊 | 高速差分轉接／探測板 | DP 8.1Gbps、Type-C mux、測試點不破壞阻抗 | 構想 |

---

## 2. 選型過程

### 2.1 候選與淘汰理由

| 晶片 | DDR | 封裝 | MIPI DSI | HDMI | 結論 |
|---|---|---|---|---|---|
| **T113-S3** | **內建 SIP** | **eLQFP128** | **✓** | 需 bridge | **選定** |
| Allwinner H3 | 外接 DDR3 | BGA347 | **✗ 無** | 原生 4K@30 | 淘汰 |
| F1C200s | 內建 64MB | LQFP128 | ✗ | ✗ | 太弱 |
| RK3566 | 外接 DDR4 | BGA636 0.8mm | ✓ | ✓ | 太難（DDR4） |
| RK3568 | 外接 DDR4 | BGA636 0.8mm | ✓ | ✓ + **DP** | 留給第 3 或 4 塊 |
| RK3588 | 外接 LPDDR | BGA ~1100 0.65mm | ✓ ×2 | ✓ | 個人畫不了（12~16 層 HDI） |
| Gowin GW2AR-18 | 內建 SDRAM | QFN88 | ✗ 無硬體 D-PHY | 需自建 | 換方向：這是 FPGA，不是 Linux |

### 2.2 H3 為什麼出局

一度是首選（有完整開源 KiCad 參考設計、原生 4K HDMI）。查 datasheet 第 59–60 頁後否決：

```
2.1.5.2 Display Output
  • Total two display interfaces available      ← 總共就兩個
      - HDMI V1.4 output with HDCP1.2, up to 4K@30fps
      - TV CVBS output
```

**H3 沒有 RGB 並列、沒有 LVDS、沒有 MIPI DSI。** 它是機上盒晶片，Allwinner 把面板介面省掉了。長期目標是 DSI，H3 這條路從一開始就不通往那裡。

（DE2.0 本身支援到 4096×4096，但那是內部合成引擎，出不去就沒用。）

### 2.3 為什麼 HDMI 走 bridge 反而是好事

T113-S3 沒有原生 HDMI，要靠橋接晶片（v0.4：ADV7511）把 RGB 並列轉成 HDMI。這看似是缺點，實際上：

```
多學一個介面   24 條 RGB 並列 + 4 控制線，對 CK 等長
              這是「並列高速匯流排」的入門，和 DDR、和 MIPI bridge 是同一種技能
```

而「HDMI 原不原生」對 layout 練習沒有差別 —— TMDS 差分該怎麼走還是怎麼走。

---

## 3. 風險評估

### 3.1 高機率成功

| 項目 | 信心 | 依據 |
|---|---|---|
| 電源電路 | 高 | 分壓值可用公式驗算，上一塊板做過 |
| DRC / 出圖 / 下單 | 高 | 上一塊板已走完整遍，工具與方法都在 |
| FEL 認得到晶片 | 高 | 只要電源與 USB 正確，BROM 就會回應 |
| 乙太網路 | 中高 | RTL8201F mainline 支援，電路標準 |

### 3.2 主要風險（依嚴重度）

**① eLQFP128 footprint 尺寸錯 —— 致命且無法補救**

```
焊盤長寬或間距錯了 → 整批報廢
來源必須是 datasheet 的機構圖，不能抄網路
下單前務必 1:1 列印比對

⚠ datasheet §7.2 (p.78) 有原廠 CAUTION：
   exposed pad 的機構圖上有「兩組」尺寸，
   必須用第二組 D3/E3 = 5.72 mm REF 來畫 footprint。
   拿錯那組 → 整批報廢。
```

EPAD 本身也是致命項：它是這顆晶片**唯一的數位地**（128 隻腳裡只有 1 支 AGND），
沒焊到就完全不會動，而且焊得好不好無法目視檢查。詳見 001-power.md §7。

上一塊板踩過兩次「拿欄位字面值當實際幾何」的坑（J1 custom pad、ESP32 模組 pad 自轉 270°）。這次的教訓是：**footprint 一律回到原廠機構圖驗算，不信任任何二手來源。**

**② 電源上電時序 —— 不開機，但有 log 可追**

```
T113-S3 對 VDD_CPU / VDD_SYS / VCC_IO / VCC_PLL 的上電順序有要求
症狀：FEL 都認不到，或認到但跑不起 SPL
緩解：UART log + FEL 分段驗證（見 004-usb-boot.md）
```

比 DDR 好的地方在於：**每一階段都有訊號可量、有 log 可看**，不是「完全沒反應」。

**③ 阻抗控制第一次做 —— 畫面閃爍或無畫面**

```
13 對差分，四種不同阻抗需求
緩解：下單時開阻抗控制，照 JLCPCB 回算的線寬重畫
短距離（<10cm）即使偏差 10% 通常仍可動
```

**④ MIPI 與 RGB 共用 PD0~PD9 —— 分支處理錯了 MIPI 就不會亮**

```
MIPI DSI  PD0~PD9   RGB 並列  PD0~PD21   → 前 10 支完全重疊
軟體切換切不掉電氣負載，必須用 10 顆 0Ω 隔離
0Ω 焊盤距主幹 > 0.5mm 的話，MIPI 線上就留著一段 stub → 白做
緩解：0Ω 貼著分支點放，MIPI 直通不串任何東西。詳見 002-display.md §1
```

**⑤ RGB 並列的 SSO noise —— HDMI 無畫面或花屏**（v0.3：等長已不是風險，改列 SSO）

```
18 條資料（本板選 RGB666）+ 4 控制，1080p60 → 148.5 MHz

等長：不是風險。用 IT66121 的 TS=1.5ns / TH=0.7ns 算過一次，
      扣掉保守的 3.5ns 給 SoC skew + jitter，PCB 仍有 ~149mm 餘裕，
      而 100×100mm 板上兩條線根本差不到那麼多。做到 ±10mm 是整齊，不是需求。

⚠ 換成 ADV7511 後這組數字要重取重算（結論預期不變，但算式不能沿用別顆晶片的規格）。

真正的風險：22 條同時翻轉的 SSO 地彈，會直接吃掉橋接晶片的 jitter 預算。
緩解：串聯阻尼電阻 22~33Ω、控制 slew rate、完整 GND 回流、資料線分組穿插 GND
```

**⑦ 周邊 IC 的隱藏電源軌 —— 漏了就是少焊一顆 LDO，板子回來才發現**（v0.3 新增）

```
IT66121 要 1.2V、ADV7511 要 1.8V(約180mA)、RTL8201F 只要 3.3V —— 三顆三種答案
ADV7511 的 180mA 還把 1.8V LDO 從 XC6206(200mA) 逼成 AP2112K(600mA)

教訓：每顆 IC 都要開 Power/Ground Pins 那一頁逐腳看，不能假設「3.3V 單軌」
      這一條在 v0.2 之前是漏的，規格書上「4 組電源域」寫了兩個版本都沒人發現
```

**⑥ Linux 跑不起來 —— 但這是軟體問題，可以慢慢調**

板子焊好之後，kernel / dts / driver 都能反覆改。**硬體錯了要重做，軟體錯了只要重編。** 這是這塊板相對安全的地方。

### 3.3 綜合判斷

```
FEL 認得到晶片            85~90%
UART 出現 U-Boot log      80~85%
Linux 進到 shell          75~80%
乙太網路可用              75%
HDMI 出畫面               60~70%
MIPI 面板點亮             50~60%（軟體參數為主，可反覆調）
一次下單就完全可用         45~55%
```

**關鍵不在運氣，在下單前的驗證是否跟上一塊板一樣嚴格。**
上一塊板 263 段走線、DRC 三項歸零、Gerber 逐檔比對 —— 同一套方法在這裡同樣有效。

---

## 4. 開發階段

```
階段 0  規格與選型                  ← 目前在這
        [x] 介面清單定案
        [x] 成本估算
        [x] datasheet 取得（v1.6 + User Manual v1.1/v1.3 + MangoPi MQ-R 原理圖）
        [x] 封裝型式 → eLQFP128 14×14×1.4mm，EPAD = 唯一數位地
        [x] 上電時序 → T1>2ms、T2>64ms，關機無限制
        [x] 電源軌電壓 → 0.9V / 1.5V / 3.3V + 內建 LDOA 供 1.8V
        [x] 熱阻 → θJA 20.36°C/W，不需散熱片
        [x] 封裝機構圖數字（pitch / b / L / D,E / **D3,E3**）—— 見 008-footprint.md
        [x] TCON 數量 → **2 組**（TCON_LCD 給 RGB/LVDS/DSI，TCON_TV 給 CVBS）
        [x] RGB pixel clock 上限 → **SoC 200MHz**（tDCLK≥5ns, DS Table 5-18 p.61）
            **橋接晶片 165MHz 才是瓶頸**；1080p60 的 148.5MHz 兩邊都過
        [~] MIPI lane rate → **DS 與 UM 都沒公布**（UM §5.4 只有 1 頁概述）
            由 1920×1200@60 反推約 1.0~1.2 Gbps/lane → layout 照 1.5Gbps 規格做
        [x] 勘誤：T113-S3 **無 GPU、無 RISC-V C906**，datasheet 全文零命中
        [x] 周邊 IC 電源：IT66121 要 1.2V / ADV7511 要 1.8V / RTL8201F 只要 3.3V
        [x] VCC-PD / VCC-PE / VCC-PG → **全部 3.3V**
        [x] 零件料號逐項查證 → 見 009-bom.md
            ⚠ **IT66121FN 停產（C2684803,庫存 0）** → 改用 **ADV7511KSTZ (C179459)**
            判準從「driver 最省事」改為「driver 工作就是練習目標」,見 002-display.md §3.1
            ⚠ T113-S3 實價 **$22.25**,不是估的 $8 → PCBA 片數 3 降為 2
            ✅ RY1303 料況良好（23,969 顆 @$0.20）,三路 DC-DC 可用

階段 1  原理圖
        [ ] T113-S3 符號建立（依 datasheet 分 bank）
        [ ] 電源樹
        [ ] 各介面電路
        [ ] ERC 歸零

階段 2  PCB layout
        [ ] footprint 逐一驗算 + 1:1 列印比對（見 008-footprint.md）
        [ ] 層疊與阻抗線寬（用 JLCPCB 回算值）
        [ ] 差分對走線（13 對）
        [ ] RGB666 並列等長（22 條）+ MIPI/RGB 分支 10 顆 0Ω（焊盤距主幹 ≤0.5mm）
        [ ] 鋪銅、DRC 三項歸零

階段 3  出圖與下單
        [ ] Gerber 逐檔比對（內層檔名不可帶括號 —— 上一塊板踩過）
        [ ] CPL 用 JLCPCB 官方五欄格式
        [ ] BOM 料號逐顆核對
        [ ] 零件方向在 Confirm Parts Placement 頁逐顆確認
        [ ] 鋼網**不**加購（部分貼裝用不到，見 006-assembly.md）
        [ ] PCBA 數量設 **2 片**（成本驅動），BOM 只列 T113 / ADV7511 / RTL8201F
        [ ] LCSC 零件訂單建立並與 JLCPCB 合併運費
        [ ] 主晶片備品數量確認（T113 / ADV7511 各 +1~2，單價分別 $22.25 / $13.75）

階段 4  bring-up
        [ ] 上電量測各電壓軌
        [ ] FEL：sunxi-fel version 有回應
        [ ] UART：U-Boot log
        [ ] SD 卡開機到 shell
        [ ] 乙太網路 ping
        [ ] HDMI 出畫面
        [ ] MIPI 面板點亮
```

---

## 5. 驗收條件（下單前）

比照上一塊板的標準：

- [ ] T113-S3 / ADV7511 / RTL8201F footprint 對照 datasheet 機構圖逐項核對，1:1 列印比對
- [x] **T113-S3 的 EPAD 用 datasheet §7.2 的「第二組」尺寸 → 5.72 × 5.72 mm 正方形**
      ⚠ 機構圖有六組，第 ⑥ 組也是 5.72 開頭但為長方形 5.72/5.46 —— 別選錯
- [ ] KiCad footprint 用 `LQFP-128_14x14mm_P0.4mm`（JEDEC MS-026 BEE，與 datasheet NOTE 8 相符）+ 自加 EPAD
- [ ] placement 佔位按 **16.8mm**（含腳與焊盤），不是本體的 14mm
- [ ] EPAD 下方 thermal via 陣列已放，且設為 **plugged**（否則錫會漏到背面，晶片浮起）
- [x] RTL8201F 機構圖已取得，KiCad 標準件對得上（見 008-footprint.md §5）
- [x] **ADV7511 機構圖數字已取得**：ST-100 / MS-026-BED / 本體 14.00 / 含腳 16.00 / pitch 0.50
      **無 EPAD** → KiCad `LQFP-100_14x14mm_P0.5mm` 直接可用，不需自建
- [x] **ADV7511 原始 PDF 已入庫**（58 頁 Rev D），完整腳位表與 §7 layout 建議已取
- [ ] ⚠ RTL8201F 確認用 datasheet §10.1 的 QFN-32，不是 §10.2 LQFP-48 / §10.3 QFN-48
- [ ] 電源上電時序對照 datasheet，寫成文件記錄
- [ ] **1.8V 拆成兩條**：SoC 一顆、**ADV7511 專屬一顆**（ADI §6.8 要求）
- [ ] ADV7511 的 1.8V 分 **3 組**：DVDD ／ AVDD+PVDD ／ PLVDD+BGVDD，各加 10µH+10µF
- [ ] ADV7511 每支電源腳 0.1µF、11 支 GND 各自 via 下 plane
- [ ] ADV7511 未用的 D[35:24](pin 57~68) 與 D17/D16/D9/D8/D1/D0 接 GND
- [ ] ★ **R_EXT = 887Ω ±1%** 已放，走線短，LRCLK 與 via 不靠近 pin 28
- [ ] ★ DDCSDA/DDCSCL 上拉 1.5k~2kΩ 到 HDMI +5V（datasheet 寫 required）
- [ ] ★ PD/AD (pin 38) 接法已定義（它同時決定 I2C 位址與 PD 極性）
- [ ] ★ LCD0-CLK 列入阻抗控制（單端）
- [ ] **RGB 接線在原理圖上標 LCD0-D 編號，不標顏色**（避免 R/B 對調）
- [ ] ADV7511 的 D[17:16] / D[9:8] / D[1:0] 接 GND，D[35:24] 依 datasheet 處置
- [ ] 分壓電阻算出的電壓與標稱值相符（用公式驗算，不靠標籤）
- [ ] DRC violations / unconnected / schematic parity 三項歸零
- [ ] 四層鋪銅完成，內層 GND 為完整一片
- [ ] 13 對差分：阻抗控制已開、線寬照 JLCPCB 回算值、對內等長符合各自規格
- [ ] RGB666 22 條對 CK 等長，串聯阻尼電阻已放
- [ ] MIPI/RGB 分支的 10 顆 0Ω 焊盤距主幹 ≤0.5mm（不焊時 MIPI 線上無 stub）
- [ ] 排針 20 條對外訊號全部有限流電阻，且全在 PG bank（SPI 除外）
- [ ] BOM 料號逐顆核對（尤其電阻編碼，上次踩過 6200/6201 差十倍）
- [ ] CPL 為 JLCPCB 官方五欄格式，座標與 kicad-cli 交叉比對
- [ ] Gerber 內層檔名不含括號（上次因此被判成 2 層板）
- [ ] 零件方向在 Confirm Parts Placement 頁逐顆確認

---

## 6. 下一塊板的構想

做完這塊，缺的是 **DP**。構想是高速差分轉接／探測板：

```
Type-C DP 進 ──▶ [板] ──▶ DP 座出
                  ├─ 差分測試點（可接探棒）
                  ├─ mux / redriver
                  └─ CC / PD 邏輯
```

DP 1.4 HBR3 是 **8.1 Gbps/lane** —— 比 MIPI 快 6 倍，是能碰到的最高速差分。
成本低（沒有貴晶片），技能密度高。

### ⚠ 2026-09-20：這塊板的優先序要調高

職涯目標鎖定 **HDMI/DP driver porting 與 IC 驗證**（MediaTek HDMI 軟韌體工程師職缺
明列「HDMI **and DP** Linux/Android Kernel driver porting」與「HDMI and DP IC 驗證」）。

```
T113-DEV-V1  →  HDMI 那一半（ADV7511 bridge porting + 驗證）  ✓
DP           →  這塊板完全沒有,T113-S3 無 DP 輸出
```

**第 2 塊只補得到一半。** 第 3 塊從「構想」升級為明確的下一步，
而且重點應該從純 layout 練習，往「能跑 DP driver / 能做 DP 驗證」偏移 ——
純被動轉接板量得到訊號但沒有 driver 可寫，要考慮加一顆有 mainline driver 的 DP bridge。
