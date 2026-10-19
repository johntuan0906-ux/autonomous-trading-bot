# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 19/10/2026 16:00:05 · commit `a07e325`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `38284` · round `14` · nhịp tim cách đây 29.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 948 lệnh đóng, WR 58.33%, E(R) 0.0366, PnL 137.22$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 372 | 62.63 | 1.257 | 1.171 | 0.0701 | 174.03 |
| 14 ngày | 762 | 56.82 | 1.147 | 1.061 | 0.0402 | 114.3 |
| 30 ngày | 948 | 58.33 | 1.137 | 1.06 | 0.0366 | 137.22 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 14 ngay = 1.147 < 1.2; PF($) cua so 14 ngay = 1.061 < 1.1; PF(R) cua so 30 ngay = 1.137 < 1.2; PF($) cua so 30 ngay = 1.060 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 426 lần cập nhật trọng số · Hội đồng AI: **6 model**

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
| ACE/USDT:USDT | SHORT | 2115.0 | 0.153 | 0.154182 | 0.150045 | False | False | 0.169 |
| ADA/USDT:USDT | SHORT | 1438.0 | 0.2205 | 0.222238 | 0.216155 | False | False | 0.288 |
| AERO/USDT:USDT | SHORT | 263.2 | 0.7949 | 0.804396 | 0.77116 | False | False | 0.0 |
| AIN/USDT:USDT | LONG | 3753.0 | 0.04107 | 0.040404 | 0.042735 | False | False | 0.075 |
| AIOT/USDT:USDT | LONG | 2042.0 | 0.0531 | 0.053294 | 0.05463 | True | True | 0.817 |
| APE/USDT:USDT | SHORT | 1586.0 | 0.1429 | 0.144476 | 0.13896 | False | False | 0.127 |
| ATOM/USDT:USDT | LONG | 176.05 | 1.747 | 1.7328 | 1.7825 | False | False | 0.0 |
| AVAX/USDT:USDT | SHORT | 31.0 | 9.776 | 9.854864 | 9.57884 | False | False | 0.279 |
| AXS/USDT:USDT | SHORT | 373.0 | 1.008 | 1.014686 | 0.991285 | False | False | 0.299 |
| BAT/USDT:USDT | SHORT | 295.35 | 0.18151 | 0.18132849 | 0.17093 | True | True | 0.383 |
| BCH/USDT:USDT | LONG | 1.623 | 278.21 | 276.66969 | 282.060775 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001497 | 0.001477 | 0.001547 | False | False | 0.0 |
| ENA/USDT:USDT | SHORT | 1247.0 | 0.1908 | 0.192804 | 0.18579 | False | False | 0.15 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
