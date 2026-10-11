# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 17:56:38 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `82548` · round `13` · nhịp tim cách đây 18.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 507 lệnh đóng, WR 57.59%, E(R) 0.0108, PnL 34.16$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 369 | 54.2 | 1.022 | 1.024 | 0.0054 | 16.68 |
| 14 ngày | 476 | 56.93 | 1.026 | 1.01 | 0.0063 | 9.11 |
| 30 ngày | 507 | 57.59 | 1.045 | 1.034 | 0.0108 | 34.16 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.022 < 1.2; PF($) cua so 7 ngay = 1.024 < 1.1; PF(R) cua so 14 ngay = 1.026 < 1.2; PF($) cua so 14 ngay = 1.010 < 1.1; PF(R) cua so 30 ngay = 1.045 < 1.2; PF($) cua so 30 ngay = 1.034 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 227 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 238095.0 | 0.00849 | 0.008448 | 0.008595 | False | False | 0.0 |
| 1000CAT/USDT:USDT | SHORT | 416666.5 | 0.002031 | 0.002026 | 0.002001 | True | True | 0.917 |
| 1000CHEEMS/USDT:USDT | LONG | 2500000.0 | 0.000521 | 0.000517 | 0.000531 | False | False | 0.1 |
| 1000FLOKI/USDT:USDT | SHORT | 29411.5 | 0.02717 | 0.027035000000000003 | 0.026745 | True | True | 1.294 |
| 1000LUNC/USDT:USDT | LONG | 30487.0 | 0.0512 | 0.050872 | 0.05202 | False | False | 0.0 |
| 1000RATS/USDT:USDT | LONG | 39370.0 | 0.0366 | 0.036346 | 0.037235 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005391 | 0.0053856089999999995 | 0.005331 | True | True | 0.375 |
| 1MBABYDOGE/USDT:USDT | LONG | 4761904.0 | 0.0003851 | 0.000383 | 0.00039 | False | False | 0.0 |
| 4/USDT:USDT | SHORT | 63291.0 | 0.0166 | 0.016758 | 0.016205 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
