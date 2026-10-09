# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 09:05:07 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `70904` · round `185` · nhịp tim cách đây 18.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 343 lệnh đóng, WR 65.01%, E(R) 0.085, PnL 209.89$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 258 | 65.12 | 1.607 | 1.503 | 0.1094 | 223.98 |
| 14 ngày | 315 | 64.44 | 1.386 | 1.269 | 0.0792 | 167.99 |
| 30 ngày | 343 | 65.01 | 1.405 | 1.301 | 0.085 | 209.89 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 156 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 3538.0 | 0.2321 | 0.234926 | 0.225035 | False | False | 0.212 |
| AVAX/USDT:USDT | SHORT | 79.0 | 10.21 | 10.335834 | 9.895415 | False | False | 0.167 |
| BTC/USDT:USDT | SHORT | 0.0367 | 81691.6 | 81963.390734 | 81012.123165 | False | False | 0.136 |
| DOGE/USDT:USDT | SHORT | 15974.0 | 0.08457 | 0.085196 | 0.083005 | False | False | 0.128 |
| LINK/USDT:USDT | SHORT | 74.45 | 12.796 | 12.930306 | 12.460235 | False | False | 0.0 |
| SOL/USDT:USDT | SHORT | 5.77 | 109.32 | 111.05275 | 104.988125 | False | False | 0.162 |
| XRP/USDT:USDT | SHORT | 1054.4 | 1.3879 | 1.397384 | 1.36419 | False | False | 0.169 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
