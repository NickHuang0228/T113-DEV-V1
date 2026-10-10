# 013 · 原理圖收尾階段的決定

版本：v1.0 · 2026-10-10

這份記錄「把剩下八張子圖紙畫完」時被迫做出的決定。
每一條都是前面文件留下的待確認項，或是畫圖時才浮現的衝突。

格式統一為：**問題 → 選了什麼 → 理由 → 代價**。
「代價」那一欄最重要 —— 沒有代價的決定通常是沒想清楚。

---

## 1. BOOT-SEL 怎麼接（解掉 007 §5.3）

**問題**：PC4 / PC5 同時是 SPI0 的 MOSI/MISO 與 BROM 的 BOOT-SEL strap，
但 datasheet 沒給真值表，不知道該上拉還是下拉。

**查法**：MangoPi MQ-R 是同一顆 T113-S3，它的原理圖 p.3 直接印了真值表。
文字抽取只用來定位，實際接法是把那塊區域 render 成圖目視確認的
（專案規則「抽出來的文字用來定位，不用來定案」的第五次命中）。

```
SEL[1:0]
  00:  NOR > NAND
  01:  SD  > NOR  > Other
√ 10:  SD  > NAND > Other          ← MangoPi 打勾的是這個
  11:  SD0 > EMMC2 > EMMC2_USR > Other
```

MangoPi 的實際接法：

```
VCC3V3 ─┬─ R75 10K  ─ SPI0_MISO ─ R76 NC   ─┬─ GND
        └─ R77 NC   ─ SPI0_MOSI ─ R78 10K  ─┘
         → SEL1 = 1, SEL0 = 0  →  10
```

**選了什麼**：本板要 **01（SD > NOR > Other）**，剛好與 MangoPi 左右對調。

```
SPI0_MISO (PC5, BOOT-SEL1)   10K 下拉   → 0    storage 頁 R96 焊、R95 不焊
SPI0_MOSI (PC4, BOOT-SEL0)   10K 上拉   → 1    storage 頁 R97 焊、R98 不焊
```

**理由**：本板有 SD、有 SPI NOR、沒有 NAND。選 10 的話第二順位會去找不存在的
NAND，白等一輪 timeout。

**代價**：兩個位置都留焊盤（各兩顆電阻、其中一顆不上件），多四個焊盤面積。
換到的是「改 boot order 不必飛線」—— strap 是上電那一刻的事，改不了就是改不了。

---

## 2. FEL 按鍵接哪支腳（解掉 004 §7）

**問題**：004 §7 寫「FEL 按鍵接哪一支腳必須查 datasheet」，一直沒查到。

**選了什麼**：**不需要專用 FEL 腳。**

BOOT-SEL = 01 時 BROM 依序試 SD → NOR → Other，兩個都失敗就落到 USB FEL。
要「主動」進 FEL，只要讓 SEL0 在上電瞬間變成 0：

```
SW2（usb 頁）：SPI0_MOSI ─[R107 1K]─ 按鍵 ─ GND
按住上電 → 1K 壓贏 storage 頁的 10K 上拉 → SEL[1:0] = 00（NOR > NAND）
         → NOR 是空的、又沒有 NAND → 直接進 USB FEL
```

**理由**：這是從 §1 的真值表推出來的，不是猜的。而且它不需要額外的 SoC 腳位。

**代價**：按住 SW2 時 1K 掛在 SPI0_MOSI 上。只在上電瞬間按，之後放開；
就算一直按著，3.3V/1K = 3.3mA 在 T113 的驅動能力內，而且 FEL 模式本來就不用 SPI。

---

## 3. 排針 GPIO 從 10 支變 7 支

**問題**：五個週邊控制訊號沒有 SoC 腳可用 ——
HDMI_PD、HDMI_INT_N、PANEL_RESET_N、USB_EN、USB_OC_N。
T113-S3 的 129 腳已經全部配完，unit 6 剩下的 16 支未用腳全是類比
（FMIN / LINEIN / MICIN / TVIN / TP-X,Y），不能當 GPIO。
唯一的來源是 PG bank，而 PG 16 支全部給了排針。

**選了什麼**：拿三支，另外兩支用不佔腳的做法。

| 訊號 | 做法 | 失去什麼 |
|---|---|---|
| HDMI_INT_N | **PG12**（原 HDR_GPIO8） | — |
| HDMI_PD | **PG14**（原 HDR_GPIO9） | — |
| PANEL_RESET_N | **PG4**（原 HDR_GPIO7） | — |
| USB_EN | 100K 上拉常開（usb 頁 R106） | 軟體關不掉 USB 埠 |
| USB_OC_N | 測試點 TP13 | 軟體讀不到過流狀態 |

