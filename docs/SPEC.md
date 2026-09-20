# T113-DEV-V1 規格書

版本：草案 v0.1 · 2026-09-18

---

## 1. 設計目標

一塊能開機、能上網、能推畫面的自製 Linux 開發板。所有介面都是**自己畫的**，不使用核心板或模組。

驗收的最低標準：**UART 出現 kernel log，`ping` 得通，HDMI 有畫面。**

---

## 2. 主晶片

```
Allwinner T113-S3
  CPU      2× ARM Cortex-A7           (DS §2.1 p.3)
            ⚠ datasheet 未載明時脈,全文搜 `GHz` 零命中
  協處理器  HiFi4 DSP（單核）           (DS §2.2 p.3)
            ⚠ 沒有 RISC-V C906 —— 見下方勘誤
  GPU      ⚠ 沒有 GPU —— 見下方勘誤
            只有 DE（顯示引擎）/ DI（去交錯）/ G2D（2D 加速）  (DS §2.5 p.5-6)
  記憶體    128MB DDR3（SIP 封裝，晶片內建），時脈上限 800MHz  (DS §2.3.2 p.4)
  封裝      eLQFP128  14 × 14 × 1.4 mm  (DS §2.12 p.19 / §7.1 p.77)
            底部 EPAD = pin 129 = 這顆晶片唯一的數位地（見 001-power.md §7）
  電壓      VDD-CORE / VDD-SYS  0.9V     ⚠ 不是 1.1V
            VCC-DRAM0/1         1.5V     ⚠ 內建 DDR3 仍要外部供電
            VCC-IO              3.3V
            VCC-PD/PE/PG        3.3V     全部定案（001-power.md §1.1）
            1.8V 群              外部 LDO（內建 LDOA 僅 260mA，不夠賭）
  價格      約 $8（LCSC，需查即時價與庫存）
```

### ⚠ v0.3 勘誤：兩項規格是錯的，而且會影響驗收標準

`Mali-G31 MP2` 與 `RISC-V C906` **在 datasheet 與 User Manual 裡完全不存在**。
全文搜 `Mali` / `GPU` / `OpenGL` / `Vulkan` / `RISC-V` / `C906` —— 兩份文件都零命中。

```
DS §1 Overview, p.3
  "T113-S3 ... integrates dual-core Cortex-A7 CPU and single-core HiFi4 DSP"
DS §2.1 CPU Architecture, p.3
  "Dual-core ARM Cortex-A7" —— 就這一行，沒有第二種核心
DS 系統方塊圖, p.20
  Video Output 區塊只有 DE / DI / G2D，沒有 3D 引擎
```

這兩項應該是從**同門的其他晶片**抄來的（D1/D1s 有 C906，A133/T507 有 Mali-G31）。

**後果（這才是重點）：**

```
沒有 GPU    → 顯示堆疊只有 framebuffer / DRM-KMS + G2D 2D 搬圖
              沒有 OpenGL ES，跑不了桌面合成、glmark2、任何 3D
              「HDMI 出畫面」的驗收 = 測試圖樣 / 影片解碼，不是桌面環境
沒有 C906   → 沒有 RISC-V 副核可玩
```

⚠ 另外：**datasheet 全文沒有出現任何 CPU 時脈數字**（搜 `GHz` 零命中）。
`@1.2GHz` 是市場資料，不是規格書數字 —— 本文件不再引用。

**選它的核心理由：內建 DDR3。** 第一塊 Linux 板最大的失敗來源是 DDR layout（32-bit 匯流排等長 ±0.6mm、fly-by 拓樸、阻抗控制），T113-S3 把這塊做進封裝裡，等於整條風險刪除。

---

## 3. 介面清單

### 3.1 顯示

| 輸出 | 規格 | 元件 | 差分對 |
|---|---|---|---|
| MIPI DSI | 4 lane + clock，1920×1200@60 | FPC 座 0.5mm | **5 對** |
| HDMI | RGB666 並列 → HDMI 1.4，1920×1080@60 | IT66121（**QFN64 9×9，底部 GND pad**） | **4 對 TMDS** |

**⚠ 兩者共用同一組實體接腳 PD0~PD9，不只是共用 TCON。** `(DS Table 4-3 Pin Multiplexing)`

