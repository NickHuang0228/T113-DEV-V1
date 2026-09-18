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

### WiFi：畫但不焊

算完成本才發現，**硬體只多 NT$550，貴的是另外兩項**：

```
① PCB 面積   模組 + RF keep-out 約吃掉 30×20mm
             超過 100×100mm 的話 PCB 從 $20 跳到 $35~50
             天線下方挖空還會切斷 GND 平面，可能影響旁邊差分的回流

② driver     全志 BSP（5.4/Tina）要 out-of-tree driver，版本被綁死
             mainline 6.x 的 rtw88 已有 SDIO 支援，但外設完整度不如 BSP
             第一塊板走 BSP → WiFi 落在高風險那格
```

結論：**footprint、SDIO 走線、天線區、匹配網路全部畫出來，但 BOM 不列 → 不上件 → $0。**

對「學 layout」這個目標，畫出來就練到了。最有價值的一項是
「如何在挖空 GND 的同時不破壞旁邊差分的回流」—— 那是真正的取捨題，不是照抄規則能解的。

要無線就插 USB dongle，零 layout 成本零風險。

### 組裝：貼 1 片 + 自焊 2 片

原本打算全部交給 JLCPCB，算完三種配置後改成混合：

```
全貼 2 片                $91
貼 1 片 + 自焊 2 片      $126 ≈ NT$4,060   ← 採用
全自焊                   $116 ≈ NT$3,740
```

**中間那個最貴，但選它。** 理由不是錢，是除錯：

```
JLCPCB 貼片   焊接品質穩定  →  不開機 = 設計問題
自己手焊      焊接品質未知  →  不開機 = 設計問題？還是虛焊？
```

128 隻腳裡一隻虛焊，症狀可能是「開機了但 USB 不通」或「跑十分鐘後當機」，
那種間歇性故障會吃掉好幾天。**先有一片確定焊得好的板子當黃金參考。**

零件另外從 LCSC 買（JLCPCB 不退剩料），**兩邊同屬嘉立創，訂單可合併運費**。

### 工具：好烙鐵 > 熱風槍 > 加熱台

查了一輪，優先順序跟直覺不同：

```
烙鐵      拖焊、清橋、補線、改線 —— 實際使用時間比熱風槍多十倍
熱風槍    不可取代：只有它能拆件。第一次焊自己的板子一定會要拆要修
加熱台    先別買
```

**加熱台有個容易忽略的限制 —— 面積**：

```
MHP30    30×30mm    只能焊小模組
MHP50    50×50mm    仍小於板子
板子     100×100mm
```

要整片回流 100×100mm 得買大面積加熱台（NT$3,000~4,000）或 T-962 回流爐（NT$6,000）。
對照 JLCPCB 貼一片 ≈ NT$1,450 —— 除非要做很多塊板，否則不划算。

另外確認：**QFN 其實該交給 SMT**。底部散熱焊盤需要「加熱台預熱 + 上方熱風」才好處理，
只用熱風槍會吹很久、烤焦板子、吹跑旁邊的 0402。這也是「至少貼 1 片」的理由之一。

鋼網 $8 是自焊方案裡 CP 值最高的一筆 —— 0.4mm pitch 手工上錫膏不可能均勻。

### 下一步

```
[ ] 讀 T113-S3 datasheet：封裝機構圖、上電時序、TCON 數量、時脈上限
[ ] 零件料號逐項查 LCSC（即時價、庫存、Basic/Extended）
[ ] 開 KiCad 專案，建 T113-S3 符號
```

---

## 2026-09-18 · datasheet 讀完第一輪：五個假設被推翻

取得資料：T113-S3 datasheet v1.6（98 頁）、User Manual v1.1/v1.3、MangoPi MQ-R 原理圖、
RTL8201F/CH340/IT66121 datasheet。全部放 `docs/reference/`，來源記在該目錄 README。

### 被推翻的五個假設

