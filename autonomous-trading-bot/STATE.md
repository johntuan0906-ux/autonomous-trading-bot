# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 19:12:39 · commit `f71668a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `34912` · round `None` · nhịp tim cách đây 6.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 834 lệnh đóng, WR 58.03%, E(R) 0.0202, PnL -13.76$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 605 | 56.03 | 1.037 | 0.972 | 0.0101 | -39.85 |
| 14 ngày | 788 | 57.87 | 1.097 | 1.007 | 0.0245 | 12.71 |
| 30 ngày | 834 | 58.03 | 1.078 | 0.993 | 0.0202 | -13.76 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.037 < 1.2; PF($) cua so 7 ngay = 0.972 < 1.1; PF(R) cua so 14 ngay = 1.097 < 1.2; PF($) cua so 14 ngay = 1.007 < 1.1; PF(R) cua so 30 ngay = 1.078 < 1.2; PF($) cua so 30 ngay = 0.993 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 378 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 113122.0 | 0.0041822 | 0.0041881 | 0.004292 | True | True | 0.633 |
| 1000SHIB/USDT:USDT | SHORT | 294117.0 | 0.005161 | 0.005195 | 0.005076 | False | False | 0.0 |
| AERO/USDT:USDT | LONG | 448.25 | 0.8972 | 0.908123 | 0.925085 | True | True | 1.479 |
| AIN/USDT:USDT | SHORT | 5656.0 | 0.03982 | 0.039552 | 0.03761 | True | True | 0.803 |
| AKE/USDT:USDT | LONG | 13404.0 | 0.025596 | 0.02485 | 0.027461 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 6596.3 | 0.12076 | 0.122276 | 0.11697 | False | False | 0.086 |
| AR/USDT:USDT | SHORT | 181.2 | 3.887 | 3.942172 | 3.74907 | False | False | 0.0 |
| AXL/USDT:USDT | LONG | 4436.5 | 0.0625 | 0.060246 | 0.068135 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
