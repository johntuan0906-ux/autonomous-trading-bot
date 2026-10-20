# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 20/10/2026 12:11:28 · commit `a15e0f3`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `95036` · round `30` · nhịp tim cách đây 85.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3307.78 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3249 lệnh đóng, WR 45.15%, E(R) 1.3522, PnL -975.16$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2558 | 41.99 | 6.446 | 0.721 | 1.7065 | -1073.96 |
| 14 ngày | 3020 | 43.77 | 5.739 | 0.795 | 1.4512 | -1001.25 |
| 30 ngày | 3249 | 45.15 | 5.493 | 0.819 | 1.3522 | -975.16 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.721 < 1.1; PF($) cua so 14 ngay = 0.795 < 1.1; PF($) cua so 30 ngay = 0.819 < 1.1
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

## Vị thế đang quản lý (5)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| AIN/USDT:USDT | LONG | 1877.0 | 0.04109 | 0.033678 | 0.042785 | False | False | 0.0 |
| AR/USDT:USDT | LONG | 56.5 | 3.8779999999999997 | 3.75318 | 3.89955 | False | False | 0.0 |
| AXL/USDT:USDT | LONG | 1155.3 | 0.0578 | 0.053816 | 0.05656 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 1.0 | 0.026310000000000004 | 0.026532 | 0.025895 | False | False | 0.0 |
| BAT/USDT:USDT | SHORT | 295.3 | 0.1812 | 0.205164 | 0.1656 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
