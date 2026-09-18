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

T113-S3 沒有原生 HDMI，要靠 IT66121 把 RGB 並列轉成 HDMI。這看似是缺點，實際上：

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

**⑤ RGB 並列等長 —— HDMI 無畫面或花屏**

```
18 條資料（RGB666，非 RGB888）+ 4 控制，對 CK 等長
pixel clock 若跑 1080p 約 148MHz，skew budget 約 ±80mm（比 DDR 寬鬆得多）
真正的殺手是 SSO noise：24 條同時翻轉的地彈
緩解：串聯阻尼電阻 22~33Ω、控制 slew rate、完整 GND 回流
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
        [ ] 封裝機構圖數字（pitch / b / L / D,E / **D3,E3**）—— p.78 有原廠 CAUTION
        [ ] TCON 數量、MIPI lane rate、RGB pixel clock 上限
        [ ] 零件料號逐項查證（LCSC 即時價、庫存、Basic/Extended）

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
        [ ] PCBA 數量設 3 片，BOM 只列 T113 / IT66121 / RTL8201F
        [ ] LCSC 零件訂單建立並與 JLCPCB 合併運費
        [ ] 主晶片備品數量確認（T113 ≥3、IT66121 ≥3）

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

- [ ] T113-S3 / IT66121 / RTL8201F footprint 對照 datasheet 機構圖逐項核對，1:1 列印比對
- [x] **T113-S3 的 EPAD 用 datasheet §7.2 的「第二組」尺寸 → 5.72 × 5.72 mm 正方形**
      ⚠ 機構圖有六組，第 ⑥ 組也是 5.72 開頭但為長方形 5.72/5.46 —— 別選錯
- [ ] KiCad footprint 用 `LQFP-128_14x14mm_P0.4mm`（JEDEC MS-026 BEE，與 datasheet NOTE 8 相符）+ 自加 EPAD
- [ ] placement 佔位按 **16.8mm**（含腳與焊盤），不是本體的 14mm
- [ ] EPAD 下方 thermal via 陣列已放，且設為 **plugged**（否則錫會漏到背面，晶片浮起）
- [x] IT66121 / RTL8201F 機構圖已取得，KiCad 標準件對得上（見 008-footprint.md §4 §5）
- [ ] ⚠ RTL8201F 確認用 datasheet §10.1 的 QFN-32，不是 §10.2 LQFP-48 / §10.3 QFN-48
- [ ] 電源上電時序對照 datasheet，寫成文件記錄
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
