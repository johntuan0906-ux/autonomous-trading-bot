# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 09:01:37 · commit `7b51317`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `125` · nhịp tim cách đây 44.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3372.97 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 887 lệnh đóng, WR 58.74%, E(R) 0.0222, PnL 14.56$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 658 | 57.14 | 1.049 | 0.993 | 0.0135 | -11.53 |
| 14 ngày | 841 | 58.62 | 1.101 | 1.021 | 0.0263 | 41.04 |
| 30 ngày | 887 | 58.74 | 1.084 | 1.007 | 0.0222 | 14.56 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.049 < 1.2; PF($) cua so 7 ngay = 0.993 < 1.1; PF(R) cua so 14 ngay = 1.101 < 1.2; PF($) cua so 14 ngay = 1.021 < 1.1; PF(R) cua so 30 ngay = 1.084 < 1.2; PF($) cua so 30 ngay = 1.007 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 401 lần cập nhật trọng số · Hội đồng AI: **8 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 109170.0 | 0.0040622 | 0.0040581378 | 0.003947 | True | True | 0.493 |
| 1000SHIB/USDT:USDT | SHORT | 104166.5 | 0.005052 | 0.005046948 | 0.004932 | True | True | 0.5 |
| ADA/USDT:USDT | SHORT | 2378.5 | 0.2281 | 0.2278719 | 0.222845 | True | True | 0.618 |
| AIN/USDT:USDT | SHORT | 7739.5 | 0.04062 | 0.040553 | 0.039005 | True | True | 0.604 |
| AIOT/USDT:USDT | SHORT | 5643.0 | 0.0524 | 0.054172 | 0.04797 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 14326.0 | 0.027405 | 0.026707 | 0.02915 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 6720.4 | 0.11363 | 0.115118 | 0.10991 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 81967.0 | 0.00786 | 0.007982 | 0.007555 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 453.8 | 0.8124 | 0.809009 | 0.784855 | True | True | 0.808 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
