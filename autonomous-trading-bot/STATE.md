# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 12:42:25 · commit `9b6490a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `170` · nhịp tim cách đây 121.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3368.09 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 790 lệnh đóng, WR 57.22%, E(R) 0.0176, PnL -42.97$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 561 | 54.72 | 1.021 | 0.948 | 0.0056 | -69.06 |
| 14 ngày | 744 | 56.99 | 1.086 | 0.99 | 0.022 | -16.49 |
| 30 ngày | 790 | 57.22 | 1.067 | 0.977 | 0.0176 | -42.97 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.021 < 1.2; PF($) cua so 7 ngay = 0.948 < 1.1; PF(R) cua so 14 ngay = 1.086 < 1.2; PF($) cua so 14 ngay = 0.990 < 1.1; PF(R) cua so 30 ngay = 1.067 < 1.2; PF($) cua so 30 ngay = 0.977 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 367 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| 1000PEPE/USDT:USDT | LONG | 248756.0 | 0.0041862 | 0.004146 | 0.004286 | False | False | 0.187 |
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.2 |
| ADA/USDT:USDT | SHORT | 2085.0 | 0.237 | 0.236599 | 0.231005 | True | True | 0.667 |
| AERO/USDT:USDT | SHORT | 464.15 | 0.9037 | 0.901386 | 0.87677 | True | True | 0.715 |
| AIOT/USDT:USDT | LONG | 10940.0 | 0.055 | 0.054086 | 0.057285 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| ALT/USDT:USDT | LONG | 37878.5 | 0.00836 | 0.008383999999999999 | 0.00869 | True | True | 0.682 |
| ATOM/USDT:USDT | SHORT | 517.92 | 1.832 | 1.851308 | 1.78373 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
