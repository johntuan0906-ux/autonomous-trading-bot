# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 09:51:35 · commit `4abdb76`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `102888` · round `16` · nhịp tim cách đây 6.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3665.12 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 672 lệnh đóng, WR 57.29%, E(R) 0.0383, PnL 133.01$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 443 | 54.18 | 1.128 | 1.111 | 0.0338 | 106.92 |
| 14 ngày | 641 | 56.79 | 1.145 | 1.078 | 0.0362 | 107.97 |
| 30 ngày | 672 | 57.29 | 1.152 | 1.09 | 0.0383 | 133.01 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.128 < 1.2; PF(R) cua so 14 ngay = 1.145 < 1.2; PF($) cua so 14 ngay = 1.078 < 1.1; PF(R) cua so 30 ngay = 1.152 < 1.2; PF($) cua so 30 ngay = 1.090 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 300 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 143472.0 | 0.0039233 | 0.003993 | 0.003748 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 887.4 | 0.8745 | 0.885768 | 0.84633 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 2429.5 | 0.1185 | 0.1183815 | 0.113355 | True | True | 0.335 |
| ALT/USDT:USDT | SHORT | 28735.5 | 0.00776 | 0.0077522400000000005 | 0.007325 | True | True | 0.46 |
| ASTER/USDT:USDT | SHORT | 1219.0 | 0.6878 | 0.696 | 0.6673 | False | False | 0.012 |
| AXL/USDT:USDT | SHORT | 3037.65 | 0.0563 | 0.056022999999999996 | 0.052185 | True | True | 0.668 |
| AXS/USDT:USDT | SHORT | 270.0 | 1.139 | 1.137861 | 1.092775 | True | True | 0.433 |
| BOME/USDT:USDT | SHORT | 273224.0 | 0.0007747 | 0.0007739253000000001 | 0.00073 | True | True | 0.306 |
| BR/USDT:USDT | SHORT | 889.0 | 0.45636 | 0.467598 | 0.428265 | False | False | 0.214 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
