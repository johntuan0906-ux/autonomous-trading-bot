# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 08:05:07 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `70904` · round `99` · nhịp tim cách đây 1.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4533.72 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 338 lệnh đóng, WR 65.38%, E(R) 0.0944, PnL 237.64$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 253 | 65.61 | 1.715 | 1.608 | 0.1226 | 251.73 |
| 14 ngày | 311 | 64.63 | 1.427 | 1.307 | 0.0858 | 185.36 |
| 30 ngày | 338 | 65.38 | 1.464 | 1.357 | 0.0944 | 237.64 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 151 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 3538.0 | 0.2321 | 0.234926 | 0.225035 | False | False | 0.212 |
| AVAX/USDT:USDT | SHORT | 72.0 | 10.042 | 10.18003 | 9.696925 | False | False | 0.21 |
| BTC/USDT:USDT | SHORT | 0.0367 | 81691.6 | 81963.390734 | 81012.123165 | False | False | 0.121 |
| DOGE/USDT:USDT | SHORT | 14970.0 | 0.08403 | 0.084698 | 0.08236 | False | False | 0.225 |
| LINK/USDT:USDT | SHORT | 38.485 | 12.742 | 12.729258000000002 | 12.4172 | True | True | 0.316 |
| SOL/USDT:USDT | SHORT | 5.55 | 109.39 | 111.191634 | 104.885915 | False | False | 0.105 |
| XRP/USDT:USDT | SHORT | 960.2 | 1.3792 | 1.389614 | 1.353165 | False | False | 0.058 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
