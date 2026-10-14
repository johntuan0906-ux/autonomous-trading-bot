# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 23:09:07 · commit `3183c51`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3836` · round `21` · nhịp tim cách đây 135.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3416.8 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 862 lệnh đóng, WR 58.35%, E(R) 0.0204, PnL -6.5$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 633 | 56.56 | 1.039 | 0.979 | 0.0108 | -32.59 |
| 14 ngày | 816 | 58.21 | 1.096 | 1.011 | 0.0245 | 19.98 |
| 30 ngày | 862 | 58.35 | 1.078 | 0.997 | 0.0204 | -6.5 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.039 < 1.2; PF($) cua so 7 ngay = 0.979 < 1.1; PF(R) cua so 14 ngay = 1.096 < 1.2; PF($) cua so 14 ngay = 1.011 < 1.1; PF(R) cua so 30 ngay = 1.078 < 1.2; PF($) cua so 30 ngay = 0.997 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 384 lần cập nhật trọng số · Hội đồng AI: **8 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| AERO/USDT:USDT | SHORT | 322.9 | 0.8688 | 0.8616429999999999 | 0.830085 | True | True | 0.962 |
| AIN/USDT:USDT | SHORT | 9276.0 | 0.04015 | 0.041228 | 0.037455 | False | False | 0.121 |
| AIOT/USDT:USDT | SHORT | 5733.5 | 0.0506 | 0.050235999999999996 | 0.04842 | True | True | 0.917 |
| AKE/USDT:USDT | LONG | 15923.0 | 0.025881 | 0.025253 | 0.027451 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 30487.5 | 0.00797 | 0.00796203 | 0.00756 | True | True | 0.488 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.219 |
| AXL/USDT:USDT | LONG | 4655.4 | 0.0596 | 0.057452 | 0.06497 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 16339.5 | 0.0264 | 0.0263736 | 0.025635 | True | True | 0.49 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
