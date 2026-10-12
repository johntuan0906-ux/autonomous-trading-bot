# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 03:51:31 · commit `53e7069`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `52` · nhịp tim cách đây 14.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 612 lệnh đóng, WR 55.07%, E(R) 0.0099, PnL -63.82$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 383 | 50.13 | 0.956 | 0.898 | -0.0123 | -89.91 |
| 14 ngày | 581 | 54.39 | 1.023 | 0.931 | 0.0061 | -88.86 |
| 30 ngày | 612 | 55.07 | 1.038 | 0.954 | 0.0099 | -63.82 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.956 < 1.2; PF($) cua so 7 ngay = 0.898 < 1.1; PF(R) cua so 14 ngay = 1.023 < 1.2; PF($) cua so 14 ngay = 0.931 < 1.1; PF(R) cua so 30 ngay = 1.038 < 1.2; PF($) cua so 30 ngay = 0.954 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 258 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 112866.5 | 0.0040823 | 0.0040863823 | 0.004192 | True | True | 0.512 |
| 1000SHIB/USDT:USDT | SHORT | 238095.0 | 0.005336 | 0.005378 | 0.005231 | False | False | 0.024 |
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.281 |
| ADA/USDT:USDT | SHORT | 4757.0 | 0.2426 | 0.244702 | 0.237345 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 882.9 | 0.8965 | 0.907826 | 0.868185 | False | False | 0.274 |
| AIN/USDT:USDT | LONG | 5656.0 | 0.04574 | 0.046327999999999994 | 0.04795 | True | True | 1.165 |
| AKE/USDT:USDT | SHORT | 21097.0 | 0.024146 | 0.02462 | 0.022961 | False | False | 0.148 |
| CAKE/USDT:USDT | LONG | 197.5 | 2.3038 | 2.3061038 | 2.36706 | True | True | 0.502 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
