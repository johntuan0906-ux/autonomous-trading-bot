# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 04:42:20 · commit `390cacd`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `52` · nhịp tim cách đây 89.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3408.99 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 763 lệnh đóng, WR 56.36%, E(R) 0.019, PnL -37.04$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 534 | 53.37 | 1.025 | 0.95 | 0.007 | -63.13 |
| 14 ngày | 717 | 56.07 | 1.092 | 0.993 | 0.0237 | -10.56 |
| 30 ngày | 763 | 56.36 | 1.072 | 0.979 | 0.019 | -37.04 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.025 < 1.2; PF($) cua so 7 ngay = 0.950 < 1.1; PF(R) cua so 14 ngay = 1.092 < 1.2; PF($) cua so 14 ngay = 0.993 < 1.1; PF(R) cua so 30 ngay = 1.072 < 1.2; PF($) cua so 30 ngay = 0.979 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 340 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| 1000PEPE/USDT:USDT | LONG | 156494.0 | 0.0042109 | 0.004147 | 0.004371 | False | False | 0.236 |
| 1000SHIB/USDT:USDT | SHORT | 138888.5 | 0.00522 | 0.00521478 | 0.00513 | True | True | 0.528 |
| ADA/USDT:USDT | SHORT | 4428.0 | 0.2363 | 0.238558 | 0.230655 | False | False | 0.089 |
| AERO/USDT:USDT | SHORT | 972.5 | 0.9 | 0.910282 | 0.874295 | False | False | 0.0 |
| AIN/USDT:USDT | SHORT | 3765.0 | 0.04427 | 0.044194 | 0.04095 | True | True | 0.557 |
| AIOT/USDT:USDT | LONG | 10526.0 | 0.0557 | 0.05475 | 0.058075 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.206 |
| ALGO/USDT:USDT | SHORT | 3196.9 | 0.12086 | 0.12073914 | 0.11695 | True | True | 0.345 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
