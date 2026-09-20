# 010 · T113-S3 符號建立

版本：v0.2 · 2026-09-21（與另一條線的機器抽取表交叉驗證通過）

**單一真實來源是 `hardware/data/T113-S3_pinmap.csv`。**
符號由 `hardware/scripts/gen_t113_symbol.py` 生成，**不手改 `.kicad_sym`**。

---

## 1. 為什麼不手畫

128 腳手動輸入，錯一腳就是一條接錯的線，而且**錯了幾乎看不出來** ——
原理圖上 `PD12` 接到 pin 69 和接到 pin 70 長得完全一樣，
要等 PCB 回來量測才會發現。

```
CSV  ──[生成腳本]──▶  .kicad_sym
 ▲                        │
 └── 目視核對機構圖        └── 回讀驗證,與 CSV 逐項比對
```

**改腳位一律改 CSV 再重跑腳本。** 這樣「符號和資料不一致」這種錯誤不可能發生。

---

## 2. 資料怎麼來的

`(DS §7.1 Figure 7-1 Pin Map, p.77)`

⚠ **那張圖的標籤是向量圖，不是文字** —— 整頁只抽得到 41 個字。
`pdftotext` / `get_text()` 都拿不到腳位名稱。

作法：

```python
pg = doc[86]                                   # 印刷 p.77 = PDF p.87
pg.get_pixmap(dpi=900, clip=fitz.Rect(...)).save("crop.png")
```

分四邊裁切、900 dpi render，**逐腳目視抄寫**。
頂排與底排的標籤是旋轉 90° 的，300 dpi 看不清，必須拉到 700~900 dpi。

**這是專案規則「定位靠文字，定案靠看圖」的第四次應用。**

---

## 3. 交叉驗證：與 datasheet 自己的統計表對帳

`(DS §4.1 Pin Quantity, p.23)`

| 分類 | 本表 | DS | |
|---|---|---|---|
| I/O | 102 | 102 | ✓ |
| NC | 1 | 1 | ✓ |
| Power | 21 | 21 | ✓ |
| Ground | 1 | 1 | ✓ |
| DDR Power | 3 | 3 | ✓ |
| **合計** | **128** | **128** | ✓ |

再加上：

```
1~128 無缺號、無重複        ✓
名稱無重複                   ✓
PB 6 · PC 6 · PD 23 · PE 14 · PF 7 · PG 16，各 bank 索引連續  ✓
```

**五項分類全中，代表抄寫沒有錯。** 只對總數不夠 ——
把兩支腳互換，總數不變但分類也不變，所以還要靠下面的「非連號」檢查。

> ⚠ Power = 21 的算法：要把 **VRA1 / VRA2 算進電源類**（它們是內部參考電壓輸出）。
> 不算的話是 19，對不上。這也反過來證明分類方式與原廠一致。

### 3.1 ★ 與另一條開發線的機器抽取表交叉驗證

同一天另一個 session（commit `a78672f`）用**完全不同的方法**做了同一件事：

```
這份（本文件）   目視抄 Figure 7-1 Pin Map（向量圖，900 dpi render 逐腳看）
tools/           page.find_tables() 機器抽 Table 4-2（依繪製線框切格子）
```

比對結果：

```
128 腳全部一致，零不一致
（唯一差異是本表多一列 pin 129 = EPAD —— Table 4-2 本來就不列它）
```

**兩種獨立方法、零分歧 —— 這比任何單一方法的自我檢查都強。**

> 對方那條線還發現一件事：Table 4-2 先前被記為「欄位錯位、不可用」，
> **問題不在 datasheet，在抽取方法** —— `get_text()` 依文字座標重建欄位會跑位，
> `find_tables()` 依繪製線框切格子不會。
>
> **規則升級：有線框的表格先用 `find_tables()`，沒線框的才退回看圖。**
> 本文件 §2 的「只能用看的」只適用於 Figure 7-1 這種純向量圖。

### 3.2 ⚠ 目前有兩份腳位表，還沒合併

```
tools/t113s3_pins.csv          機器抽 Table 4-2，欄位較豐富（reset/pull/drive_mA/supply/group）
hardware/data/T113-S3_pinmap.csv   本文件用的，含 EPAD、KiCad 電氣型別、mux 註記
```

**兩個真實來源是會長歪的。** 在合併成一份之前，
`gen_t113_symbol.py` 每次生成都會自動比對兩份，不一致就中止：

