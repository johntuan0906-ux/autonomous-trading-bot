# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/11/2026 06:46:09 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `80472` · round `245` · nhịp tim cách đây 28.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2996 lệnh đóng, WR 41.09%, E(R) 0.2353, PnL -1040.27$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 74 | 48.65 | 2.383 | 1.059 | 0.4579 | 9.87 |
| 14 ngày | 89 | 42.7 | 1.939 | 0.737 | 0.3701 | -69.41 |
| 30 ngày | 2565 | 37.74 | 1.951 | 0.74 | 0.2708 | -1137.35 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 1.059 < 1.1; PF($) cua so 14 ngay = 0.737 < 1.1; PF($) cua so 30 ngay = 0.740 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 762 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (13)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ACE/USDT:USDT | LONG | 1058.0 | 0.1203 | 0.112788 | 0.127224 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 701.0 | 0.1733 | 0.179 | 0.1619 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 166.67 | 0.5872 | 0.5866128 | 0.553612 | True | True | 1.304 |
| AKE/USDT:USDT | LONG | 8888.0 | 0.005355 | 0.004905 | 0.006255 | False | False | 0.055 |
| ALT/USDT:USDT | SHORT | 27777.0 | 0.00518 | 0.005324 | 0.004892 | False | False | 0.208 |
| APR/USDT:USDT | SHORT | 2339.0 | 0.03917 | 0.04088 | 0.03575 | False | False | 0.69 |
| AVAX/USDT:USDT | SHORT | 16.0 | 7.861 | 8.100064 | 7.382872 | False | False | 0.067 |
| AXL/USDT:USDT | SHORT | 2754.8 | 0.034 | 0.035452 | 0.031096 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 3875.0 | 0.02236 | 0.023392 | 0.020296 | False | False | 0.0 |
| BAT/USDT:USDT | SHORT | 698.8 | 0.11729 | 0.123014 | 0.105842 | False | False | 0.0 |
| BCH/USDT:USDT | SHORT | 0.539 | 239.84 | 247.252568 | 225.014864 | False | False | 0.136 |
| BR/USDT:USDT | SHORT | 209.3 | 0.4476 | 0.4471524 | 0.4209 | True | True | 1.925 |
| GTC/USDT:USDT | SHORT | 159.4 | 0.1736 | 0.18614 | 0.14852 | False | False | 0.455 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
