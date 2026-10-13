# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 21:49:40 · commit `0ee1b23`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `90444` · round `14` · nhịp tim cách đây 89.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3480.26 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 729 lệnh đóng, WR 56.79%, E(R) 0.0282, PnL 23.59$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 500 | 53.8 | 1.072 | 0.998 | 0.0196 | -2.5 |
| 14 ngày | 683 | 56.52 | 1.134 | 1.033 | 0.0337 | 50.06 |
| 30 ngày | 729 | 56.79 | 1.109 | 1.014 | 0.0282 | 23.59 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.072 < 1.2; PF($) cua so 7 ngay = 0.998 < 1.1; PF(R) cua so 14 ngay = 1.134 < 1.2; PF($) cua so 14 ngay = 1.033 < 1.1; PF(R) cua so 30 ngay = 1.109 < 1.2; PF($) cua so 30 ngay = 1.014 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 327 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| ALGO/USDT:USDT | SHORT | 4730.3 | 0.1201 | 0.122214 | 0.114815 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 4582.0 | 0.1491 | 0.151282 | 0.143645 | False | False | 0.0 |
| APR/USDT:USDT | SHORT | 4821.0 | 0.0526 | 0.054674 | 0.047415 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 675.1 | 0.8217 | 0.836512 | 0.78467 | False | False | 0.061 |
| AR/USDT:USDT | SHORT | 147.5 | 3.945 | 4.012792 | 3.77552 | False | False | 0.192 |
| ATOM/USDT:USDT | SHORT | 183.04 | 1.821 | 1.8176580000000002 | 1.75271 | True | True | 0.622 |
| BANK/USDT:USDT | SHORT | 14204.5 | 0.02773 | 0.02770227 | 0.02685 | True | True | 0.398 |
| QNT/USDT:USDT | SHORT | 0.85 | 209.21 | 209.00079 | 194.63101 | True | True | 0.473 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
