# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 18/11/2026 12:03:03 · commit `13042d8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `102628` · round `367` · nhịp tim cách đây 8.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3229.53 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3062 lệnh đóng, WR 40.99%, E(R) 0.232, PnL -1029.6$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 31 | 35.48 | 1.583 | 1.281 | 0.2207 | 12.95 |
| 14 ngày | 136 | 43.38 | 1.88 | 1.129 | 0.2999 | 30.16 |
| 30 ngày | 2125 | 33.22 | 2.128 | 0.596 | 0.3241 | -1247.71 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay [lenh BOT] = 0.810 < 1.1; PF(R) cua so 30 ngay [lenh BOT] = 0.654 < 1.2; PF($) cua so 30 ngay [lenh BOT] = 0.426 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 779 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| 1000BONK/USDT:USDT | SHORT | 33337.0 | 0.002349 | 0.002469 | 0.002109 | False | False | 0.675 |
| ADA/USDT:USDT | SHORT | 550.0 | 0.1504 | 0.157708 | 0.135784 | False | False | 0.246 |
| BANK/USDT:USDT | SHORT | 3794.0 | 0.02148 | 0.02145852 | 0.017742 | True | True | 4.055 |
| CKB/USDT:USDT | LONG | 54444.0 | 0.000833 | 0.000833833 | 0.000915 | True | True | 1.727 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
