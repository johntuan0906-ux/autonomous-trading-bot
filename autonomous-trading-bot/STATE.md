# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 00:35:02 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `107972` · round `13` · nhịp tim cách đây 9.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 310 lệnh đóng, WR 68.06%, E(R) 0.1266, PnL 310.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 226 | 69.03 | 2.169 | 2.077 | 0.168 | 324.89 |
| 14 ngày | 287 | 67.6 | 1.645 | 1.51 | 0.1175 | 255.7 |
| 30 ngày | 310 | 68.06 | 1.682 | 1.561 | 0.1266 | 310.8 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 144 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 1805.0 | 0.2243 | 0.229838 | 0.210455 | False | False | 0.018 |
| AVAX/USDT:USDT | SHORT | 42.0 | 9.801 | 10.033778 | 9.219055 | False | False | 0.013 |
| BTC/USDT:USDT | SHORT | 0.0146 | 80623.6 | 81307.193336 | 78914.61666 | False | False | 0.054 |
| DOGE/USDT:USDT | SHORT | 7042.0 | 0.08125 | 0.08267 | 0.0777 | False | False | 0.0 |
| LINK/USDT:USDT | SHORT | 43.04 | 12.115 | 12.34729 | 11.534275 | False | False | 0.0 |
| SOL/USDT:USDT | SHORT | 4.36 | 106.14 | 108.43174 | 100.41065 | False | False | 0.096 |
| XRP/USDT:USDT | SHORT | 445.6 | 1.3271 | 1.34954 | 1.271 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
