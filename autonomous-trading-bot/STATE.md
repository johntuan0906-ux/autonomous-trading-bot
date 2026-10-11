# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 00:47:24 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `53308` · round `11` · nhịp tim cách đây 82.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3905.17 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 542 lệnh đóng, WR 56.83%, E(R) 0.0208, PnL 58.45$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 404 | 53.47 | 1.077 | 1.051 | 0.0192 | 40.97 |
| 14 ngày | 511 | 56.16 | 1.07 | 1.032 | 0.0172 | 33.41 |
| 30 ngày | 542 | 56.83 | 1.084 | 1.052 | 0.0208 | 58.45 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.077 < 1.2; PF($) cua so 7 ngay = 1.051 < 1.1; PF(R) cua so 14 ngay = 1.070 < 1.2; PF($) cua so 14 ngay = 1.032 < 1.1; PF(R) cua so 30 ngay = 1.084 < 1.2; PF($) cua so 30 ngay = 1.052 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 240 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 192307.5 | 0.0086 | 0.008636999999999999 | 0.008665 | True | True | 1.923 |
| 1000CAT/USDT:USDT | LONG | 277777.5 | 0.002052 | 0.002054052 | 0.002097 | True | True | 0.333 |
| 1000FLOKI/USDT:USDT | LONG | 46728.0 | 0.0277 | 0.027486 | 0.028235 | False | False | 0.187 |
| 1000LUNC/USDT:USDT | LONG | 34013.0 | 0.0516 | 0.051306 | 0.052335 | False | False | 0.034 |
| 1000XEC/USDT:USDT | LONG | 86207.0 | 0.007332 | 0.007382 | 0.007477 | True | True | 1.362 |
| AAVE/USDT:USDT | LONG | 6.4 | 170.6 | 169.057696 | 174.45576 | False | False | 0.0 |
| ACH/USDT:USDT | LONG | 87719.0 | 0.006154 | 0.00604 | 0.006439 | False | False | 0.0 |
| AERO/USDT:USDT | LONG | 587.1 | 0.9647 | 0.947668 | 1.00728 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
