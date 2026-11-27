# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 28/11/2026 00:56:55 · commit `9338267`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `22700` · round `674` · nhịp tim cách đây 31.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 1000.0 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3089 lệnh đóng, WR 41.11%, E(R) 0.2373, PnL -959.75$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 24 | 50.0 | 2.704 | 2.206 | 0.6618 | 43.31 |
| 14 ngày | 45 | 48.89 | 3.424 | 3.335 | 0.7068 | 100.5 |
| 30 ngày | 180 | 42.78 | 1.941 | 1.098 | 0.3513 | 36.33 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 30 ngay [lenh BOT] = 1.087 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 785 lần cập nhật trọng số · Hội đồng AI: **3 model**

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
| APR/USDT:USDT | SHORT | 3159.0 | 0.03052 | 0.031786 | 0.027988 | False | False | 0.9 |
| CKB/USDT:USDT | LONG | 58334.0 | 0.000807 | 0.000807807 | 0.000901 | True | True | 1.14 |
| STRK/USDT:USDT | SHORT | 2989.5 | 0.0313 | 0.032638 | 0.028624 | False | False | 0.523 |
| WIF/USDT:USDT | LONG | 542.6 | 0.1346314927106 | 0.1344343 | 0.14462 | True | True | 1.434 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
