# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 07:05:06 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `70904` · round `13` · nhịp tim cách đây 25.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 336 lệnh đóng, WR 65.18%, E(R) 0.0938, PnL 233.51$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 251 | 65.34 | 1.705 | 1.598 | 0.1219 | 247.6 |
| 14 ngày | 310 | 64.19 | 1.398 | 1.279 | 0.0815 | 171.19 |
| 30 ngày | 336 | 65.18 | 1.458 | 1.35 | 0.0938 | 233.51 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 149 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 3538.0 | 0.2321 | 0.234926 | 0.225035 | False | False | 0.106 |
| AVAX/USDT:USDT | SHORT | 72.0 | 10.042 | 10.18003 | 9.696925 | False | False | 0.022 |
| BTC/USDT:USDT | SHORT | 0.0367 | 81691.6 | 81963.390734 | 81012.123165 | False | False | 0.121 |
| DOGE/USDT:USDT | SHORT | 14970.0 | 0.08403 | 0.084698 | 0.08236 | False | False | 0.12 |
| SOL/USDT:USDT | SHORT | 4.7 | 109.48 | 111.60358 | 104.17105 | False | False | 0.071 |
| XRP/USDT:USDT | SHORT | 960.2 | 1.3792 | 1.389614 | 1.353165 | False | False | 0.058 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
