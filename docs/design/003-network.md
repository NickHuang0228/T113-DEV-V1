# 003 · 乙太網路

---

## 1. 為什麼選乙太網路而不是 WiFi

**最大的價值不是「有網路」，是開發循環的速度。**

```
沒有網路
  改 kernel → 編譯 → 燒 SD 卡 → 插回板子 → 開機 → 看 log
                                  ↑ 每次 3~5 分鐘

有乙太網路
  改 kernel → 編譯 → U-Boot 從 TFTP 抓 → 開機
  rootfs 用 NFS 掛在 PC 上，改檔案立即生效
                                  ↑ 每次 20 秒
```

第一塊 Linux 板會反覆改 dts、kernel config、panel driver ——
**這個差別會決定是一週做完還是一個月做完。**

### 對照

| | **乙太網路 RMII** | WiFi SDIO 模組 |
|---|---|---|
| 晶片 | RTL8201F ~$1.2 | RTL8723DS ~$2.5 |
| Linux driver | **mainline 直接支援** | 廠商 out-of-tree，品質參差 |
| **U-Boot 階段** | **✓ TFTP / NFS 開機** | **✗ 完全沒有** |
| layout 學到 | RMII 等長 + 100Ω 差分 + 變壓器隔離 | SDIO + RF keep-out |
| 風險 | 低 | 中高 |

**要無線就插 USB WiFi dongle**（RTL8188EU / MT7601U，mainline driver 完整）——
零 layout 成本、零風險、隨時可拔。

---

## 2. 電路

```
T113-S3 EMAC ──RMII──▶ RTL8201F ──▶ RJ45（整合式含變壓器）
```

### RMII 訊號（7 條 + 管理 2 條）

```
TXD0 / TXD1      資料送出
RXD0 / RXD1      資料收進
TX_EN            送出致能
CRS_DV           載波偵測／資料有效
REF_CLK          50 MHz 參考時脈  ← 最關鍵的一條
MDC / MDIO       管理介面（讀寫 PHY 暫存器）
```

**REF_CLK 的方向要先決定**：

```
模式 A   PHY 用 25MHz 晶振，內部倍頻產生 50MHz 給 SoC
模式 B   SoC 產生 50MHz 給 PHY
```

⚠ 兩種都可行，但**電路與 dts 設定不同**，必須先確定再畫。
RTL8201F 兩種都支援，由 strap pin 決定。

---

## 3. Layout 規則

### RMII 段（PHY ↔ SoC）

```
速率      50 MHz
等長      ±5mm 即可（比 DDR 寬鬆非常多）
REF_CLK   走線最短最直，不換層，下方鋪完整 GND
阻抗      單端 50Ω（非強制，但建議）
```

### 差分段（PHY ↔ 變壓器 ↔ RJ45）

```
TX± / RX±    100Ω 差分
走線          最短最直，不換層
對內等長      ±0.5mm（100Mbps，要求寬鬆）
```

### 變壓器隔離 —— 最常被漏掉的一條

```
變壓器下方與 RJ45 側的地平面必須挖空
```

**挖了才是隔離，沒挖等於白裝變壓器。**
隔離區域涵蓋變壓器本體到 RJ45 之間的所有層，不只表層。

### Bob Smith termination

RJ45 未使用的線對要做終端，否則會變成天線：

```
4 組 75Ω 電阻 ──┬── 1000pF / 2kV 電容 ── 機殼地
                （四個中心點接在一起）
```

### 晶振

```
25 MHz 晶振緊貼 PHY，走線 <10mm
負載電容依 datasheet（通常 12~22pF）
晶振下方鋪完整 GND，不走任何訊號
```

---

## 4. TFTP + NFS 開機設定

硬體做好之後，軟體端的設定（記在這裡，bring-up 時會用到）：

### U-Boot 端

```
setenv ipaddr 192.168.1.100
setenv serverip 192.168.1.10
setenv netmask 255.255.255.0

# 從 TFTP 抓 kernel 與 dtb
tftp 0x40000000 zImage
tftp 0x4FA00000 t113-dev-v1.dtb

# rootfs 掛 NFS
setenv bootargs "console=ttyS0,115200 root=/dev/nfs rw \
  nfsroot=192.168.1.10:/srv/nfs/rootfs,v3,tcp \
  ip=192.168.1.100:192.168.1.10:192.168.1.1:255.255.255.0::eth0:off"

bootz 0x40000000 - 0x4FA00000
```

