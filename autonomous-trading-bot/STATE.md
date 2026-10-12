# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 00:11:27 · commit `6b46e67`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `70064` · round `2` · nhịp tim cách đây 99.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 595 lệnh đóng, WR 54.12%, E(R) 0.0011, PnL -117.48$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 366 | 48.36 | 0.905 | 0.834 | -0.0275 | -143.57 |
| 14 ngày | 564 | 53.37 | 0.988 | 0.889 | -0.0032 | -142.53 |
| 30 ngày | 595 | 54.12 | 1.004 | 0.915 | 0.0011 | -117.48 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.905 < 1.2; PF($) cua so 7 ngay = 0.834 < 1.1; PF(R) cua so 14 ngay = 0.988 < 1.2; PF($) cua so 14 ngay = 0.889 < 1.1; PF(R) cua so 30 ngay = 1.004 < 1.2; PF($) cua so 30 ngay = 0.915 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 252 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (11)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 113636.0 | 0.005357 | 0.005327 | 0.005247 | True | True | 1.182 |
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.25 |
| ADA/USDT:USDT | SHORT | 1763.0 | 0.2437 | 0.242518 | 0.23661 | True | True | 0.917 |
| AERO/USDT:USDT | SHORT | 396.6 | 0.9128 | 0.8959029999999999 | 0.881285 | True | True | 1.84 |
| AR/USDT:USDT | SHORT | 95.05 | 4.099 | 4.0542929999999995 | 3.967535 | True | True | 1.35 |
| ARB/USDT:USDT | SHORT | 1951.6 | 0.1885 | 0.185981 | 0.182095 | True | True | 1.483 |
| BCH/USDT:USDT | SHORT | 2.5125 | 276.2 | 275.494932 | 271.22534 | True | True | 0.854 |
| CFX/USDT:USDT | SHORT | 4488.0 | 0.06055 | 0.06048945 | 0.057765 | True | True | 0.332 |
| CRV/USDT:USDT | SHORT | 1562.0 | 0.3505 | 0.356902 | 0.334495 | False | False | 0.0 |
| CTSI/USDT:USDT | SHORT | 5592.5 | 0.03396 | 0.03392604 | 0.031725 | True | True | 0.537 |
| NIGHT/USDT:USDT | SHORT | 6775.0 | 0.0466 | 0.046249 | 0.044755 | True | True | 0.976 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
