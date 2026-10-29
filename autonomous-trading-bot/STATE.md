# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 30/10/2026 03:35:34 · commit `4642458`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `35964` · round `567` · nhịp tim cách đây 135.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3234.93 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2910 lệnh đóng, WR 41.03%, E(R) 0.2303, PnL -992.21$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 9 | 11.11 | 0.171 | 0.171 | -0.5144 | -55.55 |
| 14 ngày | 1973 | 32.69 | 2.173 | 0.561 | 0.3287 | -1210.32 |
| 30 ngày | 2864 | 40.71 | 1.862 | 0.799 | 0.2349 | -965.73 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.171 < 1.2; PF($) cua so 7 ngay = 0.171 < 1.1; PF($) cua so 14 ngay = 0.561 < 1.1; PF($) cua so 30 ngay = 0.799 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.2%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 731 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (5)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 21978.0 | 0.005276 | 0.00473 | 0.006368 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 650.0 | 0.20690000000000003 | 0.225952 | 0.116558 | False | False | 0.52 |
| AERO/USDT:USDT | LONG | 263.2 | 0.6900999999999999 | 0.660616 | 0.752668 | False | False | 0.648 |
| AIOT/USDT:USDT | LONG | 907.2 | 0.061799999999999994 | 0.061861799999999995 | 0.093547 | True | True | 78.757 |
| APT/USDT:USDT | SHORT | 145.5 | 0.7173 | 0.801032 | 0.312328 | False | False | 0.782 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
