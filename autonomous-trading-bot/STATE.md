# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 21/11/2026 17:09:26 · commit `e24a0d8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `33732` · round `454` · nhịp tim cách đây 113.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3261.97 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3071 lệnh đóng, WR 41.06%, E(R) 0.2372, PnL -980.99$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 26 | 50.0 | 11.078 | 22.278 | 1.0798 | 82.54 |
| 14 ngày | 134 | 47.76 | 2.64 | 1.887 | 0.4774 | 134.95 |
| 30 ngày | 171 | 39.77 | 1.814 | 0.863 | 0.307 | -56.78 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 30 ngay [lenh BOT] = 1.134 < 1.2; PF($) cua so 30 ngay [lenh BOT] = 0.584 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 780 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| AERO/USDT:USDT | LONG | 172.0 | 0.3853 | 0.358294 | 0.425812 | False | False | 0.441 |
| GTC/USDT:USDT | SHORT | 391.79 | 0.1365 | 0.1363635 | 0.122208 | True | True | 1.175 |
| QNT/USDT:USDT | SHORT | 0.4 | 132.2 | 140.442536 | 115.714928 | False | False | 0.519 |
| XRP/USDT:USDT | SHORT | 98.3 | 0.8972 | 0.937856 | 0.815888 | False | False | 0.819 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
