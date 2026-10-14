# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 22:09:07 · commit `a868713`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3836` · round `7` · nhịp tim cách đây 83.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 858 lệnh đóng, WR 58.28%, E(R) 0.0205, PnL -6.25$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 629 | 56.44 | 1.04 | 0.979 | 0.0109 | -32.34 |
| 14 ngày | 812 | 58.13 | 1.096 | 1.011 | 0.0247 | 20.23 |
| 30 ngày | 858 | 58.28 | 1.078 | 0.997 | 0.0205 | -6.25 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.040 < 1.2; PF($) cua so 7 ngay = 0.979 < 1.1; PF(R) cua so 14 ngay = 1.096 < 1.2; PF($) cua so 14 ngay = 1.011 < 1.1; PF(R) cua so 30 ngay = 1.078 < 1.2; PF($) cua so 30 ngay = 0.997 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 383 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| 1000PEPE/USDT:USDT | SHORT | 166112.0 | 0.0040408 | 0.004101 | 0.003891 | False | False | 0.148 |
| ADA/USDT:USDT | SHORT | 3021.0 | 0.2276 | 0.23091 | 0.219325 | False | False | 0.272 |
| AERO/USDT:USDT | SHORT | 322.9 | 0.8688 | 0.864743 | 0.830085 | True | True | 0.762 |
| AIN/USDT:USDT | SHORT | 9242.0 | 0.03853 | 0.039612 | 0.035825 | False | False | 0.203 |
| ALGO/USDT:USDT | SHORT | 2340.8 | 0.11693 | 0.11681307 | 0.11159 | True | True | 0.501 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.0 |
| AXS/USDT:USDT | SHORT | 382.0 | 1.097 | 1.08654 | 1.0643 | True | True | 1.3 |
| BANK/USDT:USDT | SHORT | 19531.0 | 0.02688 | 0.026628 | 0.02624 | True | True | 1.484 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
