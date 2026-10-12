# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 06:21:32 · commit `67bdc0b`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `88` · nhịp tim cách đây 1.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3672.6 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 635 lệnh đóng, WR 56.54%, E(R) 0.0286, PnL 56.95$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 406 | 52.71 | 1.068 | 1.035 | 0.0182 | 30.86 |
| 14 ngày | 604 | 55.96 | 1.103 | 1.024 | 0.0259 | 31.91 |
| 30 ngày | 635 | 56.54 | 1.112 | 1.041 | 0.0286 | 56.95 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.068 < 1.2; PF($) cua so 7 ngay = 1.035 < 1.1; PF(R) cua so 14 ngay = 1.103 < 1.2; PF($) cua so 14 ngay = 1.024 < 1.1; PF(R) cua so 30 ngay = 1.112 < 1.2; PF($) cua so 30 ngay = 1.041 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 280 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| AERO/USDT:USDT | SHORT | 447.6 | 0.8941 | 0.885785 | 0.866175 | True | True | 1.244 |
| AIN/USDT:USDT | LONG | 10482.0 | 0.04624 | 0.045286 | 0.048625 | False | False | 0.073 |
| AIOT/USDT:USDT | LONG | 8025.0 | 0.0551 | 0.053854 | 0.058215 | False | False | 0.241 |
| AKE/USDT:USDT | SHORT | 10548.5 | 0.024146 | 0.023862 | 0.022961 | True | True | 1.099 |
| ALT/USDT:USDT | SHORT | 56818.0 | 0.00788 | 0.008056 | 0.00744 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 4378.0 | 0.1484 | 0.150684 | 0.14269 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 744.4 | 0.8041 | 0.817532 | 0.77052 | False | False | 0.0 |
| ARB/USDT:USDT | SHORT | 3546.0 | 0.1816 | 0.18442 | 0.17455 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
