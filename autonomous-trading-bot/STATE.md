# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 00:02:58 · commit `f08a2f9`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `72180` · round `1` · nhịp tim cách đây 38.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: None USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 301 lệnh đóng, WR 67.11%, E(R) 0.1178, PnL 272.77$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 223 | 67.71 | 1.935 | 1.834 | 0.1471 | 273.21 |
| 14 ngày | 278 | 66.55 | 1.573 | 1.434 | 0.1076 | 217.67 |
| 30 ngày | 301 | 67.11 | 1.616 | 1.492 | 0.1178 | 272.77 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 144 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (3)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 2.0 | 0.2324 | 0.230267 | 0.219565 | True | True | 0.915 |
| DOGE/USDT:USDT | SHORT | 1.0 | 0.08314 | 0.082871 | 0.079835 | True | True | 0.703 |
| SOL/USDT:USDT | SHORT | 0.01 | 108.84 | 108.73116 | 102.181875 | True | True | 0.454 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
