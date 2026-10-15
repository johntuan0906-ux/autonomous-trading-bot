# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 08:31:36 · commit `0291ea8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `118` · nhịp tim cách đây 28.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 886 lệnh đóng, WR 58.8%, E(R) 0.0234, PnL 24.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 657 | 57.23 | 1.055 | 0.999 | 0.0151 | -1.29 |
| 14 ngày | 840 | 58.69 | 1.107 | 1.026 | 0.0276 | 51.27 |
| 30 ngày | 886 | 58.8 | 1.088 | 1.012 | 0.0234 | 24.8 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.055 < 1.2; PF($) cua so 7 ngay = 0.999 < 1.1; PF(R) cua so 14 ngay = 1.107 < 1.2; PF($) cua so 14 ngay = 1.026 < 1.1; PF(R) cua so 30 ngay = 1.088 < 1.2; PF($) cua so 30 ngay = 1.012 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 400 lần cập nhật trọng số · Hội đồng AI: **8 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 218340.0 | 0.0040622 | 0.004108 | 0.003947 | False | False | 0.155 |
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005052 | 0.0051 | 0.004932 | False | False | 0.146 |
| ACE/USDT:USDT | LONG | 2927.0 | 0.1861 | 0.182684 | 0.19464 | False | False | 0.088 |
| AERO/USDT:USDT | SHORT | 429.0 | 0.8944 | 0.8935056 | 0.865265 | True | True | 0.549 |
| AIN/USDT:USDT | SHORT | 15479.0 | 0.04062 | 0.041266 | 0.039005 | False | False | 0.248 |
| APE/USDT:USDT | SHORT | 3012.0 | 0.1431 | 0.14293 | 0.13895 | True | True | 0.602 |
| APT/USDT:USDT | SHORT | 907.6 | 0.8124 | 0.823418 | 0.784855 | False | False | 0.281 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