### PC 端（Linux 或 WSL）

```
TFTP     tftpd-hpa，根目錄放 zImage 與 dtb
NFS      nfs-kernel-server，export /srv/nfs/rootfs
```

⚠ 開發機是 Windows 的話，用 WSL2 跑 TFTP/NFS，或直接用編譯機（`kdev`）。

---

## 5. 驗收

```
[ ] RMII 7 條等長 ±5mm，REF_CLK 最短最直
[ ] REF_CLK 方向已確定，strap pin 設定正確
[ ] TX±/RX± 100Ω 差分，最短路徑
[ ] 變壓器下方與 RJ45 側地平面已挖空（所有層）
[ ] Bob Smith termination 已放
[ ] 25MHz 晶振緊貼 PHY，下方完整 GND
[ ] PHY 位址（PHYAD）strap 設定確認，與 dts 一致
```

bring-up 時的驗證順序：

```
1. ifconfig eth0 up        介面存在嗎
2. ethtool eth0            link 起來了嗎、速度對嗎
3. mdio 讀 PHY ID          PHY 認得到嗎
4. ping 閘道
5. TFTP 抓檔
6. NFS 掛 rootfs
```

---

## 6. WiFi：完全不做（v0.2 決定）

### 決定歷程

```
v0.1   預留 RTL8723DS footprint + SDIO 走線 + 天線區 + 匹配網路（DNP，畫但不焊）
       理由：畫出來就練到 RF layout，不上件所以 $0
v0.2   ✗ 完全移除
       理由：腳位成本遠大於預期
```

### 為什麼改掉

做完 bank 分析（[007-pinmap.md](007-pinmap.md) §3）後發現：

```
PB / PC / PF   VCC-IO   SD 開機 + NOR 開機 + UART log   一燒就變磚
PD             VCC-PD   MIPI + HDMI                     顯示全失
PE             VCC-PE   RMII                            開發循環沒了
PG             VCC-PG   ★ 唯一「燒了也不痛」的 bank
```

**排針必須放 PG，別無選擇。** 而 WiFi 的 SDIO1 剛好也在 PG0~PG5。

```
PG 共 16 支
  − 6 支 WiFi SDIO1（DNP 也要畫走線）
  = 10 支
  − 4 支 I2C ×2
  − 2 支 UART 備援
  = 4 支純 GPIO
```

**一個永遠不焊的模組，吃掉板上最安全 bank 的 37%。** 這筆帳 v0.1 沒算。

### 移除後的收穫

```
+ 排針純 GPIO    4 → 10 支
+ 板面積         省 30 × 20 mm（更容易守住 100×100mm 的 JLCPCB 價格斷點）
+ GND 平面完整   天線區挖空消失 → 不必處理「挖空 GND 又不破壞旁邊差分回流」
+ VCC-PG 自由    不再被 SDIO 電平綁住，可選 3.3V 配合外接模組
+ layout 工時    少畫 6 條 SDIO + 匹配網路 + keep-out
− RF layout      練不到
```

**唯一的損失是學習目標，不是功能。** 而那個學習目標可以留到專用的 RF 練習板，
不需要綁在第一塊 Linux 板上一起冒險。

### 要無線就插 USB dongle

```
RTL8188EU / MT7601U     mainline driver 完整
零 layout 成本、零 RF 風險、零腳位成本
插在既有的 USB-A Host 上
```

⚠ 但注意：**USB 現在同時扛 FEL 燒錄、WiFi dongle、UVC 攝影機三個角色。**
USB-A Host 那條 HS 差分（480 Mbps）的品質，比原本規劃「只插個鍵鼠」時重要得多。
90Ω 差分阻抗與等長要認真做。

### 這是本專案第三次用同一招

```
WiFi 模組   →  USB dongle
攝影機 CSI  →  USB UVC
WiFi footprint → 完全移除，USB dongle
```

**模式：當一個功能要吃掉稀缺腳位、或帶來 layout/driver 風險，
而 USB 上有成熟替代品時，就走 USB。**

第一塊 Linux 板的成功標準是「開機」，每砍掉一項，成功機率就高一點。
