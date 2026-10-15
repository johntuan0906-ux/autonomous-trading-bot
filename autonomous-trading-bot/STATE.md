# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 09:31:37 · commit `7e4eada`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `132` · nhịp tim cách đây 89.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3472.96 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 896 lệnh đóng, WR 59.04%, E(R) 0.0375, PnL 154.04$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 667 | 57.57 | 1.125 | 1.078 | 0.0343 | 127.95 |
| 14 ngày | 850 | 58.94 | 1.164 | 1.091 | 0.0424 | 180.52 |
| 30 ngày | 896 | 59.04 | 1.142 | 1.072 | 0.0375 | 154.04 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.125 < 1.2; PF($) cua so 7 ngay = 1.078 < 1.1; PF(R) cua so 14 ngay = 1.164 < 1.2; PF($) cua so 14 ngay = 1.091 < 1.1; PF(R) cua so 30 ngay = 1.142 < 1.2; PF($) cua so 30 ngay = 1.072 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 410 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| AERO/USDT:USDT | SHORT | 668.8 | 0.8595 | 0.87445 | 0.822125 | False | False | 0.0 |
| AIOT/USDT:USDT | SHORT | 2821.5 | 0.0524 | 0.051685999999999996 | 0.04797 | True | True | 0.903 |
| APR/USDT:USDT | SHORT | 5122.5 | 0.05204 | 0.05148799999999999 | 0.0496 | True | True | 2.193 |
| AR/USDT:USDT | SHORT | 153.5 | 3.616 | 3.681134 | 3.453165 | False | False | 0.261 |
| ARB/USDT:USDT | SHORT | 3246.7 | 0.1728 | 0.17588 | 0.1651 | False | False | 0.13 |
| ASTER/USDT:USDT | SHORT | 733.0 | 0.6792 | 0.6785208 | 0.662155 | True | True | 0.352 |
| ATOM/USDT:USDT | SHORT | 361.14 | 1.679 | 1.70669 | 1.609775 | False | False | 0.144 |
| AVAX/USDT:USDT | SHORT | 27.0 | 9.539 | 9.529461 | 9.08274 | True | True | 0.652 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
