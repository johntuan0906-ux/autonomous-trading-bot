# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 04:35:05 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `21904` · round `109` · nhịp tim cách đây 28.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4580.23 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 325 lệnh đóng, WR 65.85%, E(R) 0.0946, PnL 225.84$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 240 | 66.25 | 1.71 | 1.599 | 0.1242 | 239.93 |
| 14 ngày | 301 | 65.12 | 1.402 | 1.281 | 0.0831 | 168.75 |
| 30 ngày | 325 | 65.85 | 1.456 | 1.346 | 0.0946 | 225.84 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 146 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 2503.0 | 0.2336 | 0.237594 | 0.223615 | False | False | 0.05 |
| AVAX/USDT:USDT | SHORT | 31.0 | 10.153 | 10.142847 | 9.75503 | True | True | 0.433 |
| BTC/USDT:USDT | SHORT | 0.0216 | 81745.1 | 82206.443894 | 80591.740265 | False | False | 0.223 |
| DOGE/USDT:USDT | SHORT | 11520.0 | 0.08424 | 0.085108 | 0.08207 | False | False | 0.069 |
| LINK/USDT:USDT | SHORT | 63.09 | 12.623 | 12.781496 | 12.22676 | False | False | 0.0 |
| SOL/USDT:USDT | SHORT | 7.3 | 109.79 | 111.15823 | 106.369425 | False | False | 0.205 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
