# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 22:39:07 · commit `fd3c5df`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3836` · round `14` · nhịp tim cách đây 17.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3396.63 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 861 lệnh đóng, WR 58.3%, E(R) 0.0202, PnL -8.31$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 632 | 56.49 | 1.038 | 0.978 | 0.0105 | -34.4 |
| 14 ngày | 815 | 58.16 | 1.095 | 1.01 | 0.0244 | 18.17 |
| 30 ngày | 861 | 58.3 | 1.077 | 0.996 | 0.0202 | -8.31 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.038 < 1.2; PF($) cua so 7 ngay = 0.978 < 1.1; PF(R) cua so 14 ngay = 1.095 < 1.2; PF($) cua so 14 ngay = 1.010 < 1.1; PF(R) cua so 30 ngay = 1.077 < 1.2; PF($) cua so 30 ngay = 0.996 < 1.1
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

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 3021.0 | 0.2276 | 0.23091 | 0.219325 | False | False | 0.272 |
| AERO/USDT:USDT | SHORT | 322.9 | 0.8688 | 0.8638429999999999 | 0.830085 | True | True | 0.82 |
| AIOT/USDT:USDT | SHORT | 11467.0 | 0.0506 | 0.051472 | 0.04842 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 60975.0 | 0.00797 | 0.008134 | 0.00756 | False | False | 0.244 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.219 |
| AXL/USDT:USDT | LONG | 4655.4 | 0.0596 | 0.057452 | 0.06497 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 32679.0 | 0.0264 | 0.026706 | 0.025635 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
