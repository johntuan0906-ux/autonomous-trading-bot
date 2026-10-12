# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 23:11:23 · commit `68278f3`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3300` · round `8` · nhịp tim cách đây 15.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 591 lệnh đóng, WR 54.15%, E(R) 0.0035, PnL -103.37$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 362 | 48.34 | 0.917 | 0.847 | -0.0239 | -129.46 |
| 14 ngày | 560 | 53.39 | 0.997 | 0.898 | -0.0007 | -128.42 |
| 30 ngày | 591 | 54.15 | 1.013 | 0.924 | 0.0035 | -103.37 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.917 < 1.2; PF($) cua so 7 ngay = 0.847 < 1.1; PF(R) cua so 14 ngay = 0.997 < 1.2; PF($) cua so 14 ngay = 0.898 < 1.1; PF(R) cua so 30 ngay = 1.013 < 1.2; PF($) cua so 30 ngay = 0.924 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 248 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ACE/USDT:USDT | SHORT | 3123.0 | 0.183 | 0.186202 | 0.174995 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 396.6 | 0.9128 | 0.9081030000000001 | 0.881285 | True | True | 0.873 |
| ARB/USDT:USDT | SHORT | 3903.2 | 0.1885 | 0.191062 | 0.182095 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 208333.0 | 0.001665 | 0.001617 | 0.001785 | False | False | 0.0 |
| CTSI/USDT:USDT | SHORT | 14164.0 | 0.03328 | 0.033986 | 0.031515 | False | False | 0.0 |
| JCT/USDT:USDT | SHORT | 86206.5 | 0.001881 | 0.001879119 | 0.001736 | True | True | 0.552 |
| LUMIA/USDT:USDT | SHORT | 1343.35 | 0.1099 | 0.1097901 | 0.100595 | True | True | 0.725 |
| NIGHT/USDT:USDT | SHORT | 13550.0 | 0.0466 | 0.047338 | 0.044755 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