```
① 核心電壓 1.1V        →  實際 0.9V   (DS Table 5-2 p.45)         超壓 22%
② 電源樹沒有 1.5V      →  VCC-DRAM 要外部供 1.5V                   內建 DDR3 仍要供電
③ IT66121 是 LQFP64    →  QFN64 9×9 + 底部 GND pad                 手焊高風險
④ RGB 是 24-bit 28 條  →  RGB666 18-bit 22 條 (DS Table 4-3)       HDMI 只有 26 萬色
⑤ MIPI 與 RGB dts 二選一 →  共用同一組實體接腳 PD0~PD9              硬體衝突，不是軟體問題
```

**每一項都是「看起來很合理所以沒查」的東西。** 這一輪最大的教訓不是任何單一數字，
是「合理」不等於「查證過」。

### ⑤ 是最貴的一個

```
DS Table 4-3 Pin Multiplexing:
PD0   LCD0-D2    LVDS0-V0P   DSI-D0P
PD1   LCD0-D3    LVDS0-V0N   DSI-D0N
...
PD9   LCD0-D13   LVDS0-V3N   DSI-D3N
```

MIPI 用 PD0~PD9，RGB 用 PD0~PD21。**前 10 支完全重疊。**

軟體切 mux 切不掉電氣負載 —— 跑 MIPI 時 IT66121 的輸入電容永遠掛在 1Gbps 差分線上，
而 002-display.md §2.1 自己寫過「MIPI 不能有 stub」。

**解法：PD0~PD9 用 10 顆 0Ω 隔離，MIPI 直通、IT66121 走分支，0Ω 貼著分支點放（≤0.5mm）。**
IT66121 照樣上件，只是輸入被 0Ω 斷開，切換時拆焊 0402 很容易。

專案優先序定案：**MIPI DSI > RGB/HDMI**。理由除了長期目標是 DSI，
還有 MIPI 支援 RGB888 而 RGB 並列只有 RGB666。

### EPAD：這顆晶片唯一的數位地

```
128 隻腳：I/O 102 + NC 1 + Power 21 + Ground 1 + DDR Power 3
                                          ↑
                                  ball 25 = AGND（類比地）
```

**沒有任何數位 GND 腳。** 21 支電源的回流全走 EPAD。

三種失敗（沒焊 / 焊一半 / 錫太多把晶片墊高）都無法目視檢查。
→ 組裝策略從「貼 1 片 + 自焊 2 片」改成 **「部分貼裝」：只讓 JLCPCB 貼
T113 / IT66121 / RTL8201F 三顆，其餘自焊**。

算完發現**這樣反而便宜**：JLCPCB 的 PCBA 費用幾乎全在 Extended part 上料費 $3.07/種，
跟貼幾片、幾個焊點關係很小。

```
只貼 3 顆 IC  →  3 種 × $3.07 = $9.21
全部零件      → ~12 種 × $3.07 = $36.84
多貼 2 片的焊點成本 = 227 × 2 × $0.0016 = $0.73     ← 可忽略
```

總成本 $154 → **$122**。代價是鋼網用不上了（IC 貼好後鋼網壓不平），
80 顆被動件 ×3 片要烙鐵手焊 → **被動件改 0603**。

### 上電時序比想像簡單

```
T1 > 2 ms     VCC-IO 早於 VDD-SYS / VDD-CORE
T2 > 64 ms    RESET 拉低延遲
關機          "No special restrictions for other power rails."   完全不用設計
```

不需要 sequencer IC，EN 鏈就夠。**但 RESET 的 64ms 不照抄 MangoPi** ——
它只有 10K 上拉沒有 supervisor，64ms 八成是靠 DC-DC soft-start 湊的。

### 方法論：排除法會失手

查「VDD18-DRAM 從哪來」時我先用排除法：板上只有 RY1303 三路（3.3/1.5/0.9）+ 內建 LDO，
所以 1.8V 只可能來自 LDOA。

**錯了。** 搜元件型號發現 MangoPi 另外放了 `XC6206-1.8V` / `XC6206-2.8` / `XC6206-1.2`。

排除法的前提是「窮舉完整」，而我的窮舉漏了外部 LDO。
**教訓：用排除法之前，先確認你真的數完了。** 搜元件型號字串比看電源方塊圖可靠。