```
✓ 與 tools/t113s3_pins.csv 交叉檢查一致（128 腳）
```

```
[ ] ★ 合併成單一來源：以 tools/ 的機器抽取為底，
     疊上 KiCad 需要的欄位（電氣型別、單元分配、EPAD）
```

---

## 4. ★ 四處非連號 —— 假設連號就會接錯

抄寫時最容易出錯的就是「看到 PD10、PD11 就以為後面是 PD12、PD13」。
實際上 T113-S3 有四處不連號：

### 4.1 PD12 / PD13 對調

```
pin 67  PD10
pin 68  PD11
pin 69  PD13   ★
pin 70  PD12   ★
pin 71  PD14
```

**這是全板最容易踩的一個。** PD12/PD13 是 RGB 的 `LCD0-D18`/`LCD0-D19`（R0/R1），
接反的話紅色會少兩個 bit 且錯位。

### 4.2 PG 的頂排順序

```
pin 118  PG1   ★
pin 119  PG2   ★
pin 120  PG0   ★
pin 121  PG3
pin 122  PG5   ★
pin 123  PG4   ★
```

PG0 不在 PG1 前面，PG4/PG5 對調。**排針的 GPIO 全在 PG，接錯就是排針腳位全錯。**

### 4.3 PE 的底排順序

```
pin 33  PE3      pin 40  PE7
pin 35  PE2      pin 41  PE6
pin 36  PE11     pin 42  PE5
pin 37  PE10     pin 43  PE4
pin 38  PE9      pin 44  PE0   ★
pin 39  PE8      pin 45  PE1   ★
```

PE 幾乎整段是遞減排列，而 **PE0/PE1 被放到最後**。
PE bank 是 RMII，接錯網路不會通。

### 4.4 USB0 與 USB1 的 DP/DM 順序相反

```
pin 112  USB1-DP    ★ USB1 是 DP 在前
pin 113  USB1-DM
pin 114  USB0-DM    ★ USB0 是 DM 在前
pin 115  USB0-DP
```

**兩組 USB 的極性排列是鏡像的。** 差分對接反雖然 USB 有時仍能列舉，
但這是不該賭的事 —— 而且 layout 時會影響走線交叉。

---

## 5. 單元切分

依 bank 切，理由見 [007-pinmap.md](007-pinmap.md) §2：**bank 是災損邊界，也是電源域邊界。**

| 單元 | 內容 | 腳數 |
|---|---|---|
| 1 | **電源**（所有 VCC / VDD / LDO / AGND / EPAD / DDR 電源） | 26 |
| 2 | **PB + PC + PF**（共用 VCC-IO —— 命脈 bank） | 19 |
| 3 | **PD**（VCC-PD，顯示） | 23 |
| 4 | **PE**（VCC-PE，網路） | 14 |
| 5 | **PG**（VCC-PG，排針） | 16 |
| 6 | **類比／音訊**（AVCC 域 + CVBS + 觸控 + GPADC） | 19 |
| 7 | **系統 / USB**（RESET、晶振、DZQ、USB、NC） | 12 |
| | **合計** | **129** |

**PB/PC/PF 放同一個單元是刻意的** —— 它們共用 VCC-IO，
畫原理圖時看到它們在同一張紙上，就會想起「這三個 bank 一起死」。

---

## 6. 驗證流程

```bash
python hardware/scripts/gen_t113_symbol.py          # 生成
kicad-cli sym upgrade hardware/symbols/*.kicad_sym --force   # KiCad 解析（能存表示格式合法）
kicad-cli sym export svg hardware/symbols/*.kicad_sym -o <dir>   # 七個單元都畫得出來
```

再跑回讀驗證：從 `.kicad_sym` 反解出每支腳的 `(number, name, type)`，與 CSV 逐項比對。

```
符號內腳位數 129  CSV 129
不符: 無    多餘: 無
```

---

## 7. 待辦

```
[ ] Footprint 欄位目前留空 —— 等 008-footprint.md 的 LQFP-128 + EPAD 自建件完成後填入
[ ] 符號畫面實際在 KiCad 裡開起來看一次（目前只驗證了資料正確與格式合法）
[ ] ADV7511 / RTL8201F / CH340N 的符號 —— 優先用 KiCad 內建件，缺的再自建
[ ] CSV 的 note 欄目前只填了主要 mux 功能，畫各介面電路時再補齊
[ ] ★ 兩份腳位表合併成單一來源（見 §3.2）
```
