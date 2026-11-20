# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/11/2026 22:39:10 · commit `c264523`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `33732` · round `166` · nhịp tim cách đây 116.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3252.01 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3065 lệnh đóng, WR 41.04%, E(R) 0.234, PnL -1003.06$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 21 | 47.62 | 5.19 | 9.0 | 0.7582 | 57.19 |
| 14 ngày | 133 | 46.62 | 2.336 | 1.756 | 0.4036 | 124.68 |
| 30 ngày | 165 | 39.39 | 1.641 | 0.81 | 0.2507 | -78.86 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 30 ngay [lenh BOT] = 0.944 < 1.2; PF($) cua so 30 ngay [lenh BOT] = 0.520 < 1.1
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

## Vị thế đang quản lý (3)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 385.0 | 0.1504 | 0.1502496 | 0.135784 | True | True | 1.396 |
| AERO/USDT:USDT | SHORT | 172.13 | 0.4153 | 0.4148847 | 0.382768 | True | True | 1.309 |
| NEAR/USDT:USDT | SHORT | 18.2 | 3.041 | 3.037959 | 2.742032 | True | True | 1.244 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