結論反而更保守也更好：**保留一組外部 1.8V**，不要全押 LDOA 的 260mA
（VDD18-DRAM / AVCC / VCC-TVIN 三項在 datasheet 都是 TBD，算不出來的東西不要賭）。

### datasheet 的缺口

```
VDD-CORE / VDD-SYS / VCC-DRAM 的電流  全部 TBD
Table 5-2 的 Max 欄位                 大半 TBD
```

全志沒填。0.9V 那組的電流只能估算或從參考設計反推。

好消息：θJA = 20.36 °C/W、Tj max = 110°C → 1.5W @45°C 環境 Tj 只有 75.5°C。
**熱不是這塊板的風險，不需要散熱片。**

### 工具筆記

`pdftotext -layout` 對 T113 datasheet 有效（比 zlib 好用），但：

```
Table 4-2 Pin Characteristics    ball# 與 pin name 完全對不上   不可用
Table 5-2 Operating Conditions   min/typ/max 欄位跑位          數字可用但要核對
Table 4-3 Pin Multiplexing       ✓ 抽得很乾淨                   可用
原理圖 PDF                        網路標籤與腳位對應會飄         只能當線索
```

**規則：抽出來的文字用來「定位」，不用來「定案」。**

### 下一步

```
[ ] p.78 機構圖六個數字（pitch / b / L / D,E / D3,E3）—— 有原廠 CAUTION 要用第二組 D3/E3
[ ] p.77 Pin Map 目視：VCC-LVDS 腳位、pin 50 VDD18-DRAM 接哪
[ ] LCSC 料況：RY1303 / T113 / IT66121 / RTL8201F
[ ] 腳位分配（pin map）→ docs/design/007-pinmap.md
```

---

## 2026-09-19 · CSI 出局：它跟乙太網路搶同一組腳

查 `DS §2.7.1 p.7` 與 `Table 4-3 Pin Multiplexing` 後確認兩件事：

**① T113-S3 沒有 MIPI CSI，只有 8-bit Parallel CSI（DVP）**

`§2.7 Video Input` 底下只有 `2.7.1 Parallel CSI` 和 `2.7.2 CVBS IN`。
腳位表裡只有一組 `NCSI0-*`，沒有 NCSI1，沒有任何 MIPI CSI 訊號名。

SPEC §8 原本寫「MIPI CSI 留到 V2」——**這顆根本沒有 MIPI CSI**，已更正。

**② CSI 與 RMII 在 PE0~PE9 完全重疊**

```
PE0   NCSI0-HSYNC   ...  RMII-CRS-DV
PE1   NCSI0-VSYNC   ...  RMII-RXD0
PE2   NCSI0-PCLK    ...  RMII-RXD1
PE3   NCSI0-MCLK    ...  RMII-REF-CLK
PE4   NCSI0-D0      ...  RMII-TXD0
PE5   NCSI0-D1      ...  RMII-TXD1
PE6   NCSI0-D2      ...  RMII-TX-EN
PE8   NCSI0-D4      ...  MDC
PE9   NCSI0-D5      ...  MDIO
```

MangoPi 的網路名直接叫 `VCC-RMII-CSI` —— 他們也知道。MQ-R 沒有乙太網路所以不衝突。

### 這塊板總共有兩組腳位衝突

```
A   HDMI(RGB) ↔ MIPI DSI     PD0~PD9    → 0Ω 隔離，MIPI 直通（002-display.md §1）
B   CSI       ↔ 乙太(RMII)    PE0~PE9    → 不解，直接砍掉 CSI
```

### 決定：CSI 完全不畫，攝影機走 USB UVC

乙太網路不是附加功能，是開發循環的核心（U-Boot 階段沒有 WiFi，
TFTP+NFS 讓改一次 kernel 從 3~5 分鐘縮到 20 秒）。拿它換攝影機是虧的。

```
USB UVC   mainline uvcvideo 完全支援
          USB 2.0 HS 480Mbps，720p MJPEG 綽綽有餘
          layout 成本 $0，本來就有 USB-A Host
```

**這是第三次用同一招了**：WiFi 模組 → USB dongle、攝影機 → USB UVC。
模式是：**當一個功能要吃掉稀缺的腳位或帶來 layout/driver 風險，
而 USB 上有成熟的替代品時，就走 USB。**