```
MIPI DSI   PD0 ~ PD9    （4 lane + clock = 5 對）
RGB 並列   PD0 ~ PD21   （18 資料 + 4 控制 = 22 條）
重疊       PD0 ~ PD9    完全重疊
```

軟體切換不能把電氣負載切掉 → **PD0~PD9 用 10 顆 0Ω 隔離，MIPI 直通、IT66121 走分支。**
本專案優先序：**MIPI DSI > RGB/HDMI**。詳見 [002-display.md](design/002-display.md) §1。

⚠ **本板的 RGB 並列選 RGB666（18-bit），HDMI 輸出因此是 26 萬色，漸層會有 banding。**

這是取捨，不是晶片限制：缺的 6 個 bit（LCD0-D0/D1/D8/D9/D16/D17）在 PD bank 上
確實不存在，但它們在 **PB2~PB7 的 Function2** 上 `(DS Table 4-3 p.30)`，
UM Table 5-2 (p.399) 也有完整的 RGB888 欄。**晶片支援 RGB888，我們選擇不借 PB。**

不借的理由：PB 在 VCC-IO 上，那條軌同時掛著 microSD、SPI NOR、UART0 console
—— 為了 1.2% 的色深把 6 條 148MHz 的線拉進命脈 bank，不划算。見 007-pinmap.md §6.3。

腳位對應（UM Table 5-2 的 high-aligned 規則 + DS Table 4-3）：

```
PD0 ~ PD5    = LCD0-D2 ~ D7    = B[5:0]      ⚠ PD0 是 B0(LSB)
PD6 ~ PD11   = LCD0-D10 ~ D15  = G[5:0]
PD12 ~ PD17  = LCD0-D18 ~ D23  = R[5:0]
PD18~PD21    = CLK / DE / HSYNC / VSYNC
```

**原理圖一律標 `LCD0-D` 編號，不標顏色** —— IT66121 的輸入腳也叫 `D[23:0]` 且同樣
high-aligned，按編號 1:1 接就自動對；轉成顏色名稱才會有 R/B 對調的機會。
未用的 IT66121 D[17:16] / D[9:8] / D[1:0] 接 GND。

MIPI DSI 則支援 RGB888 `(DS §2.6.2 p.6)`。

選 IT66121 而非 LT8618SX 的理由：

```
drivers/gpu/drm/bridge/ite-it66121.c   ← mainline 就有 driver
```

LT8618SX 在 Linux 上通常要靠廠商 blob。**第一塊板不在 driver 上冒險。**

### 3.2 網路

```
T113-S3 EMAC ──RMII──▶ RTL8201F ──▶ RJ45（整合式含變壓器）
                        QFN32       2 對差分（TX± / RX±）
```

選乙太網路而非 WiFi 的理由見 [003-network.md](design/003-network.md)，一句話：**U-Boot 階段沒有 WiFi，拿不到 TFTP + NFS 開機**，而那會讓開發循環從 5 分鐘縮到 20 秒。

### 3.3 USB 與燒錄

| 接口 | 用途 | 差分 |
|---|---|---|
| Type-C #1 | OTG + FEL 燒錄 + 供電 | **1 對 USB HS 90Ω** |
| Type-C #2 | CH340N → UART0 log + 供電 | — |
| USB-A | Host（WiFi dongle / 鍵鼠） | **1 對 USB HS 90Ω** |

兩個 Type-C 都用 **CC1/CC2 各 5.1kΩ 下拉**（標準 sink，取 5V），不使用 PD。

### 3.4 儲存

```
microSD   主要開機裝置，4-bit SDIO
SPI NOR   16MB（XT25F128B 或同級），FEL 可燒，備援開機
```

### 3.5 其他

```
音訊    內建 codec → 3.5mm 座（line-out）
按鍵    FEL / RESET / 電源
LED     電源 / 使用者 ×2
排針    26-pin (2×13)，全部經限流電阻
        I2C ×2        PG7/PG8、PG9/PG10        隨時可用
        UART 備援 ×1  PG13/PG15                隨時可用
        GPIO ×10      PG0~PG6, PG11, PG12, PG14  隨時可用
        SPI ×1        PD10~PD13                ⚠ 僅 MIPI 模式

⚠ 原本寫 GPIO ×20 是未經腳位驗算的數字。PG bank（唯一適合對外的 bank）只有 16 支。
WiFi footprint 移除後全部 16 支可用。詳見 [007-pinmap.md](design/007-pinmap.md)。
```

