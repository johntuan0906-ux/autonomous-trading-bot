# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 21:38:52 · commit `73a98c4`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `98564` · round `7` · nhịp tim cách đây 69.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3404.33 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 927 lệnh đóng, WR 59.12%, E(R) 0.0435, PnL 200.91$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 669 | 56.2 | 1.111 | 1.053 | 0.0316 | 90.9 |
| 14 ngày | 865 | 59.08 | 1.177 | 1.109 | 0.0459 | 221.95 |
| 30 ngày | 927 | 59.12 | 1.164 | 1.09 | 0.0435 | 200.91 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.111 < 1.2; PF($) cua so 7 ngay = 1.053 < 1.1; PF(R) cua so 14 ngay = 1.177 < 1.2; PF(R) cua so 30 ngay = 1.164 < 1.2; PF($) cua so 30 ngay = 1.090 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 418 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 172413.0 | 0.004991 | 0.005049 | 0.004846 | False | False | 0.0 |
| ACE/USDT:USDT | SHORT | 2601.0 | 0.1666 | 0.170444 | 0.15699 | False | False | 0.0 |
| AIOT/USDT:USDT | SHORT | 9980.0 | 0.0527 | 0.053702 | 0.050195 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 6105.0 | 0.10976 | 0.111398 | 0.105665 | False | False | 0.0 |
| APR/USDT:USDT | SHORT | 3993.5 | 0.04827 | 0.04822173 | 0.04514 | True | True | 0.343 |
| BNB/USDT:USDT | SHORT | 2.0 | 723.09 | 728.087574 | 710.596065 | False | False | 0.17 |
| CFX/USDT:USDT | SHORT | 11312.0 | 0.05371 | 0.054594 | 0.0515 | False | False | 0.023 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
