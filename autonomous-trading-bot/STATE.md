# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 23:17:20 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `53308` · round `None` · nhịp tim cách đây 27.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 532 lệnh đóng, WR 56.39%, E(R) 0.0018, PnL -8.81$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 394 | 52.79 | 0.975 | 0.967 | -0.0064 | -26.29 |
| 14 ngày | 501 | 55.69 | 0.988 | 0.967 | -0.0031 | -33.85 |
| 30 ngày | 532 | 56.39 | 1.007 | 0.992 | 0.0018 | -8.81 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.975 < 1.2; PF($) cua so 7 ngay = 0.967 < 1.1; PF(R) cua so 14 ngay = 0.988 < 1.2; PF($) cua so 14 ngay = 0.967 < 1.1; PF(R) cua so 30 ngay = 1.007 < 1.2; PF($) cua so 30 ngay = 0.992 < 1.1
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
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (11)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 208333.0 | 0.00857 | 0.008588 | 0.00863 | True | True | 1.25 |
| 1000CHEEMS/USDT:USDT | LONG | 1111111.0 | 0.0005265 | 0.00052905 | 0.000536 | True | True | 1.067 |
| 1000LUNC/USDT:USDT | LONG | 17241.0 | 0.05145 | 0.051565 | 0.052175 | True | True | 0.897 |
| 1000PEPE/USDT:USDT | LONG | 167224.0 | 0.0041089 | 0.00415155 | 0.004184 | True | True | 1.926 |
| 1000RATS/USDT:USDT | LONG | 21551.5 | 0.03671 | 0.036874000000000004 | 0.03729 | True | True | 1.207 |
| 1000XEC/USDT:USDT | LONG | 86206.5 | 0.007332 | 0.007365999999999999 | 0.007477 | True | True | 1.086 |
| 1INCH/USDT:USDT | LONG | 18656.0 | 0.09865 | 0.098114 | 0.09999 | False | False | 0.0 |
| 4/USDT:USDT | LONG | 37878.5 | 0.01681 | 0.017014 | 0.01714 | True | True | 2.045 |
| AAVE/USDT:USDT | LONG | 6.4 | 170.6 | 169.057696 | 174.45576 | False | False | 0.0 |
| ACH/USDT:USDT | LONG | 87719.0 | 0.006154 | 0.00604 | 0.006439 | False | False | 0.0 |
| ADA/USDT:USDT | LONG | 2676.5 | 0.2519 | 0.253966 | 0.25657 | True | True | 1.606 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