---

### 3.6 WiFi：完全不做

```
v0.1   預留 RTL8723DS footprint + SDIO 走線 + 天線區（DNP，畫但不焊）
v0.2   ✗ 完全移除
```

**移除的理由不是成本，是腳位。** WiFi 的 SDIO1 走 PG0~PG5，
而 PG 是這塊板**唯一適合對外的 bank**（其他 bank 一燒就變磚或失去網路，
見 [007-pinmap.md](design/007-pinmap.md) §3）。

```
WiFi footprint 吃掉 PG 16 支裡的 6 支 = 37%
排針的純 GPIO 從 10 支掉到 4 支
```

移除後的收穫：

```
+ 排針純 GPIO   4 → 10 支
+ 板面積        省 30 × 20 mm（更容易守住 100×100mm 的價格斷點）
+ GND 平面      天線區的挖空消失 → 不必處理「挖空 GND 又不破壞旁邊差分回流」
+ VCC-PG 電壓   不再被 SDIO 綁住，可自由選 3.3V 配合外接模組
− RF layout     練不到（這是唯一的損失，且是學習目標而非功能）
```

**要無線就插 USB WiFi dongle**（RTL8188EU / MT7601U，mainline driver 完整，零 layout 成本）。

這是本專案第三次用同一招：**WiFi → USB dongle、攝影機 → USB UVC、無線 → USB dongle。**
當一個功能要吃掉稀缺腳位或帶來 layout/driver 風險，而 USB 上有成熟替代品時，就走 USB。

---

## 4. 差分對總覽

| 訊號群 | 對數 | 阻抗 | 速率 | 難度 |
|---|---|---|---|---|
| MIPI DSI | 5 | 100Ω 差分 | ~1 Gbps/lane | ★★★ |
| HDMI TMDS | 4 | 100Ω 差分 | ~1.5 Gbps/pair | ★★★ |
| USB 2.0 HS | 2 | 90Ω 差分 | 480 Mbps | ★★ |
| 乙太 TX/RX | 2 | 100Ω 差分 | 100 Mbps | ★ |
| **合計** | **13 對** | | | |

加上 RGB 並列 **22 條**單端（**18 資料** + HS/VS/DE/CK）與 10 顆 0Ω 隔離電阻，
**這是這塊板 layout 工作量的主體**。

⚠ 差分對總數仍是 13 對，但 MIPI 的 5 對與 RGB 的前 10 條是**同一組實體走線**，
分支點的處理（0Ω 貼著主幹，stub ≤ 0.5mm）是這塊板最精細的一段 layout。

---

## 5. 電源樹

```
Type-C VBUS 5V
  ├─ DC-DC   →  3.3V   VCC-IO / GPIO bank / PHY / IT66121 / LDO-IN   ~470mA
  ├─ DC-DC   →  1.5V   VCC-DRAM0/1（DDR3 本體）                       TBD
  ├─ DC-DC   →  0.9V   VDD-CORE0/1 + VDD-SYS0/1/2                    TBD
  ├─ LDO     →  1.8V   VCC-PLL / VCC-RTC / VCC-LVDS / AVCC / VDD18-DRAM
  │                     外部 LDO，晶片內建 LDOA 僅 260mA 不夠賭
  ├─ LDO     →  1.2V   IT66121 IVDD12 / AVCC12 / PVCC12 / DVDD12     ~50mA
  │                     ⚠ VCCNOISE 只容許 100mVpp → 用 LDO 不用 DC-DC
  └─ 直通     →  5V    USB-A Host（含限流）                           500mA

外部電壓：**3.3V / 1.5V / 0.9V / 1.8V / 1.2V 共 5 組**
（3.3/1.5/0.9 可用單顆三路 DC-DC 如 RY1303，1.8V 與 1.2V 各一顆 LDO）

⚠ 1.8V 不要全押內建 LDOA（只有 260mA，且 VDD18-DRAM / AVCC / VCC-TVIN 在 datasheet 是 TBD）。
MangoPi 自己也放了外部 XC6206-1.8V LDO。多一顆 $0.05 換掉一個未知數。

⚠ **1.2V 是 v0.3 才發現的** —— IT66121 自帶核心電壓需求，不像 RTL8201F 有內建 LDO。
周邊 IC 的電源腳必須逐顆開 Power/Ground Pins 那一頁，不能假設「3.3V 單軌」。

IO bank 電壓：**VCC-PD / VCC-PE / VCC-PG 全部 3.3V**（見 001-power.md §1.1），
全板 IO 單一電平，不需要任何電平轉換。
```

