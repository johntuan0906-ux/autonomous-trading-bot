# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 06:05:06 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `21904` · round `239` · nhịp tim cách đây 10.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4550.36 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 328 lệnh đóng, WR 65.85%, E(R) 0.0921, PnL 220.61$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 243 | 66.26 | 1.681 | 1.572 | 0.1206 | 234.69 |
| 14 ngày | 303 | 65.02 | 1.385 | 1.265 | 0.0802 | 161.46 |
| 30 ngày | 328 | 65.85 | 1.442 | 1.333 | 0.0921 | 220.61 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 149 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 2503.0 | 0.2336 | 0.237594 | 0.223615 | False | False | 0.2 |
| AVAX/USDT:USDT | SHORT | 75.0 | 10.14 | 10.271788 | 9.81053 | False | False | 0.121 |
| BTC/USDT:USDT | SHORT | 0.0295 | 81784.4 | 82122.696902 | 80938.657745 | False | False | 0.067 |
| DOGE/USDT:USDT | SHORT | 11520.0 | 0.08424 | 0.085108 | 0.08207 | False | False | 0.242 |
| LINK/USDT:USDT | SHORT | 77.88 | 12.766 | 12.894402 | 12.444995 | False | False | 0.086 |
| SOL/USDT:USDT | SHORT | 7.3 | 109.79 | 111.15823 | 106.369425 | False | False | 0.205 |
| XRP/USDT:USDT | SHORT | 755.7 | 1.3753 | 1.388532 | 1.34222 | False | False | 0.189 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
