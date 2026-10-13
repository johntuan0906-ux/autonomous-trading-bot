# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 00:15:33 · commit `c842c4a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `69080` · round `3` · nhịp tim cách đây 15.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 748 lệnh đóng, WR 56.55%, E(R) 0.023, PnL -9.81$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 519 | 53.56 | 1.045 | 0.971 | 0.0125 | -35.9 |
| 14 ngày | 702 | 56.27 | 1.11 | 1.011 | 0.028 | 16.67 |
| 30 ngày | 748 | 56.55 | 1.088 | 0.994 | 0.023 | -9.81 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.045 < 1.2; PF($) cua so 7 ngay = 0.971 < 1.1; PF(R) cua so 14 ngay = 1.110 < 1.2; PF($) cua so 14 ngay = 1.011 < 1.1; PF(R) cua so 30 ngay = 1.088 < 1.2; PF($) cua so 30 ngay = 0.994 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 334 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| AIN/USDT:USDT | SHORT | 6711.0 | 0.04424 | 0.04573 | 0.040515 | False | False | 0.02 |
| AIOT/USDT:USDT | LONG | 7363.0 | 0.0549 | 0.053542 | 0.058295 | False | False | 0.147 |
| ALGO/USDT:USDT | SHORT | 5624.2 | 0.11901 | 0.120788 | 0.114565 | False | False | 0.0 |
| APR/USDT:USDT | SHORT | 5230.0 | 0.0547 | 0.056612 | 0.04992 | False | False | 0.052 |
| APT/USDT:USDT | SHORT | 716.4 | 0.8358 | 0.849758 | 0.800905 | False | False | 0.043 |
| AR/USDT:USDT | SHORT | 170.9 | 3.919 | 3.977496 | 3.77276 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
