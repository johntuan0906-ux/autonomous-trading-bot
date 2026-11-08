# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 08/11/2026 14:15:56 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `80472` · round `3` · nhịp tim cách đây 5.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2970 lệnh đóng, WR 40.98%, E(R) 0.2258, PnL -1091.01$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 48 | 45.83 | 0.974 | 0.707 | -0.0095 | -40.87 |
| 14 ngày | 63 | 38.1 | 0.95 | 0.492 | -0.0222 | -120.15 |
| 30 ngày | 2584 | 37.96 | 1.894 | 0.722 | 0.255 | -1213.63 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.974 < 1.2; PF($) cua so 7 ngay = 0.707 < 1.1; PF(R) cua so 14 ngay = 0.950 < 1.2; PF($) cua so 14 ngay = 0.492 < 1.1; PF($) cua so 30 ngay = 0.722 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 746 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (18)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 1.0 | 0.002917 | 0.002914083 | 0.002689 | True | True | 1.333 |
| 1000SHIB/USDT:USDT | SHORT | 1.0 | 0.004601 | 0.004596399 | 0.004373 | True | True | 1.325 |
| ACE/USDT:USDT | SHORT | 2347.0 | 0.1236 | 0.125304 | 0.120192 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 1.0 | 0.1879 | 0.18771210000000002 | 0.1738 | True | True | 1.191 |
| AIOT/USDT:USDT | LONG | 414.0 | 0.1273 | 0.117646 | 0.146608 | False | False | 0.155 |
| ALGO/USDT:USDT | LONG | 1196.8 | 0.09543 | 0.092088 | 0.102114 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 1.0 | 0.00554 | 0.00553446 | 0.00512 | True | True | 1.095 |
| APE/USDT:USDT | SHORT | 1862.0 | 0.1058 | 0.107948 | 0.101504 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 352.3 | 0.5929 | 0.604252 | 0.570196 | False | False | 0.0 |
| ARB/USDT:USDT | LONG | 866.9 | 0.169 | 0.164386 | 0.178228 | False | False | 0.087 |
| ASTER/USDT:USDT | SHORT | 315.0 | 0.6799 | 0.692584 | 0.654532 | False | False | 0.016 |
| ATOM/USDT:USDT | SHORT | 154.0 | 1.363 | 1.388974 | 1.311052 | False | False | 0.0 |
| AXL/USDT:USDT | SHORT | 0.1 | 0.0386 | 0.0385614 | 0.035252 | True | True | 1.493 |
| AXS/USDT:USDT | SHORT | 247.0 | 0.817 | 0.833194 | 0.784612 | False | False | 0.0 |
| BAT/USDT:USDT | SHORT | 0.1 | 0.12777 | 0.12764223 | 0.117198 | True | True | 1.536 |
| BR/USDT:USDT | SHORT | 299.0 | 0.4476 | 0.46095 | 0.4209 | False | False | 0.0 |
| BTR/USDT:USDT | SHORT | 2192.0 | 0.04205 | 0.043874 | 0.038402 | False | False | 0.0 |
| CAKE/USDT:USDT | SHORT | 149.0 | 1.8981 | 1.924872 | 1.844556 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
