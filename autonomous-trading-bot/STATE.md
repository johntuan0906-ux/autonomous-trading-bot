# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 20:16:29 · commit `ffb1a37`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `44348` · round `7` · nhịp tim cách đây 111.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3418.47 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 840 lệnh đóng, WR 58.21%, E(R) 0.0228, PnL 9.72$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 611 | 56.3 | 1.051 | 0.989 | 0.0138 | -16.37 |
| 14 ngày | 794 | 58.06 | 1.108 | 1.02 | 0.0273 | 36.2 |
| 30 ngày | 840 | 58.21 | 1.088 | 1.005 | 0.0228 | 9.72 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.051 < 1.2; PF($) cua so 7 ngay = 0.989 < 1.1; PF(R) cua so 14 ngay = 1.108 < 1.2; PF($) cua so 14 ngay = 1.020 < 1.1; PF(R) cua so 30 ngay = 1.088 < 1.2; PF($) cua so 30 ngay = 1.005 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 378 lần cập nhật trọng số · Hội đồng AI: **9 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (10)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 108695.5 | 0.005096 | 0.0050799999999999994 | 0.004981 | True | True | 0.848 |
| AKE/USDT:USDT | LONG | 15822.0 | 0.025075 | 0.024443 | 0.026655 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 2645.5 | 0.12084 | 0.119805 | 0.116115 | True | True | 1.048 |
| ALT/USDT:USDT | SHORT | 34722.0 | 0.00813 | 0.00812187 | 0.00777 | True | True | 0.486 |
| APE/USDT:USDT | SHORT | 2617.5 | 0.1468 | 0.14615499999999998 | 0.142025 | True | True | 0.838 |
| APT/USDT:USDT | SHORT | 446.5 | 0.8069 | 0.8060930999999999 | 0.778905 | True | True | 0.545 |
| AR/USDT:USDT | SHORT | 45.3 | 3.887 | 3.857586 | 3.74907 | True | True | 1.033 |
| ARB/USDT:USDT | SHORT | 3915.4 | 0.1839 | 0.186454 | 0.177515 | False | False | 0.039 |
| ASTER/USDT:USDT | SHORT | 1439.0 | 0.6923 | 0.699248 | 0.67493 | False | False | 0.0 |
| ATOM/USDT:USDT | SHORT | 474.92 | 1.775 | 1.796056 | 1.72236 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
