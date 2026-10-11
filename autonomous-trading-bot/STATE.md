# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 14:38:39 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `74908` · round `11` · nhịp tim cách đây 149.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 476 lệnh đóng, WR 59.03%, E(R) 0.0173, PnL 61.46$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 338 | 55.92 | 1.059 | 1.073 | 0.014 | 43.98 |
| 14 ngày | 445 | 58.43 | 1.055 | 1.044 | 0.0129 | 36.41 |
| 30 ngày | 476 | 59.03 | 1.072 | 1.066 | 0.0173 | 61.46 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.059 < 1.2; PF($) cua so 7 ngay = 1.073 < 1.1; PF(R) cua so 14 ngay = 1.055 < 1.2; PF($) cua so 14 ngay = 1.044 < 1.1; PF(R) cua so 30 ngay = 1.072 < 1.2; PF($) cua so 30 ngay = 1.066 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 224 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (5)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 208333.0 | 0.00858 | 0.008532 | 0.0087 | False | False | 0.208 |
| 1000000MOG/USDT:USDT | LONG | 7462.65 | 0.1107 | 0.111165 | 0.112375 | True | True | 1.194 |
| 1000CAT/USDT:USDT | SHORT | 714285.0 | 0.002035 | 0.002049 | 0.002 | False | False | 0.286 |
| 1000RATS/USDT:USDT | LONG | 38461.0 | 0.03672 | 0.03646 | 0.03737 | False | False | 0.0 |
| 1INCH/USDT:USDT | LONG | 8278.0 | 0.09769 | 0.097938 | 0.0992 | True | True | 0.911 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