詳見 [001-power.md](design/001-power.md)。峰值估算 **~900mA @5V = 4.5W**，Type-C 5V/3A 餘裕三倍。

⚠ VDD-CORE / VDD-SYS / VCC-DRAM 的電流在 datasheet 裡是 **TBD**（全志沒填），
只能靠估算或從參考設計反推。這是這份 datasheet 最大的缺口。

---

## 6. 製造規格

```
層數        4 層
疊構        JLC04161H-7628（與上一塊板相同，參數已驗證過）
板厚        1.6mm
外層銅厚    1oz
內層銅厚    0.5oz
阻抗控制    必須開啟（MIPI / TMDS / USB）
板框        ≤ 100×100mm（JLCPCB 價格斷點）
表面處理    ENIG（QFP 0.4mm pitch 建議）
PCB 數量    5 片
PCBA 數量   2 片
```

⚠ 阻抗線寬必須用 JLCPCB 回算值重畫，不能自行假設。

---

## 7. 成本估算

```
T113-S3 ×2                              $16
IT66121 ×2                              $8
RTL8201F ×2                             $2.5
CH340N ×2                               $1.6
電源 5 組 ×2                             $10
RJ45 含變壓器 ×2                         $4
接頭（HDMI / Type-C ×2 / USB-A / SD / FPC / 排針）  $11
SPI NOR / 晶振 ×3 / 被動件 ~80 顆        $12
PCB 4 層 5 片 + 阻抗控制                  $20
PCBA 服務費（部分貼裝 3 片，見 7.1）       $21
運費 DHL                                 $18
──────────────────────────────────────────────
合計                                     $122 ≈ NT$3,930
```

⚠ **上表已過時,見 [009-bom.md](design/009-bom.md) 的實查結果。** 兩項重大差異：

```
T113-S3    估 $8   實際 $22.25   ← 一項就多 $28.50(×2 片)
IT66121    估 $4   停產,買不到   ← 阻塞項,HDMI 橋接要改選
```

連帶決定:**PCBA 片數由 3 片降為 2 片**,否則三個替代方案都會超過 NT$5,000。

### 7.1 組裝方式的三種配置

PCB 最低量就是 5 片，**PCBA 貼幾片自己選**，剩下的當裸板寄回。

| | 全貼 2 片 | 貼 1 片 + 自焊 2 片 | **部分貼裝 ×3 片** |
|---|---|---|---|
| JLCPCB 貼什麼 | 全部零件 | 全部零件 | **只貼 3 顆難焊 IC** |
| PCB 5 片 + 阻抗 | $20 | $20 | $20 |
| PCBA 服務費 | ~$49 | ~$48 | **~$21** |
| LCSC 自購零件 | — | $45 | $45 |
| 鋼網 | — | $8 | **不需要** |
| 合併運費 | $18 | $18 | $18 |
| **合計** | ~$87 | ~$139 | **~$104 ≈ NT$3,330** |
| 拿到手 | 2 貼好 + 3 裸板 | 1 貼好 + 2 自焊 + 2 備用 | **3 片主晶片貼好 + 2 裸板** |

**改採最右欄「部分貼裝」。** v0.1 原本選中間那欄，查完 datasheet 後改掉，兩個理由：

**① T113-S3 的 EPAD 是唯一的數位地，不焊就不會動，而且焊得好不好看不見。**
IT66121 是 QFN64 + 底部 GND pad、RTL8201F 是 QFN32 —— 三顆都是手焊高風險件。
把「不可觀測的焊點」外包，「可觀測的」留給自己，跟當初選 QFP 不選 BGA 是同一個判斷標準。

