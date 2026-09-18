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

## 6. WiFi：畫但不焊（DNP）

### 決定

```
PCB 上放 footprint、SDIO 走線、天線區域、匹配網路位置
BOM 不列這些料 → JLCPCB 不上件 → 不收費
```

實際花費：**$0**（只要板子仍在 100×100mm 內）。

### 為什麼不上件

**硬體成本其實不高**（約 NT$550）：

```
RTL8723DS 模組 ×2（WiFi+BT, SDIO）    $6
32.768kHz 晶振 ×2                     $0.4
1.8V LDO ×2（部分模組需要）            $0.6
u.FL 座 ×2 + 外接天線 ×2              $3
匹配網路 π型 + 去耦 ×2                 $1
Extended part fee                     $6
```

**貴的是另外兩項：**

**① PCB 面積可能跳級**

```
模組本體          ~12×12mm
RF keep-out       天線周圍 5~10mm 淨空
PCB 天線（若用）   額外 ~15×5mm
實際吃掉           約 30×20mm
```

超過 100×100mm 的話，4 層 5 片從 $20 跳到 $35~50。
而且天線下方挖空會切斷 GND 平面，**可能影響旁邊 MIPI/TMDS 的回流路徑**。

**② driver 風險取決於 kernel 選擇**

| kernel | RTL8723DS SDIO | 風險 |
|---|---|---|
| mainline 6.x | `rtw88` 已有 SDIO 支援 | 低 |
| **全志 BSP 5.4 / Tina** | **需 out-of-tree driver，版本被綁死** | **高** |

第一塊板建議走**全志 BSP**（外設齊全、bring-up 容易），那 WiFi 就落在高風險那格。

### 要無線就插 USB dongle

```
RTL8188EU / MT7601U / RTL8812AU   $3~5
mainline driver 完整、零 layout 成本、零風險、隨時可拔
```

### 但 layout 還是要畫 —— 因為那才是學習目標

畫出來就練到了，不一定要焊：

```
RF keep-out 規劃
天線淨空區與所有層挖空
π 型匹配網路擺位（靠近天線饋入點）
50Ω 單端 RF 走線
如何在挖空 GND 的同時不破壞旁邊差分的回流   ← 最有價值的一項
```

最後一項是真正的取捨題，不是照抄規則能解的。

之後真要用，手焊模組上去即可（SDIO 走線已經在板子上）。
