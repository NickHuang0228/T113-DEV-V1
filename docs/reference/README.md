# 參考資料

大型 PDF 不進版控（見 `.gitignore`），這裡記錄每份文件的來源，換機器時照這份重新取得。

---

## Allwinner T113-S3

| 檔案 | 說明 | 來源 |
|---|---|---|
| `allwinner/T113-S3_datasheet_v1.6.pdf` | 主 datasheet（較新） | Allwinner / sunxi 社群 |
| `allwinner/T113-S3_datasheet_v1.2.pdf` | 主 datasheet（舊版，對照用） | 同上 |

⚠ 兩個版本都留著：**datasheet 改版時常會修正或刪除規格**，
遇到矛盾要以新版為準，但舊版有時反而寫得比較細。

### 還需要取得

```
[ ] T113-S3 User Manual（暫存器層級，datasheet 沒有）
[ ] T113-S3 封裝機構圖（footprint 的唯一可信來源）
[ ] T113-S3 Design Guide / 參考原理圖（若原廠有釋出）
```

---

## 橋接與周邊

```
[ ] IT66121 datasheet        ITE，RGB → HDMI
[ ] RTL8201F datasheet       Realtek，RMII PHY
[ ] CH340N datasheet         沁恒，USB → UART
[ ] TPS2051 datasheet        TI，USB Host 限流開關（若採用）
```

---

## 開源參考設計

```
MangoPi MQ-R                 T113-S3，有公開原理圖
DongshanPI-Nezha-STU         T113-S3，100ask，有公開資料
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
