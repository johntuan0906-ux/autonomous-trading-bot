# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 15:24:13 · commit `f9fd247`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `83108` · round `27` · nhịp tim cách đây 150.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3283.98 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3296 lệnh đóng, WR 45.15%, E(R) 1.3326, PnL -996.4$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2605 | 42.03 | 6.362 | 0.718 | 1.6753 | -1095.2 |
| 14 ngày | 3067 | 43.79 | 5.676 | 0.792 | 1.4285 | -1022.49 |
| 30 ngày | 3296 | 45.15 | 5.436 | 0.816 | 1.3326 | -996.4 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.718 < 1.1; PF($) cua so 14 ngay = 0.792 < 1.1; PF($) cua so 30 ngay = 0.816 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 446 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (16)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 25879.5 | 0.0041723 | 0.0041764723 | 0.004292 | True | True | 0.366 |
| 1000SHIB/USDT:USDT | LONG | 59523.0 | 0.005003 | 0.004961 | 0.005108 | False | False | 0.238 |
| AERO/USDT:USDT | SHORT | 251.0 | 0.8071 | 0.81706 | 0.7822 | False | False | 0.0 |
| AIOT/USDT:USDT | LONG | 1535.5 | 0.0571 | 0.057157099999999995 | 0.059135 | True | True | 0.369 |
| AKE/USDT:USDT | LONG | 1364.5 | 0.032219 | 0.033847 | 0.034509 | True | True | 2.277 |
| ALGO/USDT:USDT | LONG | 2500.0 | 0.11146 | 0.11046 | 0.11396 | False | False | 0.2 |
| APR/USDT:USDT | LONG | 1120.0 | 0.02829 | 0.02831829 | 0.03108 | True | True | 0.314 |
| AR/USDT:USDT | LONG | 55.7 | 3.772 | 3.727168 | 3.88408 | False | False | 0.223 |
| ASTER/USDT:USDT | LONG | 459.0 | 0.7094 | 0.70396 | 0.723 | False | False | 0.092 |
| AVAX/USDT:USDT | SHORT | 12.5 | 9.562 | 9.494311 | 9.320445 | True | True | 1.201 |
| AXS/USDT:USDT | SHORT | 158.0 | 0.999 | 0.9959450000000001 | 0.979275 | True | True | 0.887 |
| BANK/USDT:USDT | LONG | 10869.0 | 0.02631 | 0.02608 | 0.026885 | False | False | 0.174 |
| BAT/USDT:USDT | LONG | 386.8 | 0.19913 | 0.192668 | 0.215285 | False | False | 0.0 |
| CRV/USDT:USDT | LONG | 505.2 | 0.3668 | 0.361852 | 0.37917 | False | False | 0.0 |
| CTSI/USDT:USDT | LONG | 7812.0 | 0.03068 | 0.03036 | 0.03148 | False | False | 0.094 |
| DASH/USDT:USDT | LONG | 4.392 | 50.08 | 49.510816 | 51.50296 | False | False | 0.158 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
