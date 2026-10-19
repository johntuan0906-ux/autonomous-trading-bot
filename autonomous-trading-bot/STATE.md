# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 19/10/2026 17:30:07 · commit `b285d3e`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `38284` · round `35` · nhịp tim cách đây 32.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3331.79 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 955 lệnh đóng, WR 58.12%, E(R) 0.0322, PnL 126.36$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 365 | 64.38 | 1.277 | 1.227 | 0.0759 | 219.64 |
| 14 ngày | 763 | 56.75 | 1.138 | 1.067 | 0.0378 | 124.38 |
| 30 ngày | 955 | 58.12 | 1.12 | 1.055 | 0.0322 | 126.36 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 14 ngay = 1.138 < 1.2; PF($) cua so 14 ngay = 1.067 < 1.1; PF(R) cua so 30 ngay = 1.120 < 1.2; PF($) cua so 30 ngay = 1.055 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 432 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (14)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 719.0 | 0.2205 | 0.21886899999999998 | 0.216155 | True | True | 1.438 |
| AIN/USDT:USDT | LONG | 1876.5 | 0.04107 | 0.041187 | 0.042735 | True | True | 0.676 |
| APE/USDT:USDT | SHORT | 1586.0 | 0.1427 | 0.145934 | 0.140565 | False | False | 0.0 |
| AR/USDT:USDT | LONG | 56.5 | 3.874 | 3.829762 | 3.984595 | False | False | 0.09 |
| ARB/USDT:USDT | LONG | 893.4 | 0.199 | 0.196202 | 0.205995 | False | False | 0.143 |
| AVAX/USDT:USDT | SHORT | 15.5 | 9.776 | 9.740432 | 9.57884 | True | True | 0.951 |
| AXL/USDT:USDT | LONG | 1155.3 | 0.0578 | 0.056298 | 0.060505 | False | False | 0.2 |
| AXS/USDT:USDT | SHORT | 93.0 | 1.007 | 0.999522 | 0.98939 | True | True | 1.562 |
| BANK/USDT:USDT | SHORT | 12135.0 | 0.02632 | 0.026526 | 0.025805 | False | False | 0.243 |
| BAT/USDT:USDT | SHORT | 295.3 | 0.1812 | 0.187912 | 0.173765 | False | False | 0.0 |
| BNB/USDT:USDT | LONG | 1.21 | 727.33 | 724.749348 | 732.20663 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001499 | 0.001457 | 0.00152 | False | False | 0.0 |
| ENA/USDT:USDT | SHORT | 623.5 | 0.1908 | 0.18890200000000001 | 0.18579 | True | True | 1.447 |
| ETHFI/USDT:USDT | LONG | 269.5 | 0.7034 | 0.694126 | 0.726585 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
