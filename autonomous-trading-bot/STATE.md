# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 12:49:29 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `92660` · round `3` · nhịp tim cách đây 269.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 565 lệnh đóng, WR 56.28%, E(R) 0.0074, PnL -6.94$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 397 | 53.9 | 1.057 | 1.034 | 0.0149 | 28.03 |
| 14 ngày | 534 | 55.62 | 1.012 | 0.972 | 0.0031 | -31.99 |
| 30 ngày | 565 | 56.28 | 1.028 | 0.994 | 0.0074 | -6.94 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.057 < 1.2; PF($) cua so 7 ngay = 1.034 < 1.1; PF(R) cua so 14 ngay = 1.012 < 1.2; PF($) cua so 14 ngay = 0.972 < 1.1; PF(R) cua so 30 ngay = 1.028 < 1.2; PF($) cua so 30 ngay = 0.994 < 1.1
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
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000BOB/USDT:USDT | LONG | 178571.0 | 0.008669999999999999 | 0.008614 | 0.00881 | False | False | 0.0 |
| 1000000MOG/USDT:USDT | LONG | 10395.0 | 0.1131 | 0.112138 | 0.115505 | False | False | 0.104 |
| 1000CAT/USDT:USDT | LONG | 625000.0 | 0.0020499999999999997 | 0.002034 | 0.00209 | False | False | 0.0 |
| 1000LUNC/USDT:USDT | LONG | 32051.0 | 0.05164 | 0.051328 | 0.05242 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | LONG | 238095.0 | 0.005527 | 0.005485 | 0.005632 | False | False | 0.0 |
| 1000XEC/USDT:USDT | LONG | 138888.0 | 0.007275 | 0.007203 | 0.007455 | False | False | 0.0 |
| AERO/USDT:USDT | LONG | 553.7 | 0.9348 | 0.9357348 | 0.957375 | True | True | 0.587 |
| AGT/USDT:USDT | SHORT | 8993.0 | 0.018443 | 0.018424557 | 0.017748 | True | True | 0.568 |
| AIA/USDT:USDT | SHORT | 3742.5 | 0.0813 | 0.080734 | 0.07963 | True | True | 1.347 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
