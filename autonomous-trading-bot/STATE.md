# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 21:07:09 · commit `?`
- **Chế độ**: **LIVE (TIỀN THẬT)** · `DRY_RUN=False` · `LIVE_CONFIRM=True`
- **Bot**: pid `30756` · round `81` · nhịp tim cách đây 16.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 22.84 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 411 lệnh đóng, WR 62.29%, E(R) 0.0571, PnL 123.14$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 286 | 57.34 | 1.24 | 1.112 | 0.0518 | 59.59 |
| 14 ngày | 380 | 61.84 | 1.26 | 1.136 | 0.0552 | 98.09 |
| 30 ngày | 411 | 62.29 | 1.26 | 1.151 | 0.0571 | 123.14 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.5%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `2` · trần size `1000.0` USDT
- Learner: 192 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** ⬅ **hiện tại** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (4)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 36.0 | 0.2363 | 0.239414 | 0.228515 | False | False | 0.225 |
| AVAX/USDT:USDT | SHORT | 0.5 | 10.287 | 10.213616 | 10.00392 | True | True | 1.148 |
| SOL/USDT:USDT | SHORT | 0.1 | 109.81 | 110.901942 | 107.080145 | False | False | 0.0 |
| XRP/USDT:USDT | SHORT | 9.2 | 1.3752 | 1.387662 | 1.344045 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