**② 部分貼裝反而更便宜。** JLCPCB 的 PCBA 費用幾乎全在 **Extended part 上料費 $3.07/種**，
跟貼幾片、幾個焊點關係很小：

```
只貼 3 顆 IC  →  3 種 × $3.07 = $9.21
全部零件      → ~12 種 × $3.07 = $36.84
多貼 2 片的焊點成本 = 227 joints × 2 × $0.0016 = $0.73     ← 可以忽略
```

代價：**鋼網用不上了**（IC 已貼好，鋼網壓不平），80 顆被動件 × 3 片要烙鐵手焊。
累但零風險，焊壞看得見也重焊得了。

⚠ **建議被動件改用 0603 而非 0402** —— 手焊難度差一個等級，而面積對 100×100mm 不是問題。
這要在畫原理圖前決定。

⚠ PCBA 服務費依 JLCPCB 官方價目表（2026-09-09 版）計算：
`setup $8.18 + stencil $1.53 + confirm placement $0.45 + feeder $3.07/種 + SMT $0.0016/joint`。
料號種類數是估的，下單前用實際 BOM 重算。

JLCPCB 與 LCSC 同屬嘉立創，**兩邊訂單可合併出貨，運費只付一次**。

詳見 [006-assembly.md](design/006-assembly.md)。

---

## 8. 刻意不做的東西

第一塊 Linux 板的成功標準是「開機」，不是「功能齊全」。以下項目**明確排除**：

| 項目 | 理由 |
|---|---|
| eMMC | SD 卡開機就夠；焊死了不好換 |
| USB Hub | 增加複雜度，用不到 |
| WiFi 模組（含 footprint） | driver 風險高、U-Boot 階段用不到，且 SDIO 會吃掉 PG bank 6 支腳 —— 那是唯一適合對外的 bank。要無線插 USB dongle |
| **攝影機（Parallel CSI）** | **與乙太網路共用 PE0~PE9，二選一** —— 乙太是核心決定（U-Boot TFTP+NFS），不換。要攝影機插 **USB UVC**，mainline `uvcvideo` 完全支援，零 layout 成本 |

⚠ **T113-S3 沒有 MIPI CSI**，只有 8-bit Parallel CSI（DVP）`(DS §2.7.1 p.7)`。
腳位表裡只有一組 `NCSI0-*`，位於 PE bank `(DS Table 4-3)`：

```
CSI 需要   PE0 ~ PE11    NCSI0-HSYNC/VSYNC/PCLK/MCLK/D[7:0]
RMII 需要  PE0 ~ PE9     CRS-DV/RXD0/RXD1/REF-CLK/TXD0/TXD1/TX-EN/MDC/MDIO
重疊       PE0 ~ PE9     完全衝突
```

（MangoPi 原理圖的網路名就叫 `VCC-RMII-CSI` —— 他們也知道這兩個共用。
MQ-R 沒有乙太網路所以不衝突，我們有，就衝突了。）

**決定：PE bank 專用於 RMII，CSI 完全不畫。** 攝影機走 USB。
連帶好處：PE10~PE13 空出來可當 GPIO。
| PMIC | 分離式 DC-DC/LDO 比較好量測、好除錯 |
| DDR | 晶片內建 |

**每砍掉一項，第一次開機成功的機率就高一點。**

---

## 9. 待確認清單

下單前必須逐項查證，未確認不進 layout：

**已確認**

