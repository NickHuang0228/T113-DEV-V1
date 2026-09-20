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

---

## 2026-09-19 · 機構圖確認:一個差點踩下去的陷阱

用 pymupdf 把 datasheet PDF p.88(紙本 p.78)render 成 600~700 dpi 圖片讀出來 ——
機構圖是向量圖,`pdftotext` 抽不到表格數字,只抽得到 CAUTION 那段文字。

### 陷阱:Exposed Pad 有六組選項,不是兩組

CAUTION 寫「use the second set of exposed pad size (D3/E3: 5.72 mm REF or 0.225 mm REF)」。
我原本以為機構圖上只有兩組,讀圖後發現有六組:

```
①  3.61 REF
②  5.72 REF          ← CAUTION 指定,正方形 5.72 × 5.72
③  8.00 REF
④  7.75 / 6.60 REF
⑤  5.60 / 5.20 REF
⑥  5.72 / 5.46 REF   ← ⚠ 也是 5.72 開頭,但是長方形
```

**只看到「5.72」就選,有 50% 機率拿到 ⑥ 的長方形,短邊差 0.26mm。**

分辨方法:CAUTION 的「5.72 mm REF **or** 0.225 mm REF」,`or` 連的是同一個值的
mm 與 inch 兩種寫法,不是兩個邊長。只有 ② 是單一值。

**這正是 ROADMAP 寫的「拿欄位字面值當實際幾何」那類坑的第三次** ——
原廠都標紅字了,但紅字本身還有一層歧義。

### 第二個發現:元件佔位是 16×16,不是 14×14

```
DS §2.12 寫「eLQFP128, 14 mm x 14 mm」  →  那是 D1/E1(本體)
D / E = 16.00mm                          →  含伸出來的腳
KiCad footprint 焊盤外緣                 →  16.80mm
```

placement 草圖上要畫 17×17mm 的佔位。差 2.8mm,在 100×100mm 的板子上不算小。

### 好消息:KiCad 內建件完全對得上

```
datasheet NOTE 8        REFERENCE DOCUMENT : JEDEC MS-026
KiCad LQFP-128_14x14mm_P0.4mm   descr: "JEDEC MS-026 variation BEE, 1.40mm body thickness"
```

body 14mm、pitch 0.4mm、128 腳、本體厚 1.40mm 四項全符。
焊盤 1.475 × 0.25mm,對照 datasheet b max 0.23、L nom 0.60,符合 IPC-7351。

**所以 footprint 不用從頭做,只要在標準件上自己加一個 5.72×5.72 的 EPAD。**
EPAD 與最內側訊號焊盤間隙 4.065mm,非常寬鬆。

### 方法筆記

**機構圖是向量圖,文字抽取拿不到表格。** 正確做法:

```python
import fitz
pg = doc[87]
pg.get_pixmap(dpi=700, clip=fitz.Rect(...)).save("crop.png")
```

分區裁切 + 高 dpi render,再用視覺讀。這條加進「抽出來的文字用來定位,不用來定案」那條規則的後面 ——
**定位靠文字,定案靠看圖。**

---

## 2026-09-19 · 周邊 IC 機構圖:三顆全部搞定,兩顆直接用 KiCad 標準件

### 先更正一個我自己的錯誤

前面記「IT66121 只有 8 頁公開簡版,無機構圖」—— **錯的**。

`file` 指令把頁數讀成 8,實際用 pymupdf 開起來是 **40 頁的完整版**,
`Figure 17. 64-pin QFN Package Dimensions` 就在最後一頁 p.40。

**教訓:`file -b` 對 PDF 的頁數判讀不可靠,要用 pymupdf 的 `doc.page_count`。**
這跟前面那條「定位靠文字,定案靠看圖」是同一類問題 —— 工具給的摘要不等於內容。

### IT66121FN (QFN-64)