**理由**：判準是「缺了會不會影響 bring-up」。

```
HDMI_INT_N      HPD 偵測是本專案的練習重點（002 bring-up 清單）。
                輪詢也能做，但中斷才是 driver 真正的寫法 —— 練不到就失去意義。
HDMI_PD         002 §1.4 明確要求「MIPI 模式時 ADV7511 要保持關閉」。
                它同時是 I2C 位址的 strap，所以 GPIO 與下拉電阻兩個都要。
PANEL_RESET_N   DSI 面板的初始化序列一定要能拉 RESET，
                沒有它連 DCS 命令都送不進去。MIPI 是本專案第一優先。
USB_EN          常開就好。失去的是「軟體重啟卡死的 WiFi dongle」這個方便。
USB_OC_N        限流保護是 TPS2051B 內部做的，不靠軟體。
                失去的只是「軟體知道發生過」。
```

**代價**：**與 SPEC 不符** —— SPEC 寫排針純 GPIO 10 支，實際 7 支。
排針仍有 7 GPIO + 2 組 I2C + UART1 + UART0 console 備援，夠用，但這是明確的縮水。
如果之後覺得排針比 HDMI 中斷重要，改回去只要動 mcu 頁的三個標籤名稱
（`rename_nets.py` 反向跑）。

---

## 4. ADV7511 的 I2C 掛在排針的 TWI1 上

**問題**：ADV7511 的控制 I2C 需要接到 SoC，但 PG7/PG8（TWI1）已經給了排針。

**選了什麼**：**共用**。display 頁的 SCL/SDA 直接用 `HDR_I2C1_SCL` / `HDR_I2C1_SDA`。

**理由**：I2C 本來就是匯流排，掛多個裝置是正常用法。
ADV7511 的位址是 0x39 / 0x3D（7-bit），不是常見的衝突區。

**代價**：
- 外接模組的位址不可與 ADV7511 衝突 —— 已寫在排針頁的圖紙註記上。
- 訊號經過 mcu 頁的 100R 串聯電阻（R33/R34）。400kHz 下 RC 延遲可忽略。
- net 名稱叫 `HDR_I2C1_*` 有點誤導（它不只給排針用）。
  改名要動 mcu 頁的手畫內容，不值得。

**2kΩ 上拉放在 display 頁**（R83/R84），因為 ADV7511 是這條匯流排上
唯一一定存在的裝置（002 §3.2.2 要求 2kΩ ±5%）。

---

## 5. HDMI 的 TMDS 不放 ESD，USB 的資料線放

同一個判斷在兩處走向相反的結論，所以值得記下來。

| | HDMI TMDS | USB 2.0 HS |
|---|---|---|
| 速率 | 1.485 Gbps/pair | 480 Mbps |
| 可容忍的 ESD 元件電容 | < 1 pF | ~1.5 pF 可接受 |
| 符合的料 | 只有 0201 單線件（ESD131-B1-W0201） | USBLC6-2SC6，SOT-23-6 |
| 手焊 | 做不到 | 可以 |
| **決定** | **V1 不放** | **放，每對一顆（D1/D2/D3）** |

**為什麼不「只放一半」**：
① 在 TMDS 走線上留「不焊的焊盤」本身就是 stub，比不放更糟。
② 只保護慢速線（HPD / DDC / CEC）會造成「有保護」的錯覺。

**代價**：HDMI 熱插拔的 ESD 直接打在 ADV7511 的 TMDS 輸出上。
板子要小心拿。V2 改用整合式 HDMI ESD 陣列，placement 階段就留位置。

---

## 6. MIPI FPC 的腳位是暫定值

**問題**：002 §2.3 寫得很白 ——「面板 FPC 的 pin 定義各家不同，下單前務必用實體面板比對」。
但沒有面板就畫不出接頭，而 MIPI 是第一優先。

**選了什麼**：用常見的 40-pin 4-lane 排法（差分對之間夾 GND）先畫，
並在**圖紙上**用最大的字標明「這張腳位表是暫定值，不是定案」。

**理由**：有一張待核對的圖，比沒有圖更接近完成。
但警告必須在圖上，不是在 markdown 裡 —— 佈線時看的是圖。

