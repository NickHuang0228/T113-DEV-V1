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
  CPU      2× ARM Cortex-A7 @1.2GHz
  協處理器  RISC-V C906 @1.0GHz + HiFi4 DSP
  GPU      Mali-G31 MP2
  記憶體    128MB DDR3（SIP 封裝，晶片內建）
  封裝      QFP128  ⚠ pitch 與尺寸待從 datasheet 確認
  電壓      VDD_CPU 0.9~1.1V / VDD_SYS 1.1V / VCC_IO 3.3V / VCC_PLL 1.8V
  價格      約 $8（LCSC，需查即時價與庫存）
```

**選它的核心理由：內建 DDR3。** 第一塊 Linux 板最大的失敗來源是 DDR layout（32-bit 匯流排等長 ±0.6mm、fly-by 拓樸、阻抗控制），T113-S3 把這塊做進封裝裡，等於整條風險刪除。

---

## 3. 介面清單

### 3.1 顯示

| 輸出 | 規格 | 元件 | 差分對 |
|---|---|---|---|
| MIPI DSI | 4 lane + clock | FPC 座 0.5mm | **5 對** |
| HDMI | RGB 並列 → HDMI 1.4 | IT66121（LQFP64） | **4 對 TMDS** |

**兩者共用同一組 TCON，dts 二選一。** ⚠ 待確認：T113-S3 是否只有一組 TCON，若有兩組則可同時輸出。

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
排針    I2C ×2、SPI ×1、UART 備援、GPIO ×20
```

---

## 4. 差分對總覽

| 訊號群 | 對數 | 阻抗 | 速率 | 難度 |
|---|---|---|---|---|
| MIPI DSI | 5 | 100Ω 差分 | ~1 Gbps/lane | ★★★ |
| HDMI TMDS | 4 | 100Ω 差分 | ~1.5 Gbps/pair | ★★★ |
| USB 2.0 HS | 2 | 90Ω 差分 | 480 Mbps | ★★ |
| 乙太 TX/RX | 2 | 100Ω 差分 | 100 Mbps | ★ |
| **合計** | **13 對** | | | |

加上 RGB 並列 28 條單端（24 資料 + HS/VS/DE/CK），**這是這塊板 layout 工作量的主體**。

---

## 5. 電源樹

```
Type-C VBUS 5V
  ├─ DC-DC  →  1.1V   VDD_CPU + VDD_SYS     ~600mA
  ├─ DC-DC  →  1.8V   VCC_PLL / MIPI / DDR IO  ~200mA
  ├─ LDO    →  3.3V   VCC_IO / PHY / bridge  ~400mA
  └─ 直通    →  5V    USB-A Host（含限流）    500mA
```

詳見 [001-power.md](design/001-power.md)。峰值估算 **~900mA @5V = 4.5W**，Type-C 5V/3A 餘裕三倍。

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
電源 4 組 ×2                             $8
RJ45 含變壓器 ×2                         $4
接頭（HDMI / Type-C ×2 / USB-A / SD / FPC / 排針）  $11
SPI NOR / 晶振 ×3 / 被動件 ~80 顆        $12
Extended part fee（約 6 種）              $18
PCB 4 層 5 片 + 阻抗控制                  $20
PCBA setup + 2 片貼裝                     $35
運費 DHL                                 $18
──────────────────────────────────────────────
合計                                     $154 ≈ NT$4,960
```

⚠ 除 PCB / PCBA / 運費外，零件價格均為估算，下單前須逐項查 LCSC 即時價與庫存。

---

## 8. 刻意不做的東西

第一塊 Linux 板的成功標準是「開機」，不是「功能齊全」。以下項目**明確排除**：

| 項目 | 理由 |
|---|---|
| eMMC | SD 卡開機就夠；焊死了不好換 |
| USB Hub | 增加複雜度，用不到 |
| WiFi 模組 | driver 風險高，且 U-Boot 階段用不到；要無線插 USB dongle |
| MIPI CSI | 先把顯示這條鏈路走通，攝影機留到 V2 |
| PMIC | 分離式 DC-DC/LDO 比較好量測、好除錯 |
| DDR | 晶片內建 |

**每砍掉一項，第一次開機成功的機率就高一點。**

---

## 9. 待確認清單

下單前必須逐項查證，未確認不進 layout：

- [ ] T113-S3 封裝型式、pitch、焊盤尺寸（來源必須是 datasheet 機構圖）
- [ ] T113-S3 是否只有一組 TCON（決定 MIPI 與 RGB 能否並存）
- [ ] T113-S3 各電源軌的上電時序要求
- [ ] MIPI DSI 最高 lane rate 與支援解析度
- [ ] RGB 並列輸出的 pixel clock 上限
- [ ] IT66121 的 RGB 輸入時脈上限與電源需求
- [ ] 所有零件的 LCSC 料號、即時價、庫存、是否 Basic Part
