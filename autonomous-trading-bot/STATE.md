# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 08/11/2026 09:15:53 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89420` · round `497` · nhịp tim cách đây 123.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3184.48 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2938 lệnh đóng, WR 40.74%, E(R) 0.2258, PnL -1112.56$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 16 | 12.5 | 0.325 | 0.421 | -0.4865 | -62.42 |
| 14 ngày | 31 | 12.9 | 0.606 | 0.309 | -0.2815 | -141.7 |
| 30 ngày | 2595 | 37.53 | 1.864 | 0.705 | 0.2476 | -1310.02 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.325 < 1.2; PF($) cua so 7 ngay = 0.421 < 1.1; PF(R) cua so 14 ngay = 0.606 < 1.2; PF($) cua so 14 ngay = 0.309 < 1.1; PF($) cua so 30 ngay = 0.705 < 1.1
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
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (15)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 24560.9 | 0.002917 | 0.002914083 | 0.002689 | True | True | 1.281 |
| 1000PEPE/USDT:USDT | SHORT | 33195.0 | 0.0049025 | 0.005023 | 0.004662 | False | False | 0.633 |
| 1000SHIB/USDT:USDT | SHORT | 24560.9 | 0.004601 | 0.004596399 | 0.004373 | True | True | 1.325 |
| ADA/USDT:USDT | SHORT | 396.9 | 0.1879 | 0.18771210000000002 | 0.1738 | True | True | 1.177 |
| AERO/USDT:USDT | SHORT | 143.7 | 0.6046 | 0.632434 | 0.548932 | False | False | 0.481 |
| AIOT/USDT:USDT | LONG | 457.0 | 0.121 | 0.112252 | 0.138496 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 19047.0 | 0.00554 | 0.00575 | 0.00512 | False | False | 0.952 |
| APE/USDT:USDT | SHORT | 211.7682 | 0.1102 | 0.1100898 | 0.103852 | False | False | 42.65 |
| APT/USDT:USDT | SHORT | 246.3 | 0.5968 | 0.613036 | 0.564328 | False | False | 0.031 |
| ASTER/USDT:USDT | SHORT | 194.0 | 0.684 | 0.704532 | 0.642936 | False | False | 0.487 |
| AVAX/USDT:USDT | SHORT | 11.2 | 8.407 | 8.398593 | 7.91008 | True | True | 1.079 |
| AXL/USDT:USDT | SHORT | 1672.58 | 0.0386 | 0.0385614 | 0.035252 | True | True | 1.374 |
| BAT/USDT:USDT | SHORT | 529.69 | 0.12777 | 0.12764223 | 0.117198 | True | True | 1.298 |
| BNB/USDT:USDT | SHORT | 0.69 | 694.35 | 700.084056 | 682.881888 | False | False | 0.148 |
| GTC/USDT:USDT | SHORT | 182.3 | 0.1675 | 0.178468 | 0.145564 | False | False | 0.748 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