```
D / E      8.90  9.00  9.10
D2 / E2    3.58  3.78  3.98     EPAD
e          0.50 BSC
b          0.18  0.25  0.30
L          0.30  0.40  0.50
```

KiCad `QFN-64-1EP_9x9mm_P0.5mm_EP3.8x3.8mm_ThermalVias` —— EPAD 3.8 vs 3.78,差 0.02,直接用。

### RTL8201F (QFN-32)

```
D / E      5.00 BSC
D2 / E2    3.10  3.35  3.60     EPAD
e          0.50 BSC
JEDEC MO-220
```

⚠ **這份 datasheet 涵蓋三種封裝**,查機構圖時極容易拿錯:

```
10.1  p.55   RTL8201F   QFN-32    ← 用這個
10.2  p.56   RTL8201FL  LQFP-48
10.3  p.57   RTL8201FN  QFN-48
```

**光看「RTL8201F」的檔名不夠,料號尾碼決定封裝。** 下單前 BOM 要核到尾碼。

KiCad 選 `QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias`,不選 EP3.45 ——
**EPAD 的 land 取略小於封裝標稱值比較安全**,取大的會往 max 3.60 靠,增加與週邊焊盤橋接的風險。

### 結論:只有 T113-S3 要自建 footprint

```
T113-S3    LQFP-128_14x14mm_P0.4mm  +  自加 EPAD 5.72x5.72
IT66121    QFN-64-1EP_9x9mm_P0.5mm_EP3.8x3.8mm_ThermalVias      直接用
RTL8201F   QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias      直接用
```

原本以為 footprint 是這塊板最大的風險(ROADMAP 風險 (1):錯了整批報廢),
查完發現 **三顆全部有 JEDEC 標準編號或標準件可對**,風險比預期低很多。

真正要小心的只剩兩件:T113 的 EPAD 選錯組別,以及 RTL8201F 拿錯封裝章節。
兩件都已寫進 008-footprint.md 的驗收清單。

---

## 2026-09-20 · 顯示鏈路查證:兩處文件錯誤、兩處規格錯誤、一條漏掉的電源軌

階段 0 剩下的「TCON 數量 / MIPI lane rate / RGB pixel clock 上限」查完了。
結果不只補上三個數字,還翻出五個問題。

### 1. 我自己的文件把 R 和 B 標反了

002-display.md v0.2 寫:

```
LCD0-D2 ~ D7    PD0 ~ PD5    R[7:2]      ✗
LCD0-D18 ~ D23  PD12 ~ PD17  B[7:2]      ✗
```

UM Table 5-2 (p.399) 明講 parallel RGB 是 **high-aligned**:

```
D23..D18 = R5..R0     D15..D10 = G5..G0     D7..D2 = B5..B0
```

套上 Table 4-3 的 PD bank 對應,正確答案是 **PD0~PD5 = B、PD12~PD17 = R**,
而且 bit 序也反了 —— PD0 是 B0(LSB),不是 MSB。

**但這個錯誤在接線時不會爆** —— 因為 IT66121 的輸入腳也叫 `D[23:0]`,
也是 high-aligned。按 D 編號 1:1 接就自動對。

所以規則是:**原理圖一律標 `LCD0-D` 編號,不標顏色名稱。**
用顏色名稱轉譯一次,就多一次 R/B 對調的機會。

### 2. 「T113-S3 沒有 RGB888」—— 也是我寫錯的

v0.2 斷言晶片只到 RGB666,依據是「D0/D1/D8/D9/D16/D17 在 PD bank 上不存在」。
前半句對,結論錯 —— 那 6 支在 **PB2~PB7 的 Function2**。

UM Table 5-2 有完整 RGB888 欄,Table 5-4 與 DS Table 5-18 註(5) 都寫 24-bit。

**T113-S3 支援 RGB888,是我們選擇不用。** 理由是 PB 在 VCC-IO 上,
那條軌掛著 microSD + SPI NOR + UART0 console,為了 1.2% 色深把 6 條
148MHz 的線拉進命脈 bank,不划算。

