# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 02:35:04 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `81208` · round `96` · nhịp tim cách đây 18.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4594.33 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 322 lệnh đóng, WR 66.46%, E(R) 0.1021, PnL 247.19$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 237 | 67.09 | 1.801 | 1.689 | 0.1348 | 261.27 |
| 14 ngày | 299 | 65.89 | 1.456 | 1.332 | 0.0915 | 192.08 |
| 30 ngày | 322 | 66.46 | 1.504 | 1.392 | 0.1021 | 247.19 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 146 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Vị thế đang quản lý (2)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 1917.0 | 0.2286 | 0.233814 | 0.215565 | False | False | 0.038 |
| LINK/USDT:USDT | SHORT | 46.11 | 12.378 | 12.594856 | 11.83586 | False | False | 0.042 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