**代價**：這一頁的佈線在選定面板、逐腳核對完之前**不能開始**。
已經寫成圖紙上的核對清單。

**IOVCC 用 0Ω 二選一**：R108（+3V3，預設焊）/ R109（+1V8_SOC，不焊）。
焊錯邊的代價是面板報廢，所以核對面板 datasheet 之前不要上電。

---

## 7. 幾個「漏了就不會動，但圖上看不出來」的被動件

這一類最危險：netlist 完全合法、ERC 不會報、所有線都接得好好的，
要到 bring-up 才發現。集中列在這裡。

| 元件 | 位置 | 漏了會怎樣 |
|---|---|---|
| **R61 4.7K ↑** | net 頁，RTL8201F pin 8 RXDV | 內部弱下拉 = MII 模式。本板只拉了 RMII 的七條線，**完全不通** |
| R62 4.7K ↓ | net 頁，pin 12 CLK_CTL | REF_CLK 方向反了，50MHz 沒人提供 |
| R64 4.7K ↓ | net 頁，RXER/FXEN | 進了光纖模式 |
| R63 4.7K ↑ | net 頁，MDIO | 開汲極沒上拉，讀不到 PHY 暫存器（PHY 像不存在） |
| R60 2.49K 1% | net 頁，RSET | MDI 驅動電流不對，鏈路跑不起來 |
| R81 887R 1% | display 頁，R_EXT | ADV7511 內部參考電流沒設定，晶片不動 |
| R82 10K ↓ | display 頁，PD/AD | I2C 位址與 PD 極性都不確定 |
| R106 100K ↑ | usb 頁，USB_EN | USB-A 一直沒電（EN 是高有效，GPIO 上電是高阻態） |
| C70/C71 22pF | net 頁，25MHz 負載電容 | PHY「時而能通時而不能」 |

共通點：**接錯或漏掉都不燒件，但板子不會動。**
對照之下，電源頁踩過的兩次（FB 接錯通道、LDO 的 VOUT 並聯）是會燒件的那一類。
兩類都要防，但防法不同 —— 前者靠逐條核對 datasheet 的 strap 表，後者靠 netlist 驗證。

---

## 8. 這一輪新增的工具

| 腳本 | 用途 |
|---|---|
| `sym_pins.py` | 印出符號的腳位與座標。寫生成器前一定要先看 —— 座標算錯的線頭差幾 mm，圖上完全看不出來 |
| `dryrun_sheet.py` | 不碰檔案就檢查生成器：非格點座標、designator 撞號/跳號、net 清單 |
| `rename_nets.py` | 唯一會動到手畫內容的腳本，所以多三道保險（KiCad 關閉、git 乾淨、舊名稱剛好一次） |
| `run_all.py` | 八張子頁的生成順序有相依性，不能亂跑 |
| `schlib.Page` | 把「從腳位拉線接到標籤/電源/電阻」收成方法。偏移量算錯就是接不上 |
| `schlib.RAIL_SYMBOL` | net 名稱 → power 符號的查表。直接拿 net 名稱當 lib_id 會生出不存在的符號，開檔整頁變問號 |

### 這一輪修掉的三個「安靜的錯」

比報錯更危險的是不報錯：

1. **`check_schematic.py` 的 kicad-cli 路徑寫死 Program Files**，
   KiCad 10 實際裝在 `%LOCALAPPDATA%` → 整支檢查器一直安靜地沒跑。
   修好後立刻抓到 `U6 pin 91 (AGND)` 沒接到 GND。
2. **`sheet_uuid_of()` 從子頁自己的內容抓路徑** ——
   剛建立的空白子頁裡沒有這個資訊，會回傳 `None`，
   結果是那一頁所有元件的 reference 變成 `?`。
3. **`sym_pins.py` 不處理符號繼承** —— CH340N 是從 CH330N 繼承的，
   只看自己的區塊會得到「共 0 支腳」這種看起來像答案的錯答案。

---

## 9. 還沒做完的

```
[ ] U1 RY1303 的 QFN footprint（封裝圖是圖片，pitch / EP 尺寸待核）
[ ] U6 T113-S3 的 eLQFP128 footprint（EPAD 要自建）
[ ] 全專案的 LCSC 料號欄位 → 才能出 BOM
[ ] ERC 歸零
[ ] U6 pin 91 (AGND) 接到 GND —— check_schematic.py 修好後抓到的
[ ] MIPI FPC 腳位逐腳核對（選定面板之後）
```
