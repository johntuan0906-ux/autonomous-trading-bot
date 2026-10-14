# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 21:39:05 · commit `15d714f`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3836` · round `None` · nhịp tim cách đây 0.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 856 lệnh đóng, WR 58.18%, E(R) 0.0192, PnL -17.43$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 627 | 56.3 | 1.033 | 0.971 | 0.0091 | -43.52 |
| 14 ngày | 810 | 58.02 | 1.091 | 1.005 | 0.0234 | 9.05 |
| 30 ngày | 856 | 58.18 | 1.073 | 0.991 | 0.0192 | -17.43 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.033 < 1.2; PF($) cua so 7 ngay = 0.971 < 1.1; PF(R) cua so 14 ngay = 1.091 < 1.2; PF($) cua so 14 ngay = 1.005 < 1.1; PF(R) cua so 30 ngay = 1.073 < 1.2; PF($) cua so 30 ngay = 0.991 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 383 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| 1000SHIB/USDT:USDT | SHORT | 92592.5 | 0.005036 | 0.005030964 | 0.004901 | True | True | 0.389 |
| ADA/USDT:USDT | SHORT | 3021.0 | 0.2276 | 0.23091 | 0.219325 | False | False | 0.06 |
| AERO/USDT:USDT | SHORT | 322.85 | 0.8688 | 0.8679312 | 0.830085 | True | True | 0.491 |
| AIN/USDT:USDT | SHORT | 9242.0 | 0.03853 | 0.039612 | 0.035825 | False | False | 0.157 |
| ALGO/USDT:USDT | SHORT | 2340.8 | 0.11693 | 0.11681307 | 0.11159 | True | True | 0.351 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 436.6 | 0.8029 | 0.793826 | 0.77427 | True | True | 1.292 |
| ARB/USDT:USDT | SHORT | 1973.15 | 0.1842 | 0.18166700000000002 | 0.177865 | True | True | 1.5 |
| AXS/USDT:USDT | SHORT | 382.0 | 1.097 | 1.09054 | 1.0643 | True | True | 0.994 |
| BANK/USDT:USDT | SHORT | 19531.0 | 0.02688 | 0.026668 | 0.02624 | True | True | 1.328 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
