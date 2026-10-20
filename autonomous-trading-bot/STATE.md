# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 16:24:14 · commit `08c7330`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `56128` · round `4` · nhịp tim cách đây 177.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3257.79 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3320 lệnh đóng, WR 45.09%, E(R) 1.3235, PnL -1003.82$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2629 | 41.99 | 6.313 | 0.718 | 1.6606 | -1102.61 |
| 14 ngày | 3091 | 43.74 | 5.639 | 0.791 | 1.418 | -1029.91 |
| 30 ngày | 3320 | 45.09 | 5.403 | 0.816 | 1.3235 | -1003.82 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.718 < 1.1; PF($) cua so 14 ngay = 0.791 < 1.1; PF($) cua so 30 ngay = 0.816 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 454 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (13)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| AERO/USDT:USDT | SHORT | 208.1 | 0.8069 | 0.818908 | 0.77688 | False | False | 0.15 |
| AKE/USDT:USDT | LONG | 2049.0 | 0.035163 | 0.033943 | 0.038213 | False | False | 0.109 |
| ALGO/USDT:USDT | LONG | 2485.0 | 0.1103 | 0.109294 | 0.112815 | False | False | 0.159 |
| AVAX/USDT:USDT | SHORT | 20.0 | 9.431 | 9.554224 | 9.12294 | False | False | 0.097 |
| BANK/USDT:USDT | LONG | 10683.0 | 0.02613 | 0.025896 | 0.026715 | False | False | 0.128 |
| BAT/USDT:USDT | LONG | 401.8 | 0.20067 | 0.194448 | 0.216225 | False | False | 0.146 |
| BTR/USDT:USDT | LONG | 5506.0 | 0.04431 | 0.043856 | 0.045445 | False | False | 0.0 |
| CTSI/USDT:USDT | LONG | 8741.0 | 0.03052 | 0.030234 | 0.031235 | False | False | 0.0 |
| DOT/USDT:USDT | LONG | 154.5 | 1.1334 | 1.117222 | 1.173845 | False | False | 0.155 |
| EIGEN/USDT:USDT | SHORT | 828.9 | 0.233 | 0.236016 | 0.22546 | False | False | 0.0 |
| GWEI/USDT:USDT | LONG | 3731.0 | 0.02256 | 0.02189 | 0.024235 | False | False | 0.03 |
| HBAR/USDT:USDT | SHORT | 2934.0 | 0.08252 | 0.083372 | 0.08039 | False | False | 0.0 |
| HUMA/USDT:USDT | LONG | 5580.0 | 0.028479 | 0.028031 | 0.029599 | False | False | 0.011 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
