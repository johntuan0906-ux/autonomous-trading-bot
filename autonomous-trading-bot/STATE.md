# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 15:55:34 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `20180` · round `7` · nhịp tim cách đây 157.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3685.75 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 576 lệnh đóng, WR 55.56%, E(R) 0.0149, PnL -36.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 391 | 51.41 | 1.045 | 0.933 | 0.0123 | -57.25 |
| 14 ngày | 545 | 54.86 | 1.043 | 0.948 | 0.0112 | -61.85 |
| 30 ngày | 576 | 55.56 | 1.057 | 0.971 | 0.0149 | -36.8 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.045 < 1.2; PF($) cua so 7 ngay = 0.933 < 1.1; PF(R) cua so 14 ngay = 1.043 < 1.2; PF($) cua so 14 ngay = 0.948 < 1.1; PF(R) cua so 30 ngay = 1.057 < 1.2; PF($) cua so 30 ngay = 0.971 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 247 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000CAT/USDT:USDT | LONG | 714285.0 | 0.002046 | 0.002029 | 0.002078 | False | False | 0.0 |
| 1INCH/USDT:USDT | LONG | 14044.0 | 0.09942999999999999 | 0.098444 | 0.10095 | False | False | 0.0 |
| ACT/USDT:USDT | LONG | 75757.0 | 0.010890000000000002 | 0.010754 | 0.011195 | False | False | 0.0 |
| ADA/USDT:USDT | LONG | 4006.0 | 0.2534 | 0.250826 | 0.259135 | False | False | 0.0 |
| AERO/USDT:USDT | LONG | 1013.7 | 0.9345 | 0.925642 | 0.958045 | False | False | 0.068 |
| ALGO/USDT:USDT | LONG | 5128.2 | 0.13293 | 0.13106 | 0.137465 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
