# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 23:47:22 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `53308` · round `4` · nhịp tim cách đây 34.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3927.51 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 537 lệnh đóng, WR 56.42%, E(R) 0.0157, PnL 30.01$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 399 | 52.88 | 1.049 | 1.016 | 0.0124 | 12.53 |
| 14 ngày | 506 | 55.73 | 1.048 | 1.005 | 0.0117 | 4.96 |
| 30 ngày | 537 | 56.42 | 1.063 | 1.027 | 0.0157 | 30.01 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.049 < 1.2; PF($) cua so 7 ngay = 1.016 < 1.1; PF(R) cua so 14 ngay = 1.048 < 1.2; PF($) cua so 14 ngay = 1.005 < 1.1; PF(R) cua so 30 ngay = 1.063 < 1.2; PF($) cua so 30 ngay = 1.027 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 238 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (10)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 192307.5 | 0.0086 | 0.0086086 | 0.008665 | True | True | 0.769 |
| 1000000MOG/USDT:USDT | LONG | 6983.2 | 0.1123 | 0.11241229999999999 | 0.11409 | True | True | 0.419 |
| 1000CHEEMS/USDT:USDT | LONG | 1250000.0 | 0.00053 | 0.00053053 | 0.00054 | True | True | 0.45 |
| 1000LUNC/USDT:USDT | LONG | 17241.0 | 0.05145 | 0.05162499999999999 | 0.052175 | True | True | 1.103 |
| 1000RATS/USDT:USDT | LONG | 21552.0 | 0.03671 | 0.036914 | 0.03729 | True | True | 1.379 |
| 1000XEC/USDT:USDT | LONG | 86207.0 | 0.007332 | 0.007378000000000001 | 0.007477 | True | True | 1.293 |
| 1INCH/USDT:USDT | LONG | 9328.0 | 0.09865 | 0.099192 | 0.09999 | True | True | 1.511 |
| AAVE/USDT:USDT | LONG | 6.4 | 170.6 | 169.057696 | 174.45576 | False | False | 0.0 |
| ACH/USDT:USDT | LONG | 87719.0 | 0.006154 | 0.00604 | 0.006439 | False | False | 0.0 |
| AERO/USDT:USDT | LONG | 587.1 | 0.9647 | 0.947668 | 1.00728 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
