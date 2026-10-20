# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 14:54:13 · commit `9efcbe8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `83108` · round `20` · nhịp tim cách đây 53.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3289.14 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3294 lệnh đóng, WR 45.17%, E(R) 1.3338, PnL -993.65$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2603 | 42.07 | 6.374 | 0.719 | 1.6771 | -1092.44 |
| 14 ngày | 3065 | 43.82 | 5.685 | 0.793 | 1.43 | -1019.74 |
| 30 ngày | 3294 | 45.17 | 5.444 | 0.817 | 1.3338 | -993.65 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.719 < 1.1; PF($) cua so 14 ngay = 0.793 < 1.1; PF($) cua so 30 ngay = 0.817 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 445 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (14)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | LONG | 59523.0 | 0.005003 | 0.004961 | 0.005108 | False | False | 0.238 |
| AIOT/USDT:USDT | LONG | 3071.0 | 0.0571 | 0.056286 | 0.059135 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 1364.5 | 0.032219 | 0.033778999999999997 | 0.034509 | True | True | 2.203 |
| ALGO/USDT:USDT | LONG | 2500.0 | 0.11146 | 0.11046 | 0.11396 | False | False | 0.2 |
| APR/USDT:USDT | LONG | 2240.0 | 0.02829 | 0.027174 | 0.03108 | False | False | 0.251 |
| AR/USDT:USDT | LONG | 55.7 | 3.772 | 3.727168 | 3.88408 | False | False | 0.223 |
| ASTER/USDT:USDT | LONG | 459.0 | 0.7094 | 0.70396 | 0.723 | False | False | 0.092 |
| ATOM/USDT:USDT | LONG | 161.49 | 1.752 | 1.73652 | 1.7907 | False | False | 0.258 |
| AVAX/USDT:USDT | SHORT | 12.5 | 9.562 | 9.514311 | 9.320445 | True | True | 0.994 |
| AXS/USDT:USDT | SHORT | 158.0 | 0.999 | 0.998001 | 0.979275 | True | True | 0.38 |
| BNB/USDT:USDT | LONG | 0.01 | 729.89 | 726.887032 | 734.77242 | False | False | 0.0 |
| CRV/USDT:USDT | LONG | 505.2 | 0.3668 | 0.361852 | 0.37917 | False | False | 0.0 |
| CTSI/USDT:USDT | LONG | 7812.0 | 0.03068 | 0.03036 | 0.03148 | False | False | 0.094 |
| DASH/USDT:USDT | LONG | 4.392 | 50.08 | 49.510816 | 51.50296 | False | False | 0.158 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
