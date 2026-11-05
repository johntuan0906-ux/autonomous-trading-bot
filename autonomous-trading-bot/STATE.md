# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 06/11/2026 00:23:32 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `26728` · round `1569` · nhịp tim cách đây 105.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3186.62 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 2928 lệnh đóng, WR 40.85%, E(R) 0.228, PnL -1085.3$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 19 | 15.79 | 0.832 | 0.302 | -0.1207 | -89.22 |
| 14 ngày | 27 | 11.11 | 0.624 | 0.237 | -0.2684 | -148.64 |
| 30 ngày | 2700 | 38.93 | 1.877 | 0.758 | 0.2459 | -1111.39 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.832 < 1.2; PF($) cua so 7 ngay = 0.302 < 1.1; PF(R) cua so 14 ngay = 0.624 < 1.2; PF($) cua so 14 ngay = 0.237 < 1.1; PF($) cua so 30 ngay = 0.758 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.2%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 740 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 51282.0 | 0.004674 | 0.004908 | 0.004206 | False | False | 0.927 |
| ADA/USDT:USDT | SHORT | 455.0 | 0.20690000000000003 | 0.20669310000000002 | 0.116558 | True | True | 1.354 |
| AIOT/USDT:USDT | LONG | 241.7922248 | 0.0909 | 0.0909909 | 0.099072 | False | False | 66.007 |
| APE/USDT:USDT | SHORT | 724.1416 | 0.1122 | 0.11208779999999999 | 0.104244 | True | True | 45.455 |
| BAT/USDT:USDT | SHORT | 1751.3 | 0.13265 | 0.139502 | 0.118946 | False | False | 0.559 |
| LAB/USDT:USDT | SHORT | 3311.2 | 0.04333 | 0.046954 | 0.036082 | False | False | 0.373 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
