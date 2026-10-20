# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 15:54:14 · commit `c56d75f`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `83108` · round `35` · nhịp tim cách đây 27.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3303 lệnh đóng, WR 45.17%, E(R) 1.3313, PnL -996.01$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2612 | 42.08 | 6.354 | 0.719 | 1.6727 | -1094.8 |
| 14 ngày | 3074 | 43.82 | 5.67 | 0.792 | 1.427 | -1022.1 |
| 30 ngày | 3303 | 45.17 | 5.431 | 0.817 | 1.3313 | -996.01 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.719 < 1.1; PF($) cua so 14 ngay = 0.792 < 1.1; PF($) cua so 30 ngay = 0.817 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 452 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (14)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | LONG | 59523.0 | 0.005003 | 0.004961 | 0.005108 | False | False | 0.238 |
| AERO/USDT:USDT | SHORT | 251.0 | 0.8071 | 0.81706 | 0.7822 | False | False | 0.0 |
| APR/USDT:USDT | LONG | 1120.0 | 0.02829 | 0.028322 | 0.03108 | True | True | 0.529 |
| AR/USDT:USDT | LONG | 55.7 | 3.772 | 3.727168 | 3.88408 | False | False | 0.223 |
| ASTER/USDT:USDT | LONG | 459.0 | 0.7094 | 0.70396 | 0.723 | False | False | 0.092 |
| AXS/USDT:USDT | SHORT | 158.0 | 0.999 | 0.9939450000000001 | 0.979275 | True | True | 1.141 |
| BANK/USDT:USDT | LONG | 10869.0 | 0.02631 | 0.02608 | 0.026885 | False | False | 0.0 |
| BAT/USDT:USDT | LONG | 193.4 | 0.19913 | 0.19932913 | 0.215285 | True | True | 0.382 |
| BNB/USDT:USDT | LONG | 1.11 | 729.57 | 727.324394 | 735.184015 | False | False | 0.156 |
| BTR/USDT:USDT | LONG | 5208.0 | 0.04417 | 0.04369 | 0.04537 | False | False | 0.187 |
| CKB/USDT:USDT | SHORT | 156250.0 | 0.001428 | 0.001444 | 0.001388 | False | False | 0.0 |
| CRV/USDT:USDT | LONG | 505.2 | 0.3668 | 0.361852 | 0.37917 | False | False | 0.0 |
| CTSI/USDT:USDT | LONG | 7812.0 | 0.03068 | 0.03036 | 0.03148 | False | False | 0.094 |
| DASH/USDT:USDT | LONG | 4.392 | 50.08 | 49.510816 | 51.50296 | False | False | 0.158 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
