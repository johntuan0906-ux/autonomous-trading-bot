# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 01:51:29 · commit `bc59832`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `22` · nhịp tim cách đây 31.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 608 lệnh đóng, WR 55.1%, E(R) 0.0101, PnL -62.79$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 379 | 50.13 | 0.957 | 0.898 | -0.0122 | -88.88 |
| 14 ngày | 577 | 54.42 | 1.024 | 0.931 | 0.0063 | -87.84 |
| 30 ngày | 608 | 55.1 | 1.039 | 0.954 | 0.0101 | -62.79 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.957 < 1.2; PF($) cua so 7 ngay = 0.898 < 1.1; PF(R) cua so 14 ngay = 1.024 < 1.2; PF($) cua so 14 ngay = 0.931 < 1.1; PF(R) cua so 30 ngay = 1.039 < 1.2; PF($) cua so 30 ngay = 0.954 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 255 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000PEPE/USDT:USDT | LONG | 225733.0 | 0.0040823 | 0.004038 | 0.004192 | False | False | 0.251 |
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.281 |
| AERO/USDT:USDT | SHORT | 882.9 | 0.8965 | 0.907826 | 0.868185 | False | False | 0.15 |
| AIN/USDT:USDT | LONG | 11312.0 | 0.04574 | 0.044856 | 0.04795 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 2413.0 | 0.1522 | 0.1520478 | 0.14702 | True | True | 0.338 |
| AR/USDT:USDT | SHORT | 95.1 | 4.099 | 4.047293 | 3.967535 | True | True | 1.483 |
| CAKE/USDT:USDT | LONG | 395.0 | 2.3038 | 2.278496 | 2.36706 | False | False | 0.008 |
| DOGE/USDT:USDT | SHORT | 14124.0 | 0.08466 | 0.085368 | 0.08289 | False | False | 0.056 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
