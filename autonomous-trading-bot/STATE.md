# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 19/10/2026 18:00:08 · commit `69ba2b8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `76116` · round `1` · nhịp tim cách đây 39.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 1058 lệnh đóng, WR 56.81%, E(R) 0.1511, PnL 71.53$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 468 | 60.04 | 2.208 | 1.151 | 0.3349 | 164.81 |
| 14 ngày | 864 | 55.21 | 1.657 | 1.033 | 0.1822 | 64.65 |
| 30 ngày | 1058 | 56.81 | 1.558 | 1.029 | 0.1511 | 71.53 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay = 1.033 < 1.1; PF($) cua so 30 ngay = 1.029 < 1.1
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

## Vị thế đang quản lý (16)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 59808.0 | 0.0041240999999999995 | 0.00401 | 0.00422 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 719.0 | 0.2205 | 0.218169 | 0.216155 | True | True | 1.841 |
| AIN/USDT:USDT | LONG | 1877.0 | 0.04109 | 0.04102 | 0.04284 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 1586.0 | 0.1427 | 0.145934 | 0.140565 | False | False | 0.0 |
| AR/USDT:USDT | LONG | 56.5 | 3.874 | 3.829762 | 3.984595 | False | False | 0.09 |
| ARB/USDT:USDT | LONG | 893.4 | 0.19899999999999998 | 0.193396 | 0.20321 | False | False | 0.0 |
| AVAX/USDT:USDT | SHORT | 31.0 | 9.776 | 9.740432 | 9.57884 | True | True | 0.951 |
| AXL/USDT:USDT | LONG | 1155.3 | 0.0578 | 0.056298 | 0.060505 | False | False | 0.266 |
| AXS/USDT:USDT | SHORT | 186.0 | 1.007 | 1.00792 | 0.9837 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 12135.0 | 0.02632 | 0.026272999999999998 | 0.025805 | True | True | 0.777 |
| BAT/USDT:USDT | SHORT | 295.3 | 0.1812 | 0.187912 | 0.173765 | False | False | 0.0 |
| BNB/USDT:USDT | LONG | 1.21 | 727.33 | 724.749348 | 732.20663 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001499 | 0.001457 | 0.00152 | False | False | 0.0 |
| DASH/USDT:USDT | SHORT | 2.814 | 49.32 | 49.380334 | 47.839165 | False | False | 0.0 |
| ENA/USDT:USDT | SHORT | 624.0 | 0.19069999999999998 | 0.189794 | 0.182465 | False | False | 0.0 |
| ETHFI/USDT:USDT | LONG | 269.5 | 0.7058376994434137 | 0.68348 | 0.714 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
