# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 21/11/2026 03:39:17 · commit `b8be11a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `33732` · round `243` · nhịp tim cách đây 30.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3258.01 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3066 lệnh đóng, WR 41.06%, E(R) 0.2345, PnL -995.85$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 22 | 50.0 | 5.664 | 10.009 | 0.8057 | 64.4 |
| 14 ngày | 129 | 48.06 | 2.401 | 1.789 | 0.4235 | 120.09 |
| 30 ngày | 166 | 39.76 | 1.669 | 0.827 | 0.26 | -71.65 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 30 ngay [lenh BOT] = 1.000 < 1.2; PF($) cua so 30 ngay [lenh BOT] = 0.548 < 1.1
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

## Vị thế đang quản lý (5)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 385.0 | 0.1504 | 0.1502496 | 0.135784 | True | True | 1.601 |
| AERO/USDT:USDT | LONG | 172.0 | 0.3853 | 0.358294 | 0.425812 | False | False | 0.0 |
| GTC/USDT:USDT | SHORT | 559.7 | 0.1365 | 0.143646 | 0.122208 | False | False | 0.504 |
| NEAR/USDT:USDT | SHORT | 18.2 | 3.041 | 3.037959 | 2.742032 | True | True | 1.82 |
| XRP/USDT:USDT | SHORT | 98.3 | 0.8972 | 0.937856 | 0.815888 | False | False | 0.236 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
