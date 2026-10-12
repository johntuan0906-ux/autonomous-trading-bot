# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 12:19:28 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `57496` · round `1` · nhịp tim cách đây 255.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3782.78 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 560 lệnh đóng, WR 56.07%, E(R) 0.0065, PnL -12.36$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 394 | 53.3 | 1.051 | 1.026 | 0.0134 | 21.67 |
| 14 ngày | 529 | 55.39 | 1.008 | 0.967 | 0.0021 | -37.4 |
| 30 ngày | 560 | 56.07 | 1.025 | 0.99 | 0.0065 | -12.36 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.051 < 1.2; PF($) cua so 7 ngay = 1.026 < 1.1; PF(R) cua so 14 ngay = 1.008 < 1.2; PF($) cua so 14 ngay = 0.967 < 1.1; PF(R) cua so 30 ngay = 1.025 < 1.2; PF($) cua so 30 ngay = 0.990 < 1.1
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

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000MOG/USDT:USDT | LONG | 10395.0 | 0.1131 | 0.112138 | 0.115505 | False | False | 0.104 |
| 1000CHEEMS/USDT:USDT | LONG | 1111111.0 | 0.0005265 | 0.0005270264999999999 | 0.000536 | True | True | 0.533 |
| 1000LUNC/USDT:USDT | LONG | 32051.0 | 0.05164 | 0.051328 | 0.05242 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | LONG | 166667.0 | 0.005482 | 0.00553 | 0.005557 | True | True | 2.1 |
| 1INCH/USDT:USDT | LONG | 7396.0 | 0.09897 | 0.099362 | 0.10066 | True | True | 1.08 |
| 1MBABYDOGE/USDT:USDT | LONG | 2173913.0 | 0.0003913 | 0.00039169130000000005 | 0.000396 | True | True | 0.565 |
| AERO/USDT:USDT | LONG | 553.7 | 0.9348 | 0.9357348 | 0.957375 | True | True | 0.321 |
| AGT/USDT:USDT | SHORT | 35971.0 | 0.018443 | 0.018721 | 0.017748 | False | False | 0.295 |
| AIA/USDT:USDT | SHORT | 14970.0 | 0.0813 | 0.081968 | 0.07963 | False | False | 0.165 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