**「晶片做不到」和「我們不做」是兩回事,文件裡不能混。**

### 3. pixel clock 上限:grep 用錯關鍵字會整張表漏掉

找了半天沒找到 LCD 的時脈上限,一度寫進文件說「全志沒公布」。錯的。

```
DS §5.11.1 Table 5-18  DCLK cycle time  tDCLK  Min 5 ns   →  200 MHz
DS §5.11.2 Table 5-19  Pclk frequency          Max 148.5 MHz  ← 這是 CSI 輸入
```

兩張表連在一起。**搜 `MHz` 只會撞到 CSI 那張,因為 LCD 那張用 `ns` 表示。**

這是「抽出來的文字用來定位,不用來定案」的第四次命中,而且是新的一種:
前三次是抽取失真,**這次是搜尋關鍵字本身有偏差 —— 同一個物理量,兩張表用不同單位寫。**

以後查上限值,`MHz` 和 `ns`(還有 `Gbps` / `UI`)要一起搜。

結論:

```
T113-S3 TCON_LCD   200 MHz
IT66121            165 MHz     ← 瓶頸在這
1080p@60 需要      148.5 MHz   兩邊都過
```

### 4. 等長根本不是風險,ROADMAP 的定性要下修

有了 IT66121 的真實數字就能算了:

```
TS 1.5ns + TH 0.7ns,TPJ 2.0ns max     (IT66121 DS p.17)
148.5MHz → Tpixel 6.734 ns
6.734 − 1.5 − 0.7 = 4.53 ns
保守留 3.5ns 給 SoC skew + jitter → PCB 還有 ~1ns = 149mm
```

**100×100mm 的板子上,兩條走線差不到 149mm。** 等長在物理上不可能成為瓶頸。

ROADMAP 風險 ⑤ 原本寫「RGB 並列等長」,改成「RGB 並列的 SSO noise」——
地彈會直接吃掉 IT66121 那 2.0ns 的 jitter 預算,那才是 148.5MHz 下會出事的路徑。

### 5. ⚠ 最嚴重的一項:IT66121 要 1.2V,規格書漏了兩個版本

```
IVDD12  pin 8,35,56   核心邏輯
PVCC12  pin 18        HDMI PLL        "should be regulated"
AVCC12  pin 23        類比前端        "should be regulated"
DVDD12  pin 28        數位前端
VCCNOISE              Max 100 mVpp
```

**全板電源域從 4 組變 5 組。** 如果沒查出來,板子回來才發現 IT66121 少一條電源軌 ——
那是要飛線的等級。

對照組:RTL8201F 有內建 1.1V LDO,只吃 3.3V,而且 datasheet 明講外部核心電源
「not suggested,internal regulators cannot be disabled」。

**同樣是周邊 IC,一顆自帶 LDO,一顆沒有。**
教訓:每顆 IC 都要開 Power/Ground Pins 那一頁逐腳看,不能假設「3.3V 單軌」。
這條加進 ROADMAP 風險 ⑦。

### 6. 順手抓到:T113-S3 沒有 GPU,也沒有 RISC-V C906

SPEC 寫 `GPU Mali-G31 MP2` 和 `RISC-V C906 @1.0GHz`。
DS + UM 兩份文件搜 `Mali` / `GPU` / `OpenGL` / `Vulkan` / `RISC-V` / `C906` —— **零命中**。

```
DS §1 p.3    "integrates dual-core Cortex-A7 CPU and single-core HiFi4 DSP"
DS §2.1 p.3  "Dual-core ARM Cortex-A7"  —— 就這一行
DS 方塊圖 p.20  只有 DE / DI / G2D,沒有 3D 引擎
```

這兩項是從同門晶片抄來的(D1/D1s 有 C906,A133/T507 有 Mali-G31)。