連帶好處：PE bank 現在只要服務 RMII，pin map 少一組衝突要解，PE10~PE13 可當 GPIO。

### 差異：兩組衝突的處理方式不同，因為速度差 20 倍

```
MIPI      1 Gbps 差分        上升時間 ~200ps   臨界長度 ~5mm    → stub ≤0.5mm，必須 0Ω
CSI/RMII  50~148MHz 單端 CMOS 上升時間 ~1~2ns  臨界長度 ~25~50mm → 其實容忍度高
```

CSI 那組技術上可以用 0Ω 解（而且比 MIPI 那組容易），**但沒必要** ——
用 USB 換掉整條線路比畫一組永遠不焊的走線划算。

---

## 2026-09-19 · WiFi footprint 也砍掉：一個永遠不焊的模組不該吃掉最安全的 bank

做完 bank 分析後推翻 v0.1 的「WiFi 畫但不焊」決定。

### 起因：排針只剩 4 支 GPIO

算 pin map 時發現 SPEC 寫的「GPIO ×20 排針」根本放不下：

```
PB / PC / PF   VCC-IO   SD 開機 + NOR 開機 + UART log   一燒就變磚
PD             VCC-PD   MIPI + HDMI                     顯示全失
PE             VCC-PE   RMII                            開發循環沒了
PG             VCC-PG   ★ 唯一「燒了也不痛」的 bank
```

排針必須放 PG，別無選擇。而 PG 只有 16 支，WiFi 的 SDIO1 佔掉 PG0~PG5：

```
16 − 6(WiFi) − 4(I2C×2) − 2(UART) = 4 支純 GPIO
```

**一個永遠不焊的模組，吃掉板上最安全 bank 的 37%。** 這筆帳 v0.1 完全沒算。

### 移除後

```
+ 排針純 GPIO    4 → 10 支
+ 板面積         省 30 × 20 mm（更容易守住 100×100mm 的價格斷點）
+ GND 平面完整   天線區挖空消失
+ VCC-PG 自由    不再被 SDIO 綁住 → 定為 3.3V
+ layout 工時    少畫 6 條 SDIO + 匹配網路 + keep-out
− RF layout      練不到
```

### 為什麼願意放棄 RF layout 這個學習目標

v0.1 的理由是「畫出來就練到 RF layout，不上件所以 $0」。
那句話只算了**金錢成本**，沒算**腳位成本與面積成本**。

而且 RF layout 可以留到專用的練習板 ——
**不需要綁在第一塊 Linux 板上一起冒險。**
第三塊板本來就規劃了高速差分轉接／探測板，RF 併進去更合適。

### 這是第三次用同一招

```
WiFi 模組      → USB dongle
攝影機 CSI     → USB UVC
WiFi footprint → 完全移除，USB dongle
```

**模式：當一個功能要吃掉稀缺腳位、或帶來 layout/driver 風險，
而 USB 上有成熟替代品時，就走 USB。**

⚠ 代價是 **USB 現在同時扛 FEL 燒錄、WiFi dongle、UVC 攝影機三個角色**。
USB-A Host 那條 HS 差分（480Mbps）的品質，比原本規劃「只插個鍵鼠」時重要得多。

### 排針最終規格

```
28 pin (2×14)
  GPIO ×10       PG0~PG6, PG11, PG12, PG14      隨時可用
  I2C  ×2        PG7/PG8 (TWI2)、PG9/PG10 (TWI1) 隨時可用
  UART 備援 ×1   PG13/PG15 (UART1)               隨時可用
  SPI  ×1        PD10~PD13 (SPI1)                ⚠ 僅 MIPI 模式
  電源/地 ×8
限流電阻 20 顆 0603（I2C 100Ω ×4，其餘 330Ω ×16）
```

**PG bank 意外地好用：有四組完整 I2C（TWI0~TWI3）和五組 UART。
但完全沒有 SPI mux** —— 所以排針的 SPI 只能從 PD 的 SPI1 借，且跑 HDMI 時會消失。
（SPI0 在 PC bank，是 SPI NOR 備援開機裝置，絕對不能對外。）
