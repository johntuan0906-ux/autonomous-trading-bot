# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 14:08:53 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `59544` · round `3` · nhịp tim cách đây 124.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4190.56 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 467 lệnh đóng, WR 58.24%, E(R) 0.011, PnL 30.36$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 329 | 54.71 | 1.02 | 1.021 | 0.0049 | 12.88 |
| 14 ngày | 436 | 57.57 | 1.025 | 1.006 | 0.006 | 5.31 |
| 30 ngày | 467 | 58.24 | 1.045 | 1.033 | 0.011 | 30.36 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.020 < 1.2; PF($) cua so 7 ngay = 1.021 < 1.1; PF(R) cua so 14 ngay = 1.025 < 1.2; PF($) cua so 14 ngay = 1.006 < 1.1; PF(R) cua so 30 ngay = 1.045 < 1.2; PF($) cua so 30 ngay = 1.033 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 221 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (10)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 208333.0 | 0.00858 | 0.008532 | 0.0087 | False | False | 0.208 |
| 1000000MOG/USDT:USDT | LONG | 7462.65 | 0.1107 | 0.111065 | 0.112375 | True | True | 1.045 |
| 1000CAT/USDT:USDT | SHORT | 714285.0 | 0.002035 | 0.002049 | 0.002 | False | False | 0.286 |
| 1000CHEEMS/USDT:USDT | LONG | 1250000.0 | 0.000521 | 0.0005227000000000001 | 0.000531 | True | True | 0.925 |
| 1000FLOKI/USDT:USDT | LONG | 32468.0 | 0.02708 | 0.027223 | 0.027465 | True | True | 1.429 |
| 1000LUNC/USDT:USDT | LONG | 14705.5 | 0.05147 | 0.05152147 | 0.05232 | True | True | 0.471 |
| 1000PEPE/USDT:USDT | LONG | 231481.0 | 0.0040136 | 0.0040226 | 0.004069 | True | True | 0.917 |
| 1000RATS/USDT:USDT | LONG | 38461.0 | 0.03673 | 0.03647 | 0.03738 | False | False | 0.0 |
| 1INCH/USDT:USDT | LONG | 8278.0 | 0.09769 | 0.097968 | 0.0992 | True | True | 0.96 |
| 1MBABYDOGE/USDT:USDT | LONG | 2173913.0 | 0.0003853 | 0.00038585 | 0.00039 | True | True | 0.739 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
