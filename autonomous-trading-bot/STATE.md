# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 21:19:40 · commit `e3cf9bf`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `90444` · round `7` · nhịp tim cách đây 7.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3492.72 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 726 lệnh đóng, WR 56.75%, E(R) 0.0285, PnL 25.08$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 497 | 53.72 | 1.074 | 0.999 | 0.02 | -1.01 |
| 14 ngày | 680 | 56.47 | 1.135 | 1.035 | 0.0341 | 51.56 |
| 30 ngày | 726 | 56.75 | 1.11 | 1.015 | 0.0285 | 25.08 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.074 < 1.2; PF($) cua so 7 ngay = 0.999 < 1.1; PF(R) cua so 14 ngay = 1.135 < 1.2; PF($) cua so 14 ngay = 1.035 < 1.1; PF(R) cua so 30 ngay = 1.110 < 1.2; PF($) cua so 30 ngay = 1.015 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 324 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 78616.0 | 0.0041846 | 0.0042133 | 0.004345 | True | True | 0.951 |
| ACE/USDT:USDT | LONG | 1803.5 | 0.1884 | 0.19081399999999998 | 0.19533 | True | True | 1.371 |
| AIN/USDT:USDT | SHORT | 13927.0 | 0.04236 | 0.043078 | 0.040565 | False | False | 0.125 |
| APE/USDT:USDT | SHORT | 4582.0 | 0.1491 | 0.151282 | 0.143645 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 675.1 | 0.8217 | 0.836512 | 0.78467 | False | False | 0.061 |
| ATOM/USDT:USDT | SHORT | 366.08 | 1.821 | 1.848316 | 1.75271 | False | False | 0.0 |
| QNT/USDT:USDT | SHORT | 1.7 | 209.21 | 215.041596 | 194.63101 | False | False | 0.024 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
