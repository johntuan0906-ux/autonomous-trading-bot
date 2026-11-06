# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 06/11/2026 20:15:46 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `88656` · round `130` · nhịp tim cách đây 116.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3164.99 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2931 lệnh đóng, WR 40.81%, E(R) 0.2267, PnL -1115.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 18 | 5.56 | 0.687 | 0.153 | -0.2516 | -115.58 |
| 14 ngày | 30 | 10.0 | 0.539 | 0.205 | -0.3427 | -179.14 |
| 30 ngày | 2703 | 38.88 | 1.869 | 0.753 | 0.2445 | -1141.89 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.687 < 1.2; PF($) cua so 7 ngay = 0.153 < 1.1; PF(R) cua so 14 ngay = 0.539 < 1.2; PF($) cua so 14 ngay = 0.205 < 1.1; PF($) cua so 30 ngay = 0.753 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.2%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 742 lần cập nhật trọng số · Hội đồng AI: **11 model**

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
| 1000SHIB/USDT:USDT | SHORT | 51282.0 | 0.004674 | 0.004908 | 0.004206 | False | False | 0.927 |
| ADA/USDT:USDT | SHORT | 455.0 | 0.20690000000000003 | 0.20669310000000002 | 0.116558 | True | True | 1.522 |
| ALGO/USDT:USDT | SHORT | 3824.0 | 0.09361 | 0.096748 | 0.087334 | False | False | 0.137 |
| BAT/USDT:USDT | SHORT | 1751.3 | 0.13265 | 0.139502 | 0.118946 | False | False | 0.776 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
