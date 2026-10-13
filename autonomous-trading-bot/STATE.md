# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 04:12:20 · commit `c7839f6`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `45` · nhịp tim cách đây 16.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3415.04 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 762 lệnh đóng, WR 56.3%, E(R) 0.0188, PnL -38.99$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 533 | 53.28 | 1.024 | 0.949 | 0.0067 | -65.08 |
| 14 ngày | 716 | 56.01 | 1.091 | 0.992 | 0.0234 | -12.51 |
| 30 ngày | 762 | 56.3 | 1.071 | 0.978 | 0.0188 | -38.99 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.024 < 1.2; PF($) cua so 7 ngay = 0.949 < 1.1; PF(R) cua so 14 ngay = 1.091 < 1.2; PF($) cua so 14 ngay = 0.992 < 1.1; PF(R) cua so 30 ngay = 1.071 < 1.2; PF($) cua so 30 ngay = 0.978 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 339 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| 1000PEPE/USDT:USDT | LONG | 156494.0 | 0.0042109 | 0.004147 | 0.004371 | False | False | 0.236 |
| 1000SHIB/USDT:USDT | SHORT | 277777.0 | 0.00522 | 0.005256 | 0.00513 | False | False | 0.167 |
| AIN/USDT:USDT | SHORT | 7530.0 | 0.04427 | 0.045598 | 0.04095 | False | False | 0.12 |
| AIOT/USDT:USDT | LONG | 4139.0 | 0.0555 | 0.055596 | 0.05852 | True | True | 0.579 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.206 |
| ALGO/USDT:USDT | SHORT | 6393.8 | 0.12086 | 0.122424 | 0.11695 | False | False | 0.058 |
| BANK/USDT:USDT | SHORT | 17730.0 | 0.02774 | 0.027712260000000002 | 0.027035 | True | True | 0.319 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
