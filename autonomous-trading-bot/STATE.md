# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 13:12:26 · commit `18f4888`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `178` · nhịp tim cách đây 41.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 792 lệnh đóng, WR 57.32%, E(R) 0.019, PnL -31.25$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 563 | 54.88 | 1.028 | 0.957 | 0.0077 | -57.34 |
| 14 ngày | 746 | 57.1 | 1.093 | 0.997 | 0.0235 | -4.77 |
| 30 ngày | 792 | 57.32 | 1.073 | 0.983 | 0.019 | -31.25 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.028 < 1.2; PF($) cua so 7 ngay = 0.957 < 1.1; PF(R) cua so 14 ngay = 1.093 < 1.2; PF($) cua so 14 ngay = 0.997 < 1.1; PF(R) cua so 30 ngay = 1.073 < 1.2; PF($) cua so 30 ngay = 0.983 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 369 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 248756.0 | 0.0041862 | 0.004146 | 0.004286 | False | False | 0.187 |
| 1000SHIB/USDT:USDT | SHORT | 166666.5 | 0.005189 | 0.005183811 | 0.005114 | True | True | 0.6 |
| ADA/USDT:USDT | SHORT | 2085.0 | 0.237 | 0.235599 | 0.231005 | True | True | 1.084 |
| AERO/USDT:USDT | SHORT | 464.15 | 0.9037 | 0.899686 | 0.87677 | True | True | 0.873 |
| AIOT/USDT:USDT | LONG | 10940.0 | 0.055 | 0.054086 | 0.057285 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| ALGO/USDT:USDT | SHORT | 6613.7 | 0.1218 | 0.123312 | 0.11802 | False | False | 0.231 |
| ATOM/USDT:USDT | SHORT | 258.96 | 1.832 | 1.806654 | 1.78373 | True | True | 1.813 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
