# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 00:07:08 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `75424` · round `4` · nhịp tim cách đây 3.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 301 lệnh đóng, WR 67.11%, E(R) 0.1178, PnL 272.77$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 220 | 67.27 | 1.913 | 1.811 | 0.1456 | 265.66 |
| 14 ngày | 278 | 66.55 | 1.573 | 1.434 | 0.1076 | 217.67 |
| 30 ngày | 301 | 67.11 | 1.616 | 1.492 | 0.1178 | 272.77 |

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
| ADA/USDT:USDT | SHORT | 1989.0 | 0.2275 | 0.232526 | 0.214935 | False | False | 0.08 |
| AVAX/USDT:USDT | SHORT | 46.0 | 9.931 | 10.147738 | 9.389155 | False | False | 0.148 |
| BTC/USDT:USDT | SHORT | 0.0152 | 80888.0 | 81541.78618 | 79253.53455 | False | False | 0.076 |
| DOGE/USDT:USDT | SHORT | 7739.0 | 0.08199 | 0.083282 | 0.07876 | False | False | 0.155 |
| LINK/USDT:USDT | SHORT | 47.99 | 12.336 | 12.544368 | 11.81508 | False | False | 0.086 |
| SOL/USDT:USDT | SHORT | 4.5 | 107.5 | 109.721104 | 101.94724 | False | False | 0.086 |
| XRP/USDT:USDT | SHORT | 467.8 | 1.3406 | 1.361976 | 1.28716 | False | False | 0.061 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
