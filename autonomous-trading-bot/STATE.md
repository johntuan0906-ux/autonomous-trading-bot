# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 11:41:28 · commit `67b0bcd`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `95036` · round `23` · nhịp tim cách đây 25.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3311.25 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3240 lệnh đóng, WR 45.28%, E(R) 1.3563, PnL -964.18$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2549 | 42.13 | 6.463 | 0.723 | 1.7129 | -1062.97 |
| 14 ngày | 3011 | 43.91 | 5.752 | 0.796 | 1.4559 | -990.27 |
| 30 ngày | 3240 | 45.28 | 5.505 | 0.821 | 1.3563 | -964.18 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.723 < 1.1; PF($) cua so 14 ngay = 0.796 < 1.1; PF($) cua so 30 ngay = 0.821 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 436 lần cập nhật trọng số · Hội đồng AI: **6 model**

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
| AIN/USDT:USDT | LONG | 1877.0 | 0.04109 | 0.033678 | 0.042785 | False | False | 0.0 |
| AR/USDT:USDT | LONG | 56.5 | 3.8779999999999997 | 3.75318 | 3.89955 | False | False | 0.0 |
| AXL/USDT:USDT | LONG | 1155.3 | 0.0578 | 0.053816 | 0.05656 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 1.0 | 0.026310000000000004 | 0.026532 | 0.025895 | False | False | 0.0 |
| BAT/USDT:USDT | SHORT | 295.3 | 0.1812 | 0.205164 | 0.1656 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001499 | 0.00146 | 0.001523 | False | False | 0.154 |
| ETHFI/USDT:USDT | LONG | 269.5 | 0.7058376994434137 | 0.685696 | 0.71336 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
