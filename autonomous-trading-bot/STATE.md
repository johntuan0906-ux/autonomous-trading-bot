# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 19:06:46 · commit `?`
- **Chế độ**: **LIVE (TIỀN THẬT)** · `DRY_RUN=False` · `LIVE_CONFIRM=True`
- **Bot**: pid `76676` · round `165` · nhịp tim cách đây 26.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 22.5 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 399 lệnh đóng, WR 61.15%, E(R) 0.0452, PnL 122.54$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 296 | 58.45 | 1.214 | 1.183 | 0.0454 | 99.8 |
| 14 ngày | 368 | 60.6 | 1.193 | 1.135 | 0.0422 | 97.49 |
| 30 ngày | 399 | 61.15 | 1.2 | 1.15 | 0.0452 | 122.54 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 14 ngay = 1.193 < 1.2
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.5%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `2` · trần size `1000.0` USDT
- Learner: 184 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| AVAX/USDT:USDT | SHORT | 0.5 | 10.443 | 10.429407000000001 | 10.180965 | True | True | 0.63 |
| DOGE/USDT:USDT | SHORT | 88.5 | 0.08531 | 0.08518200000000001 | 0.08375 | True | True | 0.705 |
| SOL/USDT:USDT | SHORT | 0.12 | 111.19 | 112.118322 | 108.869195 | False | False | 0.129 |
| XRP/USDT:USDT | SHORT | 4.6 | 1.4054 | 1.4039946 | 1.37552 | True | True | 0.602 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
