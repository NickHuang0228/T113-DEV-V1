# T113-DEV-V1

自製 Allwinner T113-S3 Linux 開發板 —— 第一塊會跑 Linux 的自畫板。

前一塊：[ESP32S3-DEV-V1](https://github.com/NickHuang0228/ESP32-Kicad)（已下單、已 bring-up、WiFi 壓力測試通過）

---

## 這塊板要補的技能

上一塊板走完了 KiCad 全流程：四層疊構、USB FS 差分、單電壓域、出圖下單、bring-up。
這一塊往上走一階：

| | ESP32S3-DEV-V1 | **T113-DEV-V1** |
|---|---|---|
| 主晶片 | ESP32-S3 模組 | **T113-S3 裸晶片** |
| 電源域 | 1 組 | **4 組**（外部 3.3/1.5/0.9V + 晶片內建 1.8V LDO） |
| 差分對 | 1 對（USB FS 12Mbps） | **9 對**（USB HS / TMDS / MIPI / RMII） |
| 阻抗控制 | 無 | **必須** |
| 作業系統 | MicroPython | **Linux（自己 bring up）** |
| 燒錄 | USB CDC | **SD 卡 / FEL / TFTP+NFS** |

核心目標：**把一顆裸 SoC 從電源、時脈、儲存一路接到能開機、能上網、能推畫面。**

---

## 規格摘要

```
主晶片   Allwinner T113-S3
         2× Cortex-A7 @1.2GHz + RISC-V C906 + HiFi4 DSP
         內建 128MB DDR3（SIP 封裝，不需自行 layout DDR）

顯示     MIPI DSI 4-lane  FPC 座
         RGB 並列 → IT66121 → HDMI Type-A
         （共用同一組 TCON，dts 二選一）

網路     RMII → RTL8201F → RJ45 HR911105A（整合式含變壓器）
         WiFi 不做（SDIO 會吃掉 PG bank 6 支腳），要無線插 USB dongle

USB      Type-C #1  OTG + FEL 燒錄 + 供電
         Type-C #2  CH340N UART log + 供電
         USB-A      Host（可插 WiFi dongle）

儲存     microSD（主要開機）+ SPI NOR 16MB

音訊     內建 codec + 3.5mm 座

外設     28-pin 排針（2×14）
         GPIO ×10 · I2C ×2 · UART 備援 ×1（PG bank，隨時可用）
         SPI ×1（PD10~PD13，僅 MIPI 模式）
         全部經限流電阻，見 docs/design/007-pinmap.md

PCB      4 層 · 阻抗控制 · 100×100mm 以內
```

預算目標：**NT$5,000 以內**（PCB 5 片 + PCBA 2 片 + 零件 + 運費）

---

## 為什麼是 T113-S3

選型過程記在 [docs/ROADMAP.md](docs/ROADMAP.md)，結論：

- **內建 128MB DDR3（SIP）** —— 第一塊 Linux 板最大的風險（DDR 等長 layout）直接消除
- **eLQFP128 封裝** —— 腳位露在外面，可目視、可量測、焊橋可自己修；BGA 出問題只能報廢
  （底部有 EPAD，是唯一的數位地，必焊 → 主晶片交給 PCBA，見 006-assembly.md）
- **有 MIPI DSI** —— 這是長期目標（CSI/DSI/HDMI/DP 的 layout 經驗）的必要條件
- **$8** —— 便宜到可以買備品

被淘汰的選項與理由同樣記在 ROADMAP。

---

## 目前狀態

```
[x] 選型定案
[x] 規格書
[ ] 原理圖
[ ] PCB layout
[ ] 出圖驗證
[ ] 下單
[ ] bring-up
```

---

## 文件索引

| 文件 | 內容 |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | 完整規格：介面、元件、接腳、製造 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 選型過程、風險評估、驗收條件 |
| [docs/design/001-power.md](docs/design/001-power.md) | 電源樹與上電時序 |
| [docs/design/002-display.md](docs/design/002-display.md) | MIPI DSI 與 RGB→HDMI |
| [docs/design/003-network.md](docs/design/003-network.md) | RMII 與乙太網路 |
| [docs/design/004-usb-boot.md](docs/design/004-usb-boot.md) | Type-C、FEL、燒錄流程 |
| [docs/design/005-stackup.md](docs/design/005-stackup.md) | 層疊、阻抗、走線規則 |
| [docs/design/006-assembly.md](docs/design/006-assembly.md) | 組裝策略、工具選擇、備品 |
| [docs/design/007-pinmap.md](docs/design/007-pinmap.md) | bank 策略、腳位分配、排針規格 |
| [docs/design/008-footprint.md](docs/design/008-footprint.md) | 機構圖實測、EPAD 尺寸、footprint 驗算 |
| [notes/devlog.md](notes/devlog.md) | 開發日誌 |
