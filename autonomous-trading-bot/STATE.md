# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 07:51:34 · commit `38dfb7a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `110` · nhịp tim cách đây 2.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 642 lệnh đóng, WR 56.85%, E(R) 0.0319, PnL 80.45$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 413 | 53.27 | 1.088 | 1.06 | 0.0235 | 54.36 |
| 14 ngày | 611 | 56.3 | 1.117 | 1.042 | 0.0294 | 55.4 |
| 30 ngày | 642 | 56.85 | 1.125 | 1.057 | 0.0319 | 80.45 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.088 < 1.2; PF($) cua so 7 ngay = 1.060 < 1.1; PF(R) cua so 14 ngay = 1.117 < 1.2; PF($) cua so 14 ngay = 1.042 < 1.1; PF(R) cua so 30 ngay = 1.125 < 1.2; PF($) cua so 30 ngay = 1.057 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 286 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000PEPE/USDT:USDT | SHORT | 86956.5 | 0.0038845 | 0.00383855 | 0.003739 | True | True | 1.299 |
| 1000SHIB/USDT:USDT | SHORT | 80645.0 | 0.005131 | 0.005109 | 0.004976 | True | True | 0.855 |
| ACE/USDT:USDT | SHORT | 3563.0 | 0.1763 | 0.179106 | 0.169285 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 1511.0 | 0.2303 | 0.22915400000000002 | 0.22203 | True | True | 0.846 |
| AIN/USDT:USDT | LONG | 10482.0 | 0.04624 | 0.045286 | 0.048625 | False | False | 0.231 |
| AIOT/USDT:USDT | LONG | 8025.0 | 0.0551 | 0.053854 | 0.058215 | False | False | 0.241 |
| ALGO/USDT:USDT | SHORT | 2606.85 | 0.11885 | 0.117799 | 0.114055 | True | True | 1.048 |
| APT/USDT:USDT | SHORT | 372.2 | 0.8041 | 0.786316 | 0.77052 | True | True | 1.824 |
| AR/USDT:USDT | SHORT | 64.25 | 3.789 | 3.730905 | 3.594475 | True | True | 1.247 |
| ASTER/USDT:USDT | SHORT | 1365.0 | 0.6809 | 0.688224 | 0.66259 | False | False | 0.15 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