**後果是驗收標準要改**:沒有 GPU 代表顯示堆疊只有 framebuffer/DRM-KMS + G2D,
沒有 OpenGL ES。「HDMI 出畫面」= 測試圖樣或影片解碼,**不是桌面環境**。

另外 datasheet 全文搜 `GHz` 零命中 —— `@1.2GHz` 也是市場資料,不是規格書數字。

### 7. 附帶收掉的三個待決事項

```
VCC-PE  → 3.3V   RTL8201F 數位 IO 只吃 DVDD33,無獨立 VDDIO,1.8V 過不了 VIH
VCC-PD  → 3.3V   IT66121 的 OVDD 三種電壓皆可,不構成限制
                 MIPI D-PHY 吃 VCC-LVDS(pin 65,MangoPi 標 "LVDS1.8")而非 VCC-PD
VCC-PG  → 3.3V   v0.2 已定
```

**全板 IO 單一 3.3V 電平,不需要任何電平轉換。**

VCC-PD 那一條的推論(D-PHY 吃 VCC-LVDS)datasheet 沒有明文,
依據是「整顆晶片的電源腳裡沒有任何 DSI 專用軌」的排除法 ——
已留在 001-power.md §2.2.2 的待確認清單,要找一份真的接 DSI 面板的參考設計核對。

### 方法筆記

這次五個問題裡,**三個是我自己先前寫錯的**(R/B 標反、RGB888 斷言、「沒公布上限」),
兩個是抄來的規格沒查證(GPU、C906)。

共同點:**都是「看起來已經確認過」的欄位。** 打了勾的項目沒有再被質疑。

規則補一條:**驗收清單上的 `[x]` 要標出處頁碼。** 沒有頁碼的勾等於沒查。
這次能抓出來,是因為為了查 TCON 又把 §5 和 §2.6 重讀了一遍。

---

## 2026-09-20 · 橋接晶片換人:IT66121 停產,改 ADV7511 —— 順帶把選型判準整個換掉

### 起因是查料,結果是改設計

階段 0 最後一項「零件料號逐項查證」,本來以為只是填價格。
查到第二顆就卡住:

```
IT66121FN  C2684803  庫存 0  "This product is no longer manufactured."
```

**如果只看 `stockCount == 0`,會以為是缺貨,等補貨就好。**
是 `noBuyReason` 那句話把它從「等一週」變成「重畫原理圖」。

```
規則:查料況要看停產標記,不是只看庫存數字。
```

### 找替代品的過程中,判準自己變了

盤點並列 RGB 輸入 + 有貨 + 有 mainline driver 的候選,只剩兩顆,外加一顆沒 driver 的。
我照原本的判準(002-display.md §3.1:「第一塊板不在 driver 上冒險」)推薦了 **TFP410**
—— 最便宜、電源最簡單、driver 最省事。

然後 Nick 丟了一份職缺過來。我以為是 bootloader(網址的 query 是 bootloader),
抓下來一看是 **HDMI軟韌體工程師(竹北)**:

```
1. HDMI and DP Linux/Android Kernel driver porting
2. HDMI and DP IC 驗證
3. 相關產品客戶 support
```

**判準整個倒過來。** 原本是「driver 越省事越好」,現在是「driver 工作就是要練的東西」。

在新判準下 TFP410 從第一名變最後一名:

```
TFP410   DVI serializer,連 I2C 都沒有,只有一支 power-down GPIO
         ti-tfp410.c 的「porting」約等於寫 20 行 DTS
         沒有 audio / InfoFrame / HDCP / CEC → HDMI 協定層幾乎空白
```

改選 **ADV7511**:完整 HDMI、mainline `adv7511/`、驗證面涵蓋
EDID/HPD/HDCP/audio(N,CTS)/InfoFrame/CEC/CSC。

**這件事本身是個教訓:選型判準不是永久的,目標變了判準就要重審。**
我差一點就用一條已經失效的判準,做了一個對新目標最差的選擇。