- [x] T113-S3 封裝型式 → **eLQFP128, 14 × 14 × 1.4 mm** `(DS §2.12 p.19 / §7.1 p.77)`
- [x] T113-S3 各電源軌電壓 → 見 §5 與 001-power.md §1 `(DS §5.3 p.45-46)`
- [x] T113-S3 上電時序 → T1 > 2ms、T2 > 64ms，關機無限制 `(DS §5.12 p.73-74)`
- [x] 熱阻 θJA = 20.36 °C/W、Tj max = 110 °C → 不需散熱片 `(DS §6 p.76)`
- [x] EPAD (pin 129) 是唯一數位地 → 必焊，交給 PCBA `(DS §4.1 p.23)`
- [x] IT66121 封裝 → **QFN64 9×9 mm + 底部 GND pad**（非 LQFP64）
- [x] MIPI 與 RGB 共用 PD0~PD9 實體接腳 → 需 0Ω 隔離 `(DS Table 4-3)`
- [x] **本板選 RGB666 → 22 條**（晶片支援 RGB888，需另借 PB2~PB7，本板不借）
      `(UM Table 5-2 p.399 / DS Table 4-3 p.30)`，理由見 007-pinmap.md §6.3
- [x] 解析度上限 → RGB 1920×1080@60、MIPI DSI 1920×1200@60 `(DS §2.6 p.6)`
- [x] **TCON 數量 → 2 組**：TCON_LCD（RGB/LVDS/DSI 共用）+ TCON_TV（CVBS）
      `(UM §5.1 p.397 / §5.2 p.452；CCU 0x0B60 / 0x0B80)` → RGB 與 DSI 確定二選一
- [x] **RGB pixel clock 上限 → 200 MHz**（tDCLK min 5 ns）`(DS §5.11.1 Table 5-18, p.61)`
      IT66121 只到 165 MHz → **瓶頸在橋接晶片**，1080p60 的 148.5 MHz 兩邊都過
- [x] **RGB666 腳位對應**：PD0~PD5 = B[5:0]、PD6~PD11 = G[5:0]、PD12~PD17 = R[5:0]
      ⚠ 002-display.md v0.2 把 R/B 標反，v0.3 已更正
- [x] **IT66121 需要 1.2V 軌**（IVDD12/AVCC12/PVCC12/DVDD12）`(IT66121 DS p.7, p.14)`
- [x] **RTL8201F 只需 3.3V**（核心 1.1V 由內建 LDO 產生，且不可外供）`(RTL DS §8.8 p.38)`

**未確認**

- [x] T113-S3 機構圖全部數字 → 見 [008-footprint.md](design/008-footprint.md) `(DS §7.2 p.78)`
      pitch **0.40 BSC** · b **0.18** (0.13~0.23) · L **0.60** (0.45~0.75)
      本體 D1/E1 **14.00** · **含腳 D/E 16.00** · 共面度 ccc 0.08 · JEDEC **MS-026**
      **EPAD = 5.72 × 5.72 mm**（機構圖有六組選項，CAUTION 指定第 ② 組）
      ⚠ 陷阱：第 ⑥ 組也是 5.72 開頭但為長方形 5.72/5.46
- [ ] MIPI DSI 最高 lane rate —— **DS 與 UM 都沒有公布**
      UM §5.4 只有 1 頁概述，無暫存器、無 D-PHY 時序表
      解析度上限 1920×1200@60 `(DS §2.6.2 p.6)` 反推約 1.0~1.2 Gbps/lane
      → layout 一律照 1.5 Gbps 的規格做（100Ω ±10%、對內 ±0.1mm），不賭
- [ ] MIPI D-PHY 的 4-lane 電流（電源軌已推定為 VCC-LVDS，見 001-power.md §2.2.2）
- [ ] VDD18-DRAM (pin 50) 接內建 LDOA 還是外部 1.8V
- [ ] IT66121 的 SYSRSTN 要接 GPIO（MIPI 模式時保持 reset）
- [ ] 1.2V LDO 選型（3.3V→1.2V，≥100mA，SOT-23）+ LCSC 料況
- [x] IT66121 封裝機構圖 → QFN-64 9×9，pitch 0.5，EPAD 3.78×3.78 `(IT66121 DS Figure 17, p.40)`
- [x] RTL8201F 封裝機構圖 → QFN-32 5×5，pitch 0.5，EPAD 3.35×3.35 `(RTL DS §10.1, p.55, JEDEC MO-220)`
- [x] VCC-PD / VCC-PE / VCC-PG → **全部 3.3V**（見 001-power.md §1.1）
- [ ] RY1303（三路 DC-DC）的 LCSC 料況 → 決定用三路或分離式 ×3
- [ ] 所有零件的 LCSC 料號、即時價、庫存、是否 Basic Part
