# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 13:54:13 · commit `dfece25`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `83108` · round `5` · nhịp tim cách đây 136.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3297.59 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3284 lệnh đóng, WR 45.19%, E(R) 1.3386, PnL -987.98$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2593 | 42.07 | 6.407 | 0.72 | 1.6845 | -1086.77 |
| 14 ngày | 3055 | 43.83 | 5.71 | 0.793 | 1.4354 | -1014.07 |
| 30 ngày | 3284 | 45.19 | 5.467 | 0.818 | 1.3386 | -987.98 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.720 < 1.1; PF($) cua so 14 ngay = 0.793 < 1.1; PF($) cua so 30 ngay = 0.818 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 438 lần cập nhật trọng số · Hội đồng AI: **6 model**

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
| AERO/USDT:USDT | SHORT | 225.7 | 0.804 | 0.815074 | 0.776315 | False | False | 0.027 |
| AIOT/USDT:USDT | LONG | 3164.0 | 0.0564 | 0.05561 | 0.058375 | False | False | 0.127 |
| ALGO/USDT:USDT | LONG | 1299.35 | 0.11174 | 0.11185174 | 0.114145 | True | True | 0.499 |
| AR/USDT:USDT | LONG | 55.7 | 3.772 | 3.727168 | 3.88408 | False | False | 0.0 |
| ARB/USDT:USDT | LONG | 751.6 | 0.1992 | 0.195874 | 0.207515 | False | False | 0.0 |
| ATOM/USDT:USDT | LONG | 161.49 | 1.752 | 1.73652 | 1.7907 | False | False | 0.258 |
| AVAX/USDT:USDT | SHORT | 25.0 | 9.562 | 9.658622 | 9.320445 | False | False | 0.021 |
| AXS/USDT:USDT | SHORT | 316.0 | 0.999 | 1.00689 | 0.979275 | False | False | 0.127 |
| BANK/USDT:USDT | LONG | 5434.5 | 0.02623 | 0.02625623 | 0.026805 | True | True | 0.565 |
| BNB/USDT:USDT | LONG | 1.15 | 730.3 | 728.138344 | 735.70414 | False | False | 0.125 |
| CRV/USDT:USDT | LONG | 505.2 | 0.3668 | 0.361852 | 0.37917 | False | False | 0.0 |
| CYBER/USDT:USDT | LONG | 299.9 | 0.316 | 0.316316 | 0.32642 | True | True | 0.48 |
| DASH/USDT:USDT | LONG | 4.392 | 50.08 | 49.510816 | 51.50296 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