### 查到這條路走得通

```c
// drivers/gpu/drm/sun4i/sun4i_rgb.c
drm_of_find_panel_or_bridge(tcon->dev->of_node, 1, 0, &rgb->panel, &rgb->bridge);
drm_bridge_attach(encoder, rgb->bridge, NULL, 0);
```

sunxi TCON 的並列 RGB 輸出**原生支援掛外部 drm_bridge**,所以 porting 有骨架。
而且 mainline 的 `adv7511/` 目錄同時含 **adv7533/35(MIPI DSI→HDMI)**——
這塊板本來就有 DSI,同一份 codebase 能練兩條輸入路徑。

### 換料的連鎖反應比預期多

一顆晶片換掉,動了七份文件:

```
電源域     5 組 → 4 組      1.2V 取消(那是 IT66121 要的)
1.8V LDO   XC6206 → AP2112K  ADV7511 的 1.8V 吃 180mA,XC6206 只有 200mA 不夠
1.8V 分域  新增要求          ADI 要求四個 1.8V 域分成 3 組各加 LC 濾波
封裝       QFN-64 9×9 → LQFP-100 14×14   佔位從 9mm 級跳到 16mm 級
placement  要重畫            板上變成兩顆 14mm 見方的晶片
footprint  008 §4 作廢       ADV7511 機構圖還沒拿到
PCBA 片數  3 → 2            這是 T113 實價 $22.25 逼的,不是換料逼的
```

**`1.8V LDO 從 XC6206 換成 AP2112K` 這條特別值得記**:
v0.3 才寫過「多一顆 $0.05 的 XC6206 換掉一個未知數」,現在那顆容量不夠。
**負載變了,已經選好的元件也要重算 —— 不能因為上一版定案就沿用。**

### 刻意沒做的事:沒有填 ADV7511 的機構圖數字

ADI 官網的 PDF 對 curl 和 WebFetch 全部回 **HTTP 000**(連線被擋),
package outline 和 datasheet 都抓不到。

我可以從產品頁、LCSC 規格欄、經銷商頁面湊出「LQFP-100 14×14, pitch 0.5」,
但 **ROADMAP 風險 ① 寫得很清楚:footprint 一律回原廠機構圖,不信任二手來源。**

T113-S3 的 EPAD 就是靠讀原始機構圖才躲掉「六組尺寸選錯」那個坑。
ADV7511 沒有理由用比較鬆的標準。所以 008 §4A **刻意留白**,只寫待辦。

```
[ ] 手動下載 ADV7511 datasheet → docs/reference/peripherals/
    要的是:package outline(含 EPAD 尺寸)+ Video Input AC Timing(tSU/tHD/jitter)
```

同理,002-display.md 的 skew budget 還掛著 IT66121 的 TS=1.5ns/TH=0.7ns,
已標註「待換 ADV7511 數字重算」。結論(等長不是瓶頸)預期不變,
但**算式不能沿用別顆晶片的規格** —— 那正是這個月稍早才抓到的同一類錯誤。

### 兩個要誠實承認的退步

```
1. 008-footprint.md v0.2 的結論「三顆全部有標準件可對,風險比預期低很多」
   暫時收回。ADV7511 的機構圖還沒拿到。

2. ROADMAP §2.1 用「$8 —— 便宜到可以買備品」當選型理由。
   T113-S3 實價 $22.25,那條理由不成立。
   選型結論不變(內建 DDR3 仍是決定性優勢),但論述要改。
```

### DP 的缺口

職缺寫 HDMI **and** DP。這塊板三個方案都給不了 DP —— T113-S3 沒有 DP 輸出。
ROADMAP §6 的第 3 塊板(高速差分/DP)從「構想」升級為明確的下一步,
而且重點要從純 layout 練習往「能跑 DP driver、能做 DP 驗證」偏移 ——
純被動轉接板量得到訊號,但沒有 driver 可寫。
