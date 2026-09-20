# 參考資料

大型 PDF 不進版控（見 `.gitignore`），這裡記錄每份文件的來源，換機器時照這份重新取得。

---

## 周邊 IC

| 檔案 | 頁數 | 說明 | 來源 |
|---|---|---|---|
| `peripherals/ADV7511_Hardware_Users_Guide.pdf` | 58 | **HDMI 橋接主文件**（Rev D, 2011-07）—— 電氣規格 §4、腳位表 §5、Layout §7 | [analog.com](https://www.analog.com/media/en/technical-documentation/user-guides/ADV7511_Hardware_Users_Guide.pdf) |
| `peripherals/RTL8201F-VB-CG_datasheet_v1.4.pdf` | 67 | 乙太 PHY | Realtek |
| `peripherals/CH340DS1_datasheet.pdf` | — | USB-UART | WCH |
| `peripherals/IT66121FN_datasheet_v1.02.pdf` | 40 | ⚠ **已停產，設計已改用 ADV7511**；保留作對照 | ITE |

⚠ **ADV7511 的 PDF 無法自動下載。** ADI 封鎖 curl / PowerShell / WebFetch
（HTTP 000 或連線重置），各大鏡像站也拿不到正確檔案。
**必須用瀏覽器開上面的連結，手動按下載鈕**（Chrome 不接受程式合成的點擊）。

數字摘要已整理在 `peripherals/ADV7511KSTZ_extracted.md`（**這份有進版控**），
換機器時就算一時拿不到 PDF，設計也不會卡住。

### ADV7511 章節速查

```
§4    p.12-13   Table 1 電氣規格（VIH 1.35~3.5V · tVSU 1.0ns · tVHLD 0.7ns · 1.8V 325mW）
§5.1  p.18      Figure 6 腳位圖   ★ D[35:0] 的索引↔腳號只能從這張圖看
§5.1  p.19-20   Table 3 完整腳位表（R_EXT 887Ω · PD/AD 一腳兩用）
§5.1  p.21      Figure 7 機構圖（ST-100 · MS-026-BED · 14×14 · 無 EPAD）
§6.8  p.50      Power Domains  ★「要自己專屬的 1.8V LDO」這句在這裡
§6.8  p.50      Figure 23 三組分法（DVDD ／ AVDD+PVDD ／ PLVDD+BGVDD）
§6.8.1 p.50     無上電時序要求
§7.1  p.52      Figure 24 雜訊上限曲線（200k~1MHz 只容許 1.3 mV rms）
§7.2~7.7 p.53-54 CLK 阻抗控制 · 上拉值 · R_EXT · CEC
§7.8  p.55      Figure 27 參考原理圖
```

⚠ **規格分散在 §4 / §5 / §6.8 / §7 四處** —— 只讀 §7「PCB Layout Recommendations」
會漏掉 §6.8 的專屬 LDO 要求。這是實際踩過的坑。

---

## Allwinner T113-S3

| 檔案 | 頁數 | 說明 | 來源 |
|---|---|---|---|
| `allwinner/T113-S3_Datasheet_v1.6_20220303.pdf` | 98 | **主 datasheet**（含封裝機構圖 §7.2） | [dl.linux-sunxi.org](https://dl.linux-sunxi.org/T113-S3/T113-S3_Datasheet_v1.6_20220303.pdf) |
| `allwinner/T113-S3_User_Manual_v1.3.pdf` | 1360 | 暫存器手冊（較新） | [mangopi.org](https://mangopi.org/_media/t113-s3_user_manual_v1.3_.pdf) |
| `allwinner/T113-S3_User_Manual_v1.1.pdf` | 1383 | 暫存器手冊（舊版，對照用） | [bbs.aw-ol.com](https://bbs.aw-ol.com/assets/uploads/files/1648883311855-t113-s3_user_manual_v1.1.pdf) |

⚠ 兩個 User Manual 版本都留著：**改版時常會修正或刪除規格**，
遇到矛盾要以新版為準，但舊版有時反而寫得比較細（v1.1 比 v1.3 多 23 頁）。

### datasheet 章節速查

```
§2.12  p.19        Package（eLQFP128, 14×14×1.4mm）
§4.1   p.23        Pin Quantity（128 腳裡只有 1 支 AGND）
§4.2   p.23~       Pin Characteristics  ⚠ pdftotext 抽出來欄位錯位，必須看原頁
§5.3   p.45-46     Recommended Operating Conditions（各軌電壓）
§5.4   p.47-48     Power Consumption（多項 TBD）
§5.12  p.73-74     Power-On / Power-Off Sequence
§6     p.76        Package Thermal（θJA 20.36 °C/W）
§7.1   p.77        Pin Map
§7.2   p.78        Package Dimension  ⚠ CAUTION：EPAD 要用第二組 D3/E3
```

### 還需要取得

```
[ ] T113-S3 Design Guide / 原廠參考原理圖（若原廠有釋出）
[ ] T113-S3 datasheet v1.2（舊版對照；v1.6 的 revision history 已列各版變更，優先度低）
```

---

## 橋接與周邊

| 檔案 | 頁數 | 說明 | 來源 |
|---|---|---|---|
| `peripherals/IT66121FN_datasheet_v1.02.pdf` | **40** | RGB → HDMI，**完整版**（含 Figure 17 機構圖 p.40） | [seeeddoc.github.io](https://seeeddoc.github.io/BeagleBone_Green_HDMI_Cape/res/IT66121FN_Datasheet_v1.02.pdf) |
| `peripherals/RTL8201F-VB-CG_datasheet_v1.4.pdf` | 67 | RMII PHY，完整版 | [skytech.ir](http://skytech.ir/DownLoad/File/895_RTL8201F.pdf) |
| `peripherals/CH340DS1_datasheet.pdf` | 11 | USB → UART | [robototehnika.ru](https://robototehnika.ru/file/CH340.pdf) |

> ⚠ **更正**：先前記為「8 頁公開簡版、無機構圖」是錯的 —— `file` 指令把頁數讀錯，
> 實際是 **40 頁的完整版**，`Figure 17. 64-pin QFN Package Dimensions` 在 p.40。
> 封裝：QFN-64，9×9 mm，pitch 0.5，EPAD 3.78×3.78，PIN65 = GND PAD。
> 完整尺寸見 [008-footprint.md](../design/008-footprint.md) §4。

⚠ **RTL8201F 的 datasheet 涵蓋三種封裝**，查機構圖時別拿錯章節：

```
§10.1  p.55   RTL8201F   QFN-32    ← 本專案用這個
§10.2  p.56   RTL8201FL  LQFP-48
§10.3  p.57   RTL8201FN  QFN-48
```

### 還需要取得

```
[ ] RY1303 datasheet（三路 DC-DC，MangoPi 用的，若採用）
[ ] TPS2051 datasheet（TI，USB Host 限流開關，若採用）
[ ] XT25F128B datasheet（SPI NOR）
[ ] 接頭類：RJ45 HR911105A / Type-C / microSD / FPC 座（畫 PCB 前）
```

---

## 開源參考設計

| 檔案 | 頁數 | 說明 | 來源 |
|---|---|---|---|
| `boards/MangoPi_MQ-R_sch_v1.6.pdf` | 3 | T113-S3 參考設計 | [mangopi.org](https://mangopi.org/_media/mq-dual_sch_v1.6.pdf) |

MangoPi MQ-R 涵蓋範圍：

```
可對照   T113 本體、電源（RY1303 三路 DC-DC）、時脈、boot、USB、SDIO、RGB/MIPI 輸出
不涵蓋   IT66121（RGB→HDMI）、RTL8201F（RMII→PHY→RJ45）
         MQ-R 是 USB 隨身碟大小的板子，沒有 HDMI bridge 也沒有乙太網路
```

```
[ ] DongshanPI-Nezha-STU 原理圖（100ask，**有乙太網路**，補 MQ-R 缺的那段）
```

⚠ 參考原理圖可以看設計思路，**footprint 一律回到原廠機構圖驗算**。
上一塊板踩過兩次「拿二手資料當實際幾何」的坑。

---

## 軟體

```
sunxi-fel            https://github.com/linux-sunxi/sunxi-tools
U-Boot mainline      有 T113 / D1 系列支援
Linux mainline       drivers/gpu/drm/bridge/ite-it66121.c
sunxi 社群 wiki      https://linux-sunxi.org/
```
