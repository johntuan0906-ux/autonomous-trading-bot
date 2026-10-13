# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 01:00:51 · commit `a99b200`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `2168` · round `None` · nhịp tim cách đây 5.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 749 lệnh đóng, WR 56.48%, E(R) 0.0217, PnL -19.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 520 | 53.46 | 1.038 | 0.963 | 0.0105 | -45.89 |
| 14 ngày | 703 | 56.19 | 1.104 | 1.004 | 0.0266 | 6.68 |
| 30 ngày | 749 | 56.48 | 1.082 | 0.989 | 0.0217 | -19.8 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.038 < 1.2; PF($) cua so 7 ngay = 0.963 < 1.1; PF(R) cua so 14 ngay = 1.104 < 1.2; PF($) cua so 14 ngay = 1.004 < 1.1; PF(R) cua so 30 ngay = 1.082 < 1.2; PF($) cua so 30 ngay = 0.989 < 1.1
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

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 156250.0 | 0.004194 | 0.00413 | 0.004354 | False | False | 0.009 |
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005189 | 0.005237 | 0.005069 | False | False | 0.0 |
| AIN/USDT:USDT | SHORT | 3355.5 | 0.04424 | 0.04419576 | 0.040515 | True | True | 0.302 |
| AIOT/USDT:USDT | LONG | 3681.5 | 0.0549 | 0.055021 | 0.058295 | True | True | 0.589 |
| ALGO/USDT:USDT | SHORT | 5624.2 | 0.11901 | 0.120788 | 0.114565 | False | False | 0.0 |
| APR/USDT:USDT | SHORT | 5230.0 | 0.0547 | 0.056612 | 0.04992 | False | False | 0.105 |
| APT/USDT:USDT | SHORT | 358.2 | 0.8358 | 0.8349641999999999 | 0.800905 | True | True | 0.43 |
| AR/USDT:USDT | SHORT | 170.9 | 3.919 | 3.977496 | 3.77276 | False | False | 0.103 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
