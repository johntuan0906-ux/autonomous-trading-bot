# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/11/2026 21:06:48 · commit `99ef49b`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `65600` · round `687` · nhịp tim cách đây 83.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3197.75 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3044 lệnh đóng, WR 41.03%, E(R) 0.2313, PnL -1048.3$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 107 | 48.6 | 2.162 | 1.482 | 0.3711 | 67.64 |
| 14 ngày | 123 | 43.9 | 1.701 | 0.958 | 0.2601 | -11.19 |
| 30 ngày | 2126 | 33.07 | 2.103 | 0.578 | 0.318 | -1329.37 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay = 0.958 < 1.1; PF($) cua so 30 ngay = 0.578 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 772 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| 1000BONK/USDT:USDT | SHORT | 29166.2 | 0.002687 | 0.0026843130000000002 | 0.002495 | False | False | 0.0 |
| 1000PEPE/USDT:USDT | SHORT | 12635.0 | 0.0045624 | 0.0045578376000000006 | 0.004118 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 35087.0 | 0.004161 | 0.004275 | 0.003933 | False | False | 0.561 |
| ADA/USDT:USDT | SHORT | 709.0 | 0.1594 | 0.16504 | 0.14812 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 205.4 | 0.4563 | 0.47577 | 0.41736 | False | False | 0.678 |
| CKB/USDT:USDT | SHORT | 77777.7 | 0.000904 | 0.0009030959999999999 | 0.000832 | True | True | 1.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
