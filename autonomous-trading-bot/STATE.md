# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 23:41:24 · commit `daf615c`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3300` · round `15` · nhịp tim cách đây 69.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3582.29 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 594 lệnh đóng, WR 54.04%, E(R) 0.0005, PnL -121.1$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 365 | 48.22 | 0.902 | 0.83 | -0.0286 | -147.19 |
| 14 ngày | 563 | 53.29 | 0.985 | 0.886 | -0.0039 | -146.15 |
| 30 ngày | 594 | 54.04 | 1.002 | 0.912 | 0.0005 | -121.1 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.902 < 1.2; PF($) cua so 7 ngay = 0.830 < 1.1; PF(R) cua so 14 ngay = 0.985 < 1.2; PF($) cua so 14 ngay = 0.886 < 1.1; PF(R) cua so 30 ngay = 1.002 < 1.2; PF($) cua so 30 ngay = 0.912 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 251 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 227272.0 | 0.005357 | 0.005401 | 0.005247 | False | False | 0.182 |
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 3526.0 | 0.2437 | 0.246536 | 0.23661 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 396.6 | 0.9128 | 0.903503 | 0.881285 | True | True | 1.238 |
| AR/USDT:USDT | SHORT | 190.1 | 4.099 | 4.151586 | 3.967535 | False | False | 0.171 |
| ARB/USDT:USDT | SHORT | 3903.2 | 0.1885 | 0.191062 | 0.182095 | False | False | 0.039 |
| LUMIA/USDT:USDT | SHORT | 1343.35 | 0.1099 | 0.1097901 | 0.100595 | True | True | 0.725 |
| NIGHT/USDT:USDT | SHORT | 13550.0 | 0.0466 | 0.047338 | 0.044755 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
