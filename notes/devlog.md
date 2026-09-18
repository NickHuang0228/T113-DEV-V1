# 開發日誌

---

## 2026-09-18 · 專案成立與選型定案

### 起點

ESP32S3-DEV-V1 已下單、已 bring-up、WiFi 壓力測試通過（10,000 包 × 250 bytes × 5 輪，
無 brownout、無重開、PSRAM 完好）。那塊板驗證了 9 條設計假設，KiCad 全流程走完一遍。

下一塊要往上走一階：**從「模組 + 單電壓 + 1 對差分」跳到「裸 SoC + 4 組電壓 + 13 對差分 + Linux」。**

### 選型過程

繞了很大一圈。依序考慮過：

```
Gowin GW2AR-18 (FPGA)  → 沒有硬體 D-PHY，且方向是 HDL 不是 Linux
Allwinner H3           → 查 datasheet 第 59-60 頁後否決（見下）
F1C200s                → 太弱，只能推 800×480
RK3566 / RK3568        → DDR4 layout 對第一塊 Linux 板太重
RK3588                 → BGA ~1100 ball / 0.65mm / 12~16 層 HDI，個人畫不了
Lattice CrossLink-NX   → 能做 DSC + 2-port，但要寫數週 Verilog
T113-S3                → 選定
```

### H3 為什麼出局（實際查證）

一度是首選：有完整開源 KiCad 參考設計、原生 4K@30 HDMI。
用 Read 工具讀 `Allwinner_H3_Datasheet_V1.2.pdf` 第 58–60 頁後確認：

```
2.1.5.2 Display Output
  • Total two display interfaces available      ← 總共就兩個
  • Two interfaces may be active in parallel
      - HDMI V1.4 output with HDCP1.2, up to 4K@30fps
      - TV CVBS output
```

**沒有 RGB 並列、沒有 LVDS、沒有 MIPI DSI。**
H3 是機上盒晶片，面板介面被省掉了。長期目標是 DSI，這條路不通往那裡。

（第一次嘗試用 zlib 抽 PDF 文字失敗，抽出 0 chars；改用 Read 工具直接讀頁面圖片才拿到。
同樣的 zlib 方法對 T113 datasheet 是有效的 —— 不同 PDF 產生器，方法要換。）

### 為什麼是 T113-S3

```
內建 128MB DDR3（SIP）   第一塊 Linux 板最大的風險直接刪除
QFP128                   腳位露在外面，可目視、可量測、焊橋自己修
有 MIPI DSI              長期目標的必要條件
$8                       便宜到可以買備品
```

**BGA 出問題只能靠 X-ray 或報廢，QFP 可以自己救。** 第一塊 Linux 板選可觀測性。

### HDMI 走 bridge 的決定

T113-S3 沒有原生 HDMI，用 IT66121 把 RGB 並列轉 HDMI。
一開始覺得是缺點，後來認為是加分：**多學一個介面**（24 條 RGB 並列等長），
那是「並列高速匯流排」的入門，和 DDR、和 MIPI bridge 是同一種技能。

選 IT66121 而不是 LT8618SX：`drivers/gpu/drm/bridge/ite-it66121.c` 在 mainline 就有。
**第一塊板不在 driver 上冒險。**

### 網路：選乙太不選 WiFi

決定性理由不是「有網路」，是 **U-Boot 階段沒有 WiFi，拿不到 TFTP + NFS 開機**。

```
沒網路   改 kernel → 編譯 → 燒 SD 卡 → 插回 → 開機    每次 3~5 分鐘
有乙太   改 kernel → 編譯 → TFTP 抓 → 開機            每次 20 秒
```

要無線就插 USB WiFi dongle，零 layout 成本零風險。

### Type-C：供電 + FEL 燒錄

```
CC1/CC2 各 5.1kΩ 下拉，標準 sink 取 5V，不用 PD
峰值估 ~900mA @5V = 4.5W，Type-C 15W 餘裕三倍
```

新學到的：全志的 **FEL 模式**。BROM 找不到啟動裝置就進 USB 下載模式，
`sunxi-fel version` 有回應 = 電源 + 時脈 + BROM + USB 差分全部正常 ——
**這會是 bring-up 第一天最有價值的一條訊息**，比 UART log 更早能拿到。

另外決定板上放 CH340N 接 UART0，多花 $0.8 換掉一個接觸不良的誤判來源。

### USB 這次不一樣

```
上一塊板  USB FS  12 Mbps   上升時間 4 ns    臨界長度 94mm  → 隨便走都能動
這塊板    USB HS 480 Mbps   上升時間 500 ps  臨界長度 12mm  → 必須控阻抗
```

FEL 燒錄會跑滿 High Speed，差分品質這次真的會影響結果。

### 成本

```
零件 + PCB 4層5片 + PCBA 2片 + 運費 ≈ $154 ≈ NT$4,960
```

刻意排除：eMMC、USB Hub、WiFi 模組、MIPI CSI、PMIC。
**第一塊 Linux 板的成功標準是「開機」，不是「功能齊全」。**

### 下一步

```
[ ] 讀 T113-S3 datasheet：封裝機構圖、上電時序、TCON 數量、時脈上限
[ ] 零件料號逐項查 LCSC（即時價、庫存、Basic/Extended）
[ ] 開 KiCad 專案，建 T113-S3 符號
```
