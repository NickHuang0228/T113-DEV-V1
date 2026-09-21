# 現在到哪了

> 這份是**狀態快照**，不是設計文件。只回答三個問題：
> 現在在哪、什麼已經不會再動、下一步做什麼。
> 每次開工先看這份，細節再去翻 `docs/`。

最後更新：2026-09-21

---

## 進度

```
階段 0  規格與選型     ████████████  完成
階段 1  原理圖         ███░░░░░░░░░  進行中  ← 現在在這
階段 2  PCB layout     ░░░░░░░░░░░░
階段 3  出圖與下單     ░░░░░░░░░░░░
階段 4  bring-up       ░░░░░░░░░░░░
```

**階段 1 的細部：**

```
[x] T113-S3 符號生成（128 腳，兩份腳位表交叉檢查通過）
[ ] 合併腳位表成單一來源        ← 下一步
[ ] 周邊元件符號（ADV7511 / RTL8201F / CH340N / 電源）
[ ] 電源樹上圖
[ ] 各介面電路上圖
[ ] ERC 歸零
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
不做        WiFi 模組、CSI、eMMC、JTAG、PMIC
```

---

## 還在動

```
腳位表      兩份共存（tools/ 與 hardware/data/）→ 待合併
BOM 價格    T113 實價是原估的 2.8 倍，總成本待重算
排針        28-pin 規格草案，未最終確認
電源電流    VDD-CORE / VDD-SYS / VCC-DRAM 在 datasheet 是 TBD
```

---

## 下一步（只做這一件）

**合併兩份腳位表成單一來源。**

```
tools/t113s3_pins.csv              機器抽，欄位豐富（reset/pull/drive/supply/group）
hardware/data/T113-S3_pinmap.csv   人工整理，含 EPAD、KiCad 電氣型別、mux 註記
```

為什麼要先做：**兩個真實來源一定會長歪。** 現在有交叉檢查擋著，
但每加一個欄位就要維護兩次，遲早對不上。原理圖還沒開始畫，現在合併最便宜。

---

## 技術債

```
[ ] 兩份腳位表未合併
[ ] SPEC.md 的成本表用的是舊價（T113 實價 2.8 倍未反映）
[ ] 002-display.md v0.2 曾把 R/B 標反，已修但要確認沒有殘留
[ ] PDF 參考資料不在版控內，換機器要重新下載（來源記在 docs/reference/README.md）
```

---

## 文件地圖

不用全讀。需要時再翻：

| 想知道什麼 | 看哪份 |
|---|---|
| 整體規格 | `docs/SPEC.md` |
| 為什麼選這顆晶片 | `docs/ROADMAP.md` §2 |
| 哪支腳接什麼 | `docs/design/007-pinmap.md` |
| 電源怎麼配 | `docs/design/011-power-tree.md` |
| 顯示鏈路 | `docs/design/002-display.md` |
| 走線規則 | `docs/design/005-stackup.md` |
| 要買什麼料 | `docs/design/009-bom.md` |
| 怎麼焊 | `docs/design/006-assembly.md` |
| 發生過什麼 | `notes/devlog.md`（最長，但只是流水帳） |
