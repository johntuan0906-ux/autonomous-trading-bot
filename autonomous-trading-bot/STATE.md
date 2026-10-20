# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 13:24:12 · commit `398fb21`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `98176` · round `3` · nhịp tim cách đây 48.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3259 lệnh đóng, WR 45.01%, E(R) 1.3473, PnL -1000.43$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2568 | 41.82 | 6.42 | 0.716 | 1.6989 | -1099.22 |
| 14 ngày | 3030 | 43.63 | 5.72 | 0.791 | 1.4456 | -1026.52 |
| 30 ngày | 3259 | 45.01 | 5.476 | 0.815 | 1.3473 | -1000.43 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.716 < 1.1; PF($) cua so 14 ngay = 0.791 < 1.1; PF($) cua so 30 ngay = 0.815 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 436 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (15)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 45871.0 | 0.0041535 | 0.004099 | 0.004288 | False | False | 0.284 |
| 1000SHIB/USDT:USDT | LONG | 56818.0 | 0.00499 | 0.004946 | 0.0051 | False | False | 0.0 |
| ACE/USDT:USDT | SHORT | 1560.0 | 0.1493 | 0.150902 | 0.145295 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 214.9 | 0.8025 | 0.81413 | 0.773425 | False | False | 0.0 |
| AIOT/USDT:USDT | LONG | 3272.0 | 0.056 | 0.055236 | 0.05791 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 2191.5 | 0.0313943 | 0.0314256943 | 0.032819 | True | True | 0.309 |
| ALGO/USDT:USDT | LONG | 1332.6 | 0.11097 | 0.11108097 | 0.113315 | True | True | 0.362 |
| APT/USDT:USDT | SHORT | 230.4 | 0.7658 | 0.776646 | 0.738685 | False | False | 0.0 |
| ASTER/USDT:USDT | LONG | 470.0 | 0.7099 | 0.704588 | 0.72318 | False | False | 0.282 |
| AXL/USDT:USDT | SHORT | 3229.9 | 0.0541 | 0.054874 | 0.052165 | False | False | 0.0 |
| BANK/USDT:USDT | LONG | 5681.5 | 0.02609 | 0.026116089999999998 | 0.02664 | True | True | 0.409 |
| BAT/USDT:USDT | LONG | 350.5 | 0.19487 | 0.187738 | 0.2127 | False | False | 0.229 |
| CFX/USDT:USDT | SHORT | 5040.0 | 0.05221 | 0.052706 | 0.05097 | False | False | 0.0 |
| CRV/USDT:USDT | LONG | 238.6 | 0.3648 | 0.3651648 | 0.377895 | True | True | 0.325 |
| CTSI/USDT:USDT | LONG | 3551.0 | 0.03048 | 0.03051048 | 0.03136 | True | True | 0.369 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
