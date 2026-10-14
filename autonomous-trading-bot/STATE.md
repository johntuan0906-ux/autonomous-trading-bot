# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 13:42:28 · commit `9f9fc74`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `185` · nhịp tim cách đây 28.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 794 lệnh đóng, WR 57.3%, E(R) 0.018, PnL -39.35$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 565 | 54.87 | 1.023 | 0.951 | 0.0062 | -65.44 |
| 14 ngày | 748 | 57.09 | 1.088 | 0.992 | 0.0224 | -12.87 |
| 30 ngày | 794 | 57.3 | 1.069 | 0.979 | 0.018 | -39.35 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.023 < 1.2; PF($) cua so 7 ngay = 0.951 < 1.1; PF(R) cua so 14 ngay = 1.088 < 1.2; PF($) cua so 14 ngay = 0.992 < 1.1; PF(R) cua so 30 ngay = 1.069 < 1.2; PF($) cua so 30 ngay = 0.979 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 371 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| AIN/USDT:USDT | SHORT | 6410.0 | 0.04322 | 0.043176780000000005 | 0.04127 | True | True | 0.308 |
| AIOT/USDT:USDT | LONG | 10940.0 | 0.055 | 0.054086 | 0.057285 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 3306.85 | 0.1218 | 0.1216782 | 0.11802 | True | True | 0.509 |
| ALT/USDT:USDT | LONG | 71428.0 | 0.00838 | 0.00824 | 0.00873 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 6134.0 | 0.1527 | 0.15433 | 0.148625 | False | False | 0.061 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
