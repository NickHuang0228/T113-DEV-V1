# hardware —— KiCad 專案

```
T113-DEV-V1.kicad_pro      專案
T113-DEV-V1.kicad_sch      根圖紙
symbols/                   自建符號（由腳本生成，勿手改）
footprints/                自建 footprint
data/                      腳位表等來源資料 ★ 單一真實來源
scripts/                   生成與檢查工具
```

---

## 協作方式

**Nick 畫，Claude 檢查。**

眼睛看 128 隻腳是靠不住的 —— 所以檢查是自動的，不是用看的。

```bash
python hardware/scripts/check_schematic.py
```

它做的事：

```
1. 用 kicad-cli 匯出 netlist
   ★ 讓 KiCad 自己做 net 解析 —— 我們不碰 wire/junction/label 的幾何，
     那是最容易判斷錯的部分
2. 對 netlist 套規則（rules_t113.py）
3. 印出 錯誤 / 警告 / 提示，每條都附設計文件出處
```

**畫一段就跑一次**，不要等整張畫完。

### 目前的規則

| 規則 | 檢查什麼 | 出處 |
|---|---|---|
| 電源軌錯誤 | T113 每支電源腳接的軌是否正確 | 011-power-tree.md §1 |
| 電源腳未接 | 有沒有電源腳浮接 | 同上 |
| 不該接電源軌 | LDOA-OUT / LDOB-OUT / VRA1 / VRA2 誤接到軌 | 011-power-tree.md §3.1 |
| ADV 電源軌錯誤 | ADV7511 的三組 1.8V 分組是否正確 | 011-power-tree.md §5 |
| ADV GND | 11 支 GND 是否都接地 | ADV7511 Table 3 |
| ADV 未用輸入 | RGB666 未用的 D 腳是否接 GND | 002-display.md §3.2 |
| RGB 接線 | T113 的 LCD0-D 與 ADV7511 的 D 是否同一條 net | 002-display.md §3.2 |
| 缺元件 | DZQ 240R、R_EXT 887R 等必備件 | 011-power-tree.md §6 |
| 單腳 net | 只接了一支腳的 net（多半是漏接） | — |

**規則只在相關元件存在時才生效** —— 還沒畫到的頁不會噴一堆錯。

新增檢查請改 `scripts/rules_t113.py`，不要改 `check_schematic.py`。

---

## 符號

**單一真實來源是 `data/T113-S3_pinmap.csv`。**

```bash
python hardware/scripts/gen_t113_symbol.py
```

改腳位一律改 CSV 再重跑，**不要手改 `.kicad_sym`**。
理由與 128 腳的核對過程見 [../docs/design/010-symbol.md](../docs/design/010-symbol.md)。

---

## ⚠ 畫圖時要特別小心的四處非連號

符號本身已經是對的，但**心裡要有底**，因為這些在原理圖上看起來完全正常：

```
PD12 / PD13 對調    pin 69 = PD13,  pin 70 = PD12
PG 頂排亂序         118=PG1 · 119=PG2 · 120=PG0 · 122=PG5 · 123=PG4
PE 底排亂序         整段遞減,但 PE0/PE1 在最後(44/45)
USB0 與 USB1 的 DP/DM 順序相反
                    112=USB1-DP · 113=USB1-DM
                    114=USB0-DM · 115=USB0-DP
```

---

## Net 命名（請照這個，檢查器認這些名字）

```
+5V_VBUS   Type-C 進來的 5V
+5V_USB    經 TPS2051B 限流後給 USB-A Host
+5V_HDMI   HDMI 座上的 +5V（DDC 上拉用，接外部螢幕）
+3V3
+1V8_SOC   SoC 側 1.8V
+1V8_HDMI  ADV7511 專屬 1.8V（LC 之前）
+1V8_DVDD  ADV7511 DVDD 組（LC 之後）
+1V8_AVDD  ADV7511 AVDD+PVDD 組（LC 之後）
+1V8_PLVDD ADV7511 PLVDD+BGVDD 組（LC 之後）
+1V5       VCC-DRAM
+0V9       VDD-CORE / VDD-SYS
GND
```

⚠ KiCad 會在階層圖紙的 net 名前加 `/` 前綴，檢查器會自動去掉，不用管。
