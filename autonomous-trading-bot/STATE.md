# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 07/11/2026 19:15:44 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89420` · round `290` · nhịp tim cách đây 129.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3190.78 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2936 lệnh đóng, WR 40.77%, E(R) 0.2266, PnL -1104.0$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 15 | 13.33 | 0.358 | 0.404 | -0.4485 | -66.88 |
| 14 ngày | 29 | 13.79 | 0.671 | 0.322 | -0.2271 | -133.14 |
| 30 ngày | 2699 | 38.64 | 1.866 | 0.751 | 0.2443 | -1154.12 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.358 < 1.2; PF($) cua so 7 ngay = 0.404 < 1.1; PF(R) cua so 14 ngay = 0.671 < 1.2; PF($) cua so 14 ngay = 0.322 < 1.1; PF($) cua so 30 ngay = 0.751 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 745 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (12)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 24560.9 | 0.002917 | 0.002914083 | 0.002689 | True | True | 1.114 |
| 1000SHIB/USDT:USDT | SHORT | 24560.9 | 0.004601 | 0.004596399 | 0.004373 | True | True | 1.026 |
| ADA/USDT:USDT | SHORT | 567.0 | 0.1879 | 0.19495 | 0.1738 | False | False | 0.78 |
| AERO/USDT:USDT | SHORT | 143.7 | 0.6046 | 0.632434 | 0.548932 | False | False | 0.259 |
| ALT/USDT:USDT | SHORT | 19047.0 | 0.00554 | 0.00575 | 0.00512 | False | False | 0.714 |
| APR/USDT:USDT | LONG | 1171.0 | 0.04391 | 0.040496 | 0.050738 | False | False | 0.513 |
| ASTER/USDT:USDT | SHORT | 194.0 | 0.684 | 0.704532 | 0.642936 | False | False | 0.336 |
| AVAX/USDT:USDT | SHORT | 16.0 | 8.407 | 8.65546 | 7.91008 | False | False | 0.608 |
| AXL/USDT:USDT | SHORT | 1672.58 | 0.0386 | 0.0385614 | 0.035252 | True | True | 1.254 |
| BAT/USDT:USDT | SHORT | 756.7 | 0.12777 | 0.133056 | 0.117198 | False | False | 0.969 |
| BNB/USDT:USDT | SHORT | 0.69 | 694.35 | 700.084056 | 682.881888 | False | False | 0.148 |
| UNI/USDT:USDT | SHORT | 22.0 | 7.022 | 7.196306 | 6.673388 | False | False | 0.258 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
