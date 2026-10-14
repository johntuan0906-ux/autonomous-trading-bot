# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 16:50:24 · commit `780dee4`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `26956` · round `8` · nhịp tim cách đây 8.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 821 lệnh đóng, WR 57.73%, E(R) 0.0172, PnL -40.78$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 592 | 55.57 | 1.021 | 0.953 | 0.0057 | -66.87 |
| 14 ngày | 775 | 57.55 | 1.084 | 0.992 | 0.0214 | -14.3 |
| 30 ngày | 821 | 57.73 | 1.066 | 0.979 | 0.0172 | -40.78 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.021 < 1.2; PF($) cua so 7 ngay = 0.953 < 1.1; PF(R) cua so 14 ngay = 1.084 < 1.2; PF($) cua so 14 ngay = 0.992 < 1.1; PF(R) cua so 30 ngay = 1.066 < 1.2; PF($) cua so 30 ngay = 0.979 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 375 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 226244.0 | 0.0041822 | 0.004138 | 0.004292 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 147059.0 | 0.005172 | 0.005143999999999999 | 0.005087 | True | True | 1.324 |
| AIN/USDT:USDT | SHORT | 6596.0 | 0.04271 | 0.041779 | 0.040815 | True | True | 1.728 |
| ALGO/USDT:USDT | SHORT | 2910.35 | 0.1198 | 0.1196802 | 0.115505 | True | True | 0.373 |
| APE/USDT:USDT | SHORT | 3276.5 | 0.1489 | 0.148563 | 0.145085 | True | True | 0.721 |
| APR/USDT:USDT | SHORT | 10438.0 | 0.052 | 0.052958 | 0.049605 | False | False | 0.209 |
| APT/USDT:USDT | SHORT | 992.8 | 0.8133 | 0.823372 | 0.78812 | False | False | 0.0 |
| ATOM/USDT:USDT | SHORT | 249.5 | 1.824 | 1.8010199999999998 | 1.7739 | True | True | 1.647 |
| QNT/USDT:USDT | SHORT | 1.4 | 213.37 | 211.593302 | 204.70349 | True | True | 1.013 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
