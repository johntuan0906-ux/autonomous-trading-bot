# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 19/10/2026 15:30:03 · commit `aaffff5`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `38284` · round `7` · nhịp tim cách đây 109.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 946 lệnh đóng, WR 58.25%, E(R) 0.036, PnL 135.81$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 371 | 62.26 | 1.239 | 1.159 | 0.066 | 163.01 |
| 14 ngày | 763 | 56.75 | 1.147 | 1.064 | 0.0403 | 120.17 |
| 30 ngày | 946 | 58.25 | 1.135 | 1.059 | 0.036 | 135.81 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 14 ngay = 1.147 < 1.2; PF($) cua so 14 ngay = 1.064 < 1.1; PF(R) cua so 30 ngay = 1.135 < 1.2; PF($) cua so 30 ngay = 1.059 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 424 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (14)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 59808.0 | 0.0041158 | 0.004074 | 0.004221 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 1438.0 | 0.2205 | 0.222238 | 0.216155 | False | False | 0.288 |
| AIN/USDT:USDT | LONG | 3753.0 | 0.04107 | 0.040404 | 0.042735 | False | False | 0.075 |
| AIOT/USDT:USDT | LONG | 2042.0 | 0.0531 | 0.0531531 | 0.05463 | True | True | 0.327 |
| APE/USDT:USDT | SHORT | 1586.0 | 0.1429 | 0.144476 | 0.13896 | False | False | 0.127 |
| ATOM/USDT:USDT | LONG | 176.05 | 1.747 | 1.7328 | 1.7825 | False | False | 0.0 |
| AVAX/USDT:USDT | SHORT | 31.0 | 9.776 | 9.854864 | 9.57884 | False | False | 0.279 |
| AXL/USDT:USDT | LONG | 1155.25 | 0.0577 | 0.057759 | 0.060405 | True | True | 0.555 |
| AXS/USDT:USDT | SHORT | 373.0 | 1.008 | 1.014686 | 0.991285 | False | False | 0.15 |
| BAT/USDT:USDT | SHORT | 590.7 | 0.18151 | 0.185742 | 0.17093 | False | False | 0.038 |
| BNB/USDT:USDT | LONG | 1.21 | 727.3 | 725.247468 | 732.43133 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001497 | 0.001477 | 0.001547 | False | False | 0.0 |
| CRV/USDT:USDT | LONG | 316.1 | 0.3543 | 0.3546543 | 0.364185 | True | True | 0.531 |
| ENA/USDT:USDT | SHORT | 1247.0 | 0.1908 | 0.192804 | 0.18579 | False | False | 0.15 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
