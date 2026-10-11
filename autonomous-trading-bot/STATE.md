# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 01:47:28 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `53308` · round `18` · nhịp tim cách đây 186.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3839.12 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 546 lệnh đóng, WR 56.96%, E(R) 0.0231, PnL 71.98$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 408 | 53.68 | 1.09 | 1.067 | 0.0224 | 54.5 |
| 14 ngày | 515 | 56.31 | 1.08 | 1.045 | 0.0197 | 46.93 |
| 30 ngày | 546 | 56.96 | 1.093 | 1.063 | 0.0231 | 71.98 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.090 < 1.2; PF($) cua so 7 ngay = 1.067 < 1.1; PF(R) cua so 14 ngay = 1.080 < 1.2; PF($) cua so 14 ngay = 1.045 < 1.1; PF(R) cua so 30 ngay = 1.093 < 1.2; PF($) cua so 30 ngay = 1.063 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 243 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000MOG/USDT:USDT | LONG | 14245.0 | 0.1122 | 0.111498 | 0.113955 | False | False | 0.0 |
| 1000FLOKI/USDT:USDT | LONG | 46728.0 | 0.0277 | 0.027486 | 0.028235 | False | False | 0.187 |
| 1000LUNC/USDT:USDT | LONG | 34013.0 | 0.0516 | 0.051306 | 0.052335 | False | False | 0.034 |
| 1000PEPE/USDT:USDT | LONG | 200803.0 | 0.0042238 | 0.004174 | 0.004349 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | LONG | 250000.0 | 0.005493 | 0.005453 | 0.005593 | False | False | 0.1 |
| AAVE/USDT:USDT | LONG | 6.4 | 170.6 | 169.057696 | 174.45576 | False | False | 0.0 |
| ACH/USDT:USDT | LONG | 87719.0 | 0.006154 | 0.00604 | 0.006439 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
