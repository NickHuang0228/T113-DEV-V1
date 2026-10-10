# 現在到哪了

> 這份是**狀態快照**，不是設計文件。只回答三個問題：
> 現在在哪、什麼已經不會再動、下一步做什麼。
> 每次開工先看這份，細節再去翻 `docs/`。

最後更新：2026-10-10

---

## 進度

```
階段 0  規格與選型     ████████████  完成
階段 1  原理圖         ███████████░  進行中  ← 現在在這（十張頁全部畫完，待跑進 KiCad）
階段 2  PCB layout     ░░░░░░░░░░░░
階段 3  出圖與下單     ░░░░░░░░░░░░
階段 4  bring-up       ░░░░░░░░░░░░
```

**階段 1 的細部：**

```
[x] T113-S3 符號生成（128 腳，自我一致性檢查通過）
[x] 合併腳位表成單一來源（2026-09-21）
[x] 電源符號（gen_power_symbols.py）
[x] 電源頁 power.kicad_sch（33 顆元件）
[x] 周邊元件符號（ADV7511 100 腳 / RTL8201F 33 腳；CH340N 用 KiCad 內建）
[x] 主晶片頁 unit 1~5（98 腳）
[x] 八張子頁的生成器全部寫完並通過 dryrun 檢查   ← 現在在這
[ ] ★ 關掉 KiCad，跑 run_all.py --apply          ← 下一步，只有你能做
[ ] 開 KiCad 檢查每頁的擺放（元件重疊、標籤被蓋住）
[ ] ERC 歸零
[ ] footprint 補齊（RY1303 QFN、T113 eLQFP128 的 EPAD 要自建）
[ ] LCSC 料號欄位 → 出 BOM
```

---

## 已定案（不會再動）

改這些要有很強的理由，且會連動一堆文件。

```
主晶片      T113-S3  eLQFP128  內建 128MB DDR3
橋接晶片    ADV7511（IT66121 已停產）
乙太 PHY    RTL8201F + RJ45 HR911105A
USB-UART    CH340N
PCB         4 層 · 阻抗控制 · 100×100mm 以內
組裝        部分貼裝（只貼 3 顆難焊 IC，其餘自焊）
bank 電壓   VCC-PD / VCC-PE / VCC-PG 全部 3.3V
顯示切換    MIPI 與 RGB 共用 PD0~PD9，10 顆 0Ω 二選一
console     UART0 走 PF2/PF4，2 顆 0Ω 分支到 CH340N
開機順序    BOOT-SEL = 01（SD > NOR > Other）
            PC5 下拉、PC4 上拉；真值表來自 MangoPi MQ-R 原理圖 p.3
FEL         不需要專用腳。SW2 把 BOOT-SEL0 拉低 → BROM 自己落到 USB FEL
不做        WiFi 模組、CSI、eMMC、JTAG、PMIC
```

---

## 還在動

```
BOM 價格    T113 實價是原估的 2.8 倍，總成本待重算
排針        2×13 = 26-pin 已定案，但純 GPIO 從 10 支縮到 7 支
            （PG12/PG14/PG4 挪給 HDMI_INT_N / HDMI_PD / PANEL_RESET_N，
             理由與代價見 docs/design/013-schematic-decisions.md §3）
MIPI FPC    40-pin 腳位是暫定值，選定面板後要逐腳核對才能佈線
電源電流    VDD-CORE / VDD-SYS / VCC-DRAM 在 datasheet 是 TBD
```

---

## 下一步（只做這一件）

**畫完電源頁 `hardware/power.kicad_sch`**，照 `011-power-tree.md` v0.2。

```
★ 電源頁畫完了（32 元件、18 條 net、值全填、無命名衝突）

已完成   RY1303 全部 21 腳、三路 buck、兩顆 AP2112K LDO、
         APX803 RESET supervisor、TPS2051B USB-A 限流
待補     ① 32 個元件的 Footprint 與 LCSC 欄位全是空的
         ② U5 的 IN 側缺一顆 0.1µF 去耦（貼著 pin 5）
         ③ 跑一次 ERC
下一頁   主晶片頁（T113-S3 + 去耦 + R9 DZQ 240R）
```

⚠ 分壓的上端要接在輸出電容之後（真正的輸出 net），不是電感前的 SW 腳。

---

## 技術債

```
[ ] SPEC.md 的成本表用的是舊價（T113 實價 2.8 倍未反映）
[ ] 002-display.md v0.2 曾把 R/B 標反，已修但要確認沒有殘留
[ ] PDF 參考資料不在版控內，換機器要重新下載（來源記在 docs/reference/README.md）
```

---

## 文件地圖

不用全讀。需要時再翻：

| 想知道什麼 | 看哪份 |
|---|---|
| **核心概念（要內化的 8 條）** | **`docs/concepts/`** |
| 整體規格 | `docs/SPEC.md` |
| 為什麼選這顆晶片 | `docs/ROADMAP.md` §2 |
| 哪支腳接什麼 | `docs/design/007-pinmap.md` |
| 電源怎麼配 | `docs/design/011-power-tree.md` |
| 顯示鏈路 | `docs/design/002-display.md` |
| 走線規則 | `docs/design/005-stackup.md` |
| **畫原理圖的規矩** | **`docs/design/012-schematic-conventions.md`** |
| 要買什麼料 | `docs/design/009-bom.md` |
| 怎麼焊 | `docs/design/006-assembly.md` |
| 發生過什麼 | `notes/devlog.md`（最長，但只是流水帳） |
