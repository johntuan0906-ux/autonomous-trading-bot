# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 10:11:27 · commit `d1e02bd`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `95036` · round `1` · nhịp tim cách đây 9.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3219 lệnh đóng, WR 45.36%, E(R) 1.1185, PnL -965.46$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2543 | 42.15 | 5.472 | 0.715 | 1.4055 | -1104.94 |
| 14 ngày | 2990 | 43.98 | 4.915 | 0.796 | 1.2006 | -991.55 |
| 30 ngày | 3219 | 45.36 | 4.712 | 0.82 | 1.1185 | -965.46 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.715 < 1.1; PF($) cua so 14 ngay = 0.796 < 1.1; PF($) cua so 30 ngay = 0.820 < 1.1
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
| 1000PEPE/USDT:USDT | LONG | 29904.0 | 0.0041240999999999995 | 0.004128224099999999 | 0.004298 | True | True | 2.642 |
| ADA/USDT:USDT | SHORT | 360.0 | 0.2204 | 0.2201796 | 0.214235 | True | True | 2.129 |
| AIN/USDT:USDT | LONG | 1877.0 | 0.04109 | 0.033678 | 0.042785 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 1586.0 | 0.1427 | 0.1475 | 0.14225 | False | False | 0.0 |
| AR/USDT:USDT | LONG | 56.5 | 3.8779999999999997 | 3.75318 | 3.89955 | False | False | 0.0 |
| ARB/USDT:USDT | LONG | 446.7 | 0.19899999999999998 | 0.199199 | 0.2097 | True | True | 0.784 |
| AXL/USDT:USDT | LONG | 1155.3 | 0.0578 | 0.053816 | 0.05656 | False | False | 0.0 |
| AXS/USDT:USDT | SHORT | 93.0 | 1.007 | 1.005993 | 0.98371 | True | True | 0.586 |
| BANK/USDT:USDT | SHORT | 12135.0 | 0.026310000000000004 | 0.026456 | 0.02584 | False | False | 0.205 |
| BAT/USDT:USDT | SHORT | 295.3 | 0.1812 | 0.205164 | 0.1656 | False | False | 0.0 |
| BNB/USDT:USDT | LONG | 0.61 | 727.33 | 728.0573300000001 | 736.403475 | True | True | 781.711 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001499 | 0.00146 | 0.001523 | False | False | 0.0 |
| DASH/USDT:USDT | SHORT | 2.814 | 49.32 | 51.132386 | 48.569035 | False | False | 0.0 |
| ENA/USDT:USDT | SHORT | 312.0 | 0.19069999999999998 | 0.1905093 | 0.18122 | True | True | 1.502 |
| ETHFI/USDT:USDT | LONG | 269.5 | 0.7058376994434137 | 0.685696 | 0.71336 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
