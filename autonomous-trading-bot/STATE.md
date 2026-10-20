# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 14:24:13 · commit `f64620d`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `83108` · round `13` · nhịp tim cách đây 39.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3292 lệnh đóng, WR 45.17%, E(R) 1.3345, PnL -991.37$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2601 | 42.06 | 6.38 | 0.719 | 1.6782 | -1090.16 |
| 14 ngày | 3063 | 43.81 | 5.689 | 0.793 | 1.4307 | -1017.46 |
| 30 ngày | 3292 | 45.17 | 5.448 | 0.817 | 1.3345 | -991.37 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.719 < 1.1; PF($) cua so 14 ngay = 0.793 < 1.1; PF($) cua so 30 ngay = 0.817 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 443 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (15)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 51759.0 | 0.0041723 | 0.004124 | 0.004292 | False | False | 0.091 |
| 1000SHIB/USDT:USDT | LONG | 59523.0 | 0.005003 | 0.004961 | 0.005108 | False | False | 0.238 |
| AIOT/USDT:USDT | LONG | 3071.0 | 0.0571 | 0.056286 | 0.059135 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 2729.0 | 0.032219 | 0.031303 | 0.034509 | False | False | 0.053 |
| APE/USDT:USDT | LONG | 1.0 | 0.1452 | 0.142884 | 0.14889 | False | False | 0.0 |
| APR/USDT:USDT | LONG | 2240.0 | 0.02829 | 0.027174 | 0.03108 | False | False | 0.0 |
| AR/USDT:USDT | LONG | 55.7 | 3.772 | 3.727168 | 3.88408 | False | False | 0.178 |
| ATOM/USDT:USDT | LONG | 161.49 | 1.752 | 1.73652 | 1.7907 | False | False | 0.258 |
| AVAX/USDT:USDT | SHORT | 12.5 | 9.562 | 9.552437999999999 | 9.320445 | True | True | 0.424 |
| AXS/USDT:USDT | SHORT | 316.0 | 0.999 | 1.00689 | 0.979275 | False | False | 0.253 |
| BANK/USDT:USDT | LONG | 2717.25 | 0.02623 | 0.02625623 | 0.026805 | True | True | 2.287 |
| BCH/USDT:USDT | LONG | 1.073 | 277.8 | 275.472242 | 283.619395 | False | False | 0.0 |
| CRV/USDT:USDT | LONG | 505.2 | 0.3668 | 0.361852 | 0.37917 | False | False | 0.0 |
| CTSI/USDT:USDT | LONG | 7812.0 | 0.03068 | 0.03036 | 0.03148 | False | False | 0.0 |
| DASH/USDT:USDT | LONG | 4.392 | 50.08 | 49.510816 | 51.50296 | False | False | 0.158 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
