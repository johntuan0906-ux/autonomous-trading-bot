# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 19:31:37 · commit `e71ff3a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `4228` · round `7` · nhịp tim cách đây 173.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 698 lệnh đóng, WR 56.73%, E(R) 0.0385, PnL 86.86$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 469 | 53.52 | 1.129 | 1.058 | 0.0344 | 60.77 |
| 14 ngày | 652 | 56.44 | 1.182 | 1.081 | 0.045 | 113.34 |
| 30 ngày | 698 | 56.73 | 1.151 | 1.056 | 0.0385 | 86.86 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.129 < 1.2; PF($) cua so 7 ngay = 1.058 < 1.1; PF(R) cua so 14 ngay = 1.182 < 1.2; PF($) cua so 14 ngay = 1.081 < 1.1; PF(R) cua so 30 ngay = 1.151 < 1.2; PF($) cua so 30 ngay = 1.056 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 315 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (10)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 185185.0 | 0.004072 | 0.004126 | 0.003937 | False | False | 0.141 |
| AERO/USDT:USDT | SHORT | 486.15 | 0.8829 | 0.8820171 | 0.85719 | True | True | 0.574 |
| AKE/USDT:USDT | SHORT | 10638.0 | 0.024452 | 0.024206 | 0.023277 | True | True | 1.023 |
| AR/USDT:USDT | SHORT | 80.3 | 3.902 | 3.888133 | 3.746335 | True | True | 0.723 |
| ARB/USDT:USDT | SHORT | 2059.3 | 0.1849 | 0.18351399999999998 | 0.17883 | True | True | 1.071 |
| ASTER/USDT:USDT | SHORT | 730.0 | 0.6903 | 0.689424 | 0.67318 | True | True | 0.628 |
| ATOM/USDT:USDT | SHORT | 194.17 | 1.809 | 1.796875 | 1.744625 | True | True | 0.971 |
| AVAX/USDT:USDT | SHORT | 32.0 | 10.292 | 10.25903 | 9.90185 | True | True | 0.711 |
| AXL/USDT:USDT | SHORT | 4604.1 | 0.0551 | 0.055042999999999995 | 0.052385 | True | True | 0.552 |
| AXS/USDT:USDT | SHORT | 720.0 | 1.133 | 1.146886 | 1.098285 | False | False | 0.216 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
