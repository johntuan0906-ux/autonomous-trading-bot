# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 05:12:21 · commit `8fe5946`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `60` · nhịp tim cách đây 17.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 765 lệnh đóng, WR 56.47%, E(R) 0.0194, PnL -33.28$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 536 | 53.54 | 1.028 | 0.953 | 0.0077 | -59.37 |
| 14 ngày | 719 | 56.19 | 1.094 | 0.996 | 0.0241 | -6.8 |
| 30 ngày | 765 | 56.47 | 1.074 | 0.981 | 0.0194 | -33.28 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.028 < 1.2; PF($) cua so 7 ngay = 0.953 < 1.1; PF(R) cua so 14 ngay = 1.094 < 1.2; PF($) cua so 14 ngay = 0.996 < 1.1; PF(R) cua so 30 ngay = 1.074 < 1.2; PF($) cua so 30 ngay = 0.981 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 342 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 156494.0 | 0.0042109 | 0.004147 | 0.004371 | False | False | 0.236 |
| ADA/USDT:USDT | SHORT | 4428.0 | 0.2363 | 0.238558 | 0.230655 | False | False | 0.089 |
| AERO/USDT:USDT | SHORT | 972.5 | 0.9 | 0.910282 | 0.874295 | False | False | 0.146 |
| AIOT/USDT:USDT | LONG | 10526.0 | 0.0557 | 0.05475 | 0.058075 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.206 |
| ALGO/USDT:USDT | SHORT | 3196.9 | 0.12086 | 0.12073914 | 0.11695 | True | True | 0.345 |
| APT/USDT:USDT | SHORT | 389.4 | 0.8413 | 0.8404587 | 0.8092 | True | True | 0.46 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
