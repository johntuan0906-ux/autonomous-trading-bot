# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 01:21:29 · commit `15ff00a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `14` · nhịp tim cách đây 101.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3619.33 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 605 lệnh đóng, WR 54.88%, E(R) 0.009, PnL -70.07$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 376 | 49.73 | 0.95 | 0.889 | -0.0142 | -96.16 |
| 14 ngày | 574 | 54.18 | 1.019 | 0.926 | 0.0051 | -95.11 |
| 30 ngày | 605 | 54.88 | 1.034 | 0.949 | 0.009 | -70.07 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.950 < 1.2; PF($) cua so 7 ngay = 0.889 < 1.1; PF(R) cua so 14 ngay = 1.019 < 1.2; PF($) cua so 14 ngay = 0.926 < 1.1; PF(R) cua so 30 ngay = 1.034 < 1.2; PF($) cua so 30 ngay = 0.949 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 253 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000PEPE/USDT:USDT | LONG | 225733.0 | 0.0040823 | 0.004038 | 0.004192 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 217391.0 | 0.005336 | 0.005382 | 0.005221 | False | False | 0.152 |
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.281 |
| AR/USDT:USDT | SHORT | 95.1 | 4.099 | 4.047293 | 3.967535 | True | True | 1.483 |
| ASTER/USDT:USDT | SHORT | 986.5 | 0.7017 | 0.7009983 | 0.68903 | True | True | 0.395 |
| CAKE/USDT:USDT | LONG | 395.0 | 2.3038 | 2.278496 | 2.36706 | False | False | 0.008 |
| CRV/USDT:USDT | SHORT | 781.0 | 0.3505 | 0.350001 | 0.334495 | True | True | 0.578 |
| DOGE/USDT:USDT | SHORT | 14124.0 | 0.08466 | 0.085368 | 0.08289 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
