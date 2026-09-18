# 004 · USB、Type-C 與燒錄

---

## 1. 接口配置

| 接口 | 用途 | 差分 | 供電 |
|---|---|---|---|
| **Type-C #1** | OTG + FEL 燒錄 | 1 對 USB HS | ✓ 5V 進 |
| **Type-C #2** | CH340N → UART0 log | — | ✓ 5V 進 |
| **USB-A** | Host（WiFi dongle / 鍵鼠） | 1 對 USB HS | 5V 出（限流） |

兩個 Type-C 都能供電，插哪個都能開機。

---

## 2. Type-C 供電

```
CC1 ──[5.1kΩ]── GND
CC2 ──[5.1kΩ]── GND
```

**標準 Type-C sink，取 5V。不使用 PD。**

理由：整板峰值 ~900mA @5V = 4.5W，Type-C 5V/3A = 15W，餘裕三倍。
PD controller 是要 9V/12V 才用得上的東西，多一顆料多一份風險。

⚠ **兩個 CC 腳都要接 5.1k** —— Type-C 可正反插，插反了只有另一個 CC 在作用。
（這點上一塊板已經做過，直接複用。）

### 實際可取電流取決於電源端

```
標準 Type-C 充電器      可到 3A
USB-A 轉 C 線接電腦     可能只有 500mA
```

USB-A Host 的 5V 要加**限流開關**（如 TPS2051），過流時只斷 Host，不影響主板。

---

## 3. FEL 模式 —— 全志的 USB 下載機制

```
BROM 開機時找不到有效啟動裝置（或按住 FEL 鍵）
  → 自動進入 USB FEL 模式
  → PC 端用 sunxi-fel 工具直接操作
```

### 能做什麼

```bash
sunxi-fel version                    # 讀晶片 ID
sunxi-fel spl u-boot-spl.bin         # 把 SPL 載進 SRAM 執行
sunxi-fel write 0x40000000 file.bin  # 寫任意記憶體位址
sunxi-fel exe 0x40000000             # 從指定位址執行
sunxi-fel spiflash-write 0 u-boot.bin # 燒 SPI NOR
```

### 為什麼 FEL 對 bring-up 極有價值

```
sunxi-fel version 有回應
  = 電源正常 + 時脈正常 + BROM 跑起來 + USB 差分通
```

**這是 bring-up 第一天最有價值的一條訊息**，比 UART log 更早能拿到 ——
因為它不需要 SPL、不需要 DDR、不需要任何自己寫的程式碼跑起來。

如果 `sunxi-fel version` 沒反應，問題範圍立刻縮到：電源、晶振、USB 差分、FEL 按鍵。

---

## 4. 燒錄與開發流程

```
第一次上電    FEL 確認晶片活著        sunxi-fel version
              FEL 載入 SPL 測試        sunxi-fel spl u-boot-spl.bin

日常開機      microSD                  dd image 進卡，插上開機

快速迭代      U-Boot TFTP 抓 kernel
              rootfs 用 NFS 掛         ← 見 003-network.md

量產／備援    SPI NOR                  sunxi-fel spiflash-write
```

**SD 卡是主力，FEL 是診斷工具，SPI NOR 是備援。** 三條路互相獨立，一條不通還有另外兩條。

---

## 5. UART log —— 生命線

### 為什麼板上要放 CH340N

| 做法 | 成本 | 說明 |
|---|---|---|
| **板上 CH340N + Type-C #2** | +$0.8 | 一條線就有 log |
| UART 走排針 + 外接 USB-TTL | $0 | 每次要接杜邦線，多一個接觸不良的環節 |

第一塊 Linux 板會盯著 UART log 看幾十個小時。**$0.8 買掉一個誤判來源，很值。**

### 電路

```
T113-S3 UART0_TX ──▶ CH340N RXD
T113-S3 UART0_RX ◀── CH340N TXD
CH340N ──USB──▶ Type-C #2
```

⚠ **UART 排針也要留**，作為 CH340N 失效時的備援。成本只有 3 支排針。

### 常用鮑率

```
115200 8N1    U-Boot 與 kernel 預設
```

---

## 6. USB 2.0 差分 layout

這塊板的 USB 跑 **High Speed 480 Mbps**，不是上一塊板的 Full Speed 12 Mbps。

```
上一塊板  USB FS 12 Mbps
          上升時間 4 ns → 臨界長度 94mm
          → 短走線幾乎不用管阻抗

這塊板    USB HS 480 Mbps
          上升時間約 500 ps → 臨界長度約 12mm
          → 必須控阻抗
```

**FEL 燒錄會跑滿 High Speed**，差分品質這次真的會影響結果。

### 規則

```
阻抗      90Ω 差分
對內等長  ±0.15mm
走線      最短最直，優先走表層，盡量不換層
參考層    全程完整 GND，不跨分割
ESD       每條資料線加 ESD 保護，電容 <1pF
共模扼流圈 可選，有助 EMI，但會影響訊號品質，V1 先留位置不放件
```

---

## 7. 按鍵

```
FEL      按住開機進入 FEL 模式（接到 datasheet 指定的 strap pin）
RESET    接 SoC 的 nRESET
電源     可選；直接插 Type-C 即開機也可以
```

⚠ FEL 按鍵接哪一支腳**必須查 datasheet**，各晶片不同。列在 SPEC 的待確認清單。

---

## 8. 驗收

```
[ ] 兩個 Type-C 的 CC1/CC2 各接 5.1kΩ 下拉
[ ] USB HS 差分 90Ω，對內等長 ±0.15mm，不跨分割
[ ] USB 資料線 ESD 保護已放，電容 <1pF
[ ] USB-A Host 的 5V 有限流開關
[ ] CH340N 接到 UART0，且 UART 排針備援已留
[ ] FEL 按鍵接到 datasheet 指定的 strap pin
[ ] RESET 按鍵與上拉電阻
```

bring-up 驗證順序：

```
1. 插 Type-C #1，量 VBUS 有 5V
2. sunxi-fel version            ← 最重要的第一個里程碑
3. 插 Type-C #2，PC 認到 COM port
4. 開機看 UART 有沒有 BROM / SPL 輸出
5. sunxi-fel spl u-boot-spl.bin 測試 SPL 能否執行
6. SD 卡開機到 U-Boot
7. USB-A 插隨身碟，確認 Host 可用
```
