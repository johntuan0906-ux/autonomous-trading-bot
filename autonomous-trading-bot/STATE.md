# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 02:51:30 · commit `273887a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `37` · nhịp tim cách đây 40.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 610 lệnh đóng, WR 55.25%, E(R) 0.0116, PnL -53.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 381 | 50.39 | 0.965 | 0.908 | -0.0097 | -79.89 |
| 14 ngày | 579 | 54.58 | 1.03 | 0.938 | 0.0078 | -78.84 |
| 30 ngày | 610 | 55.25 | 1.044 | 0.961 | 0.0116 | -53.8 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.965 < 1.2; PF($) cua so 7 ngay = 0.908 < 1.1; PF(R) cua so 14 ngay = 1.030 < 1.2; PF($) cua so 14 ngay = 0.938 < 1.1; PF(R) cua so 30 ngay = 1.044 < 1.2; PF($) cua so 30 ngay = 0.961 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 256 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 112866.5 | 0.0040823 | 0.0040863823 | 0.004192 | True | True | 0.449 |
| 1000SHIB/USDT:USDT | SHORT | 238095.0 | 0.005336 | 0.005378 | 0.005231 | False | False | 0.024 |
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.281 |
| AERO/USDT:USDT | SHORT | 882.9 | 0.8965 | 0.907826 | 0.868185 | False | False | 0.274 |
| AIN/USDT:USDT | LONG | 11312.0 | 0.04574 | 0.044856 | 0.04795 | False | False | 0.226 |
| CAKE/USDT:USDT | LONG | 395.0 | 2.3038 | 2.278496 | 2.36706 | False | False | 0.17 |
| DOGE/USDT:USDT | SHORT | 14124.0 | 0.08466 | 0.085368 | 0.08289 | False | False | 0.056 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
