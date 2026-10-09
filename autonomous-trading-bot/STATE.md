# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 08:35:07 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `70904` · round `142` · nhịp tim cách đây 18.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4516.55 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 342 lệnh đóng, WR 65.2%, E(R) 0.0882, PnL 220.18$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 257 | 65.37 | 1.644 | 1.539 | 0.1139 | 234.26 |
| 14 ngày | 314 | 64.65 | 1.409 | 1.29 | 0.0827 | 178.28 |
| 30 ngày | 342 | 65.2 | 1.426 | 1.321 | 0.0882 | 220.18 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 155 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 3538.0 | 0.2321 | 0.234926 | 0.225035 | False | False | 0.212 |
| AVAX/USDT:USDT | SHORT | 72.0 | 10.042 | 10.18003 | 9.696925 | False | False | 0.21 |
| BTC/USDT:USDT | SHORT | 0.0367 | 81691.6 | 81963.390734 | 81012.123165 | False | False | 0.136 |
| DOGE/USDT:USDT | SHORT | 15974.0 | 0.08457 | 0.085196 | 0.083005 | False | False | 0.128 |
| SOL/USDT:USDT | SHORT | 5.77 | 109.32 | 111.05275 | 104.988125 | False | False | 0.162 |
| XRP/USDT:USDT | SHORT | 1054.4 | 1.3879 | 1.397384 | 1.36419 | False | False | 0.169 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
