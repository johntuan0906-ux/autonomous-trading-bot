# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 09:21:35 · commit `434de8f`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `102888` · round `8` · nhịp tim cách đây 149.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3644.33 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 669 lệnh đóng, WR 57.1%, E(R) 0.0356, PnL 114.18$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 440 | 53.86 | 1.112 | 1.091 | 0.0297 | 88.09 |
| 14 ngày | 638 | 56.58 | 1.133 | 1.065 | 0.0334 | 89.13 |
| 30 ngày | 669 | 57.1 | 1.141 | 1.077 | 0.0356 | 114.18 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.112 < 1.2; PF($) cua so 7 ngay = 1.091 < 1.1; PF(R) cua so 14 ngay = 1.133 < 1.2; PF($) cua so 14 ngay = 1.065 < 1.1; PF(R) cua so 30 ngay = 1.141 < 1.2; PF($) cua so 30 ngay = 1.077 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 297 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000PEPE/USDT:USDT | SHORT | 143472.0 | 0.0039233 | 0.003993 | 0.003748 | False | False | 0.0 |
| AIN/USDT:USDT | LONG | 9633.0 | 0.04592 | 0.044882 | 0.048515 | False | False | 0.135 |
| AIOT/USDT:USDT | LONG | 4012.5 | 0.0553 | 0.0553553 | 0.058415 | True | True | 0.321 |
| ALGO/USDT:USDT | SHORT | 4859.0 | 0.1185 | 0.120558 | 0.113355 | False | False | 0.068 |
| ASTER/USDT:USDT | SHORT | 1219.0 | 0.6878 | 0.696 | 0.6673 | False | False | 0.0 |
| AXL/USDT:USDT | SHORT | 3037.65 | 0.0563 | 0.0562437 | 0.052185 | True | True | 0.365 |
| AXS/USDT:USDT | SHORT | 540.0 | 1.139 | 1.15749 | 1.092775 | False | False | 0.162 |
| BAT/USDT:USDT | LONG | 1579.25 | 0.1531 | 0.156157 | 0.161015 | True | True | 1.466 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
