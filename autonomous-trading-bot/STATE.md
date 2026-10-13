# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 10:51:35 · commit `1c13cc9`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `102888` · round `31` · nhịp tim cách đây 17.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 680 lệnh đóng, WR 57.35%, E(R) 0.034, PnL 106.87$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 451 | 54.32 | 1.103 | 1.081 | 0.0274 | 80.78 |
| 14 ngày | 649 | 56.86 | 1.126 | 1.058 | 0.0318 | 81.82 |
| 30 ngày | 680 | 57.35 | 1.134 | 1.071 | 0.034 | 106.87 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.103 < 1.2; PF($) cua so 7 ngay = 1.081 < 1.1; PF(R) cua so 14 ngay = 1.126 < 1.2; PF($) cua so 14 ngay = 1.058 < 1.1; PF(R) cua so 30 ngay = 1.134 < 1.2; PF($) cua so 30 ngay = 1.071 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 308 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| ACE/USDT:USDT | SHORT | 2791.0 | 0.1789 | 0.182482 | 0.169945 | False | False | 0.084 |
| AIOT/USDT:USDT | LONG | 7704.0 | 0.0547 | 0.053402 | 0.057945 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 10718.0 | 0.0233455 | 0.0233221545 | 0.022181 | True | True | 0.479 |
| ALGO/USDT:USDT | SHORT | 4906.7 | 0.11951 | 0.121548 | 0.114415 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 58823.0 | 0.00793 | 0.0081 | 0.007505 | False | False | 0.0 |
| APR/USDT:USDT | SHORT | 4995.0 | 0.07329 | 0.075292 | 0.068285 | False | False | 0.045 |
| ATOM/USDT:USDT | SHORT | 364.43 | 1.812 | 1.83944 | 1.7434 | False | False | 0.292 |
| BR/USDT:USDT | SHORT | 444.5 | 0.45636 | 0.450129 | 0.428265 | True | True | 1.054 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
