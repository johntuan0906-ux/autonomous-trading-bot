# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 01/11/2026 01:36:05 · commit `fda45ba`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `35964` · round `1255` · nhịp tim cách đây 67.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3201.6 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2920 lệnh đóng, WR 40.92%, E(R) 0.2305, PnL -1038.15$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 13 | 15.38 | 1.123 | 0.21 | 0.0811 | -67.29 |
| 14 ngày | 1983 | 32.58 | 2.165 | 0.554 | 0.3285 | -1256.26 |
| 30 ngày | 2835 | 40.21 | 1.864 | 0.786 | 0.2371 | -1024.07 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.123 < 1.2; PF($) cua so 7 ngay = 0.210 < 1.1; PF($) cua so 14 ngay = 0.554 < 1.1; PF($) cua so 30 ngay = 0.786 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.2%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 736 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (4)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 50000.0 | 0.002848 | 0.003088 | 0.002368 | False | False | 0.708 |
| 1000SHIB/USDT:USDT | SHORT | 51282.0 | 0.004674 | 0.004908 | 0.004206 | False | False | 0.808 |
| ADA/USDT:USDT | SHORT | 455.0 | 0.20690000000000003 | 0.20669310000000002 | 0.116558 | True | True | 1.197 |
| ALGO/USDT:USDT | SHORT | 5540.1 | 0.09543 | 0.097596 | 0.091098 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
