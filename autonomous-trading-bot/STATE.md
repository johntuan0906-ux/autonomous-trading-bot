# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 08/11/2026 23:46:05 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `80472` · round `141` · nhịp tim cách đây 38.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3219.51 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2977 lệnh đóng, WR 41.08%, E(R) 0.2255, PnL -1087.7$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 55 | 50.91 | 1.02 | 0.738 | 0.0068 | -37.56 |
| 14 ngày | 70 | 42.86 | 0.98 | 0.514 | -0.0082 | -116.84 |
| 30 ngày | 2558 | 37.61 | 1.901 | 0.727 | 0.2569 | -1185.22 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.020 < 1.2; PF($) cua so 7 ngay = 0.738 < 1.1; PF(R) cua so 14 ngay = 0.980 < 1.2; PF($) cua so 14 ngay = 0.514 < 1.1; PF($) cua so 30 ngay = 0.727 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 748 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (14)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 83333.0 | 0.002773 | 0.002821 | 0.002677 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 95238.0 | 0.004468 | 0.00451 | 0.004384 | False | False | 0.357 |
| ACE/USDT:USDT | SHORT | 1642.9 | 0.1236 | 0.1234764 | 0.120192 | True | True | 1.819 |
| ALGO/USDT:USDT | LONG | 1196.8 | 0.09543 | 0.092088 | 0.102114 | False | False | 0.242 |
| APE/USDT:USDT | SHORT | 1862.0 | 0.1058 | 0.107948 | 0.101504 | False | False | 0.885 |
| APT/USDT:USDT | SHORT | 352.3 | 0.5929 | 0.604252 | 0.570196 | False | False | 0.529 |
| ARB/USDT:USDT | LONG | 866.9 | 0.169 | 0.164386 | 0.178228 | False | False | 0.368 |
| ASTER/USDT:USDT | SHORT | 315.0 | 0.6799 | 0.692584 | 0.654532 | False | False | 0.205 |
| ATOM/USDT:USDT | SHORT | 107.8 | 1.363 | 1.361637 | 1.311052 | True | True | 1.271 |
| AXS/USDT:USDT | SHORT | 247.0 | 0.817 | 0.833194 | 0.784612 | False | False | 0.371 |
| BR/USDT:USDT | SHORT | 209.3 | 0.4476 | 0.4471524 | 0.4209 | True | True | 1.723 |
| CAKE/USDT:USDT | SHORT | 149.0 | 1.8981 | 1.924872 | 1.844556 | False | False | 0.568 |
| GTC/USDT:USDT | SHORT | 159.4 | 0.1736 | 0.18614 | 0.14852 | False | False | 0.287 |
| QNT/USDT:USDT | LONG | 0.5 | 200.2 | 193.000276 | 214.599448 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
