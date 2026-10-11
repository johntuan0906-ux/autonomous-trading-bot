# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 13:08:23 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `74908` · round `1` · nhịp tim cách đây 53.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4190.39 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 465 lệnh đóng, WR 58.49%, E(R) 0.0154, PnL 50.79$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 327 | 55.05 | 1.047 | 1.057 | 0.0112 | 33.31 |
| 14 ngày | 434 | 57.83 | 1.045 | 1.032 | 0.0107 | 25.75 |
| 30 ngày | 465 | 58.49 | 1.064 | 1.056 | 0.0154 | 50.79 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.047 < 1.2; PF($) cua so 7 ngay = 1.057 < 1.1; PF(R) cua so 14 ngay = 1.045 < 1.2; PF($) cua so 14 ngay = 1.032 < 1.1; PF(R) cua so 30 ngay = 1.064 < 1.2; PF($) cua so 30 ngay = 1.056 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 220 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000MOG/USDT:USDT | LONG | 14925.3 | 0.1107 | 0.11003 | 0.112375 | False | False | 0.149 |
| 1000CAT/USDT:USDT | SHORT | 714285.0 | 0.002035 | 0.002049 | 0.002 | False | False | 0.143 |
| 1000CHEEMS/USDT:USDT | LONG | 1250000.0 | 0.000521 | 0.0005215209999999999 | 0.000531 | True | True | 0.325 |
| 1000FLOKI/USDT:USDT | LONG | 64935.0 | 0.02708 | 0.026926 | 0.027465 | False | False | 0.13 |
| 1000PEPE/USDT:USDT | LONG | 462962.0 | 0.0040136 | 0.003992 | 0.004069 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 454545.0 | 0.005401 | 0.005423 | 0.005346 | False | False | 0.0 |
| 1INCH/USDT:USDT | LONG | 16556.0 | 0.09769 | 0.097086 | 0.0992 | False | False | 0.0 |
| 1MBABYDOGE/USDT:USDT | LONG | 4347826.0 | 0.0003853 | 0.000383 | 0.00039 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
