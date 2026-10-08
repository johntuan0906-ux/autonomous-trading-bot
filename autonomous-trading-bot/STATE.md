# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 05:35:05 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `21904` · round `195` · nhịp tim cách đây 26.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 326 lệnh đóng, WR 65.95%, E(R) 0.095, PnL 228.28$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 241 | 66.39 | 1.716 | 1.605 | 0.1247 | 242.36 |
| 14 ngày | 302 | 65.23 | 1.406 | 1.285 | 0.0836 | 171.19 |
| 30 ngày | 326 | 65.95 | 1.46 | 1.35 | 0.095 | 228.28 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 147 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 2503.0 | 0.2336 | 0.237594 | 0.223615 | False | False | 0.2 |
| AVAX/USDT:USDT | SHORT | 31.0 | 10.153 | 10.137594 | 9.75503 | True | True | 0.597 |
| BTC/USDT:USDT | SHORT | 0.0295 | 81784.4 | 82122.696902 | 80938.657745 | False | False | 0.067 |
| DOGE/USDT:USDT | SHORT | 11520.0 | 0.08424 | 0.085108 | 0.08207 | False | False | 0.242 |
| LINK/USDT:USDT | SHORT | 63.09 | 12.623 | 12.781496 | 12.22676 | False | False | 0.0 |
| SOL/USDT:USDT | SHORT | 7.3 | 109.79 | 111.15823 | 106.369425 | False | False | 0.205 |
| XRP/USDT:USDT | SHORT | 755.7 | 1.3753 | 1.388532 | 1.34222 | False | False | 0.189 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
