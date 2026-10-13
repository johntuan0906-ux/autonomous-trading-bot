# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 06:42:22 · commit `631d042`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `82` · nhịp tim cách đây 33.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3401.95 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 766 lệnh đóng, WR 56.4%, E(R) 0.018, PnL -43.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 537 | 53.45 | 1.021 | 0.946 | 0.0057 | -69.89 |
| 14 ngày | 720 | 56.11 | 1.088 | 0.989 | 0.0226 | -17.32 |
| 30 ngày | 766 | 56.4 | 1.069 | 0.976 | 0.018 | -43.8 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.021 < 1.2; PF($) cua so 7 ngay = 0.946 < 1.1; PF(R) cua so 14 ngay = 1.088 < 1.2; PF($) cua so 14 ngay = 0.989 < 1.1; PF(R) cua so 30 ngay = 1.069 < 1.2; PF($) cua so 30 ngay = 0.976 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 343 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 156494.0 | 0.0042109 | 0.004147 | 0.004371 | False | False | 0.236 |
| ACE/USDT:USDT | LONG | 2829.0 | 0.1955 | 0.191966 | 0.204335 | False | False | 0.028 |
| ADA/USDT:USDT | SHORT | 2214.0 | 0.2363 | 0.23606370000000002 | 0.230655 | True | True | 0.487 |
| AERO/USDT:USDT | SHORT | 972.5 | 0.9 | 0.910282 | 0.874295 | False | False | 0.146 |
| AIN/USDT:USDT | SHORT | 12468.0 | 0.04434 | 0.045142 | 0.042335 | False | False | 0.2 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.206 |
| APT/USDT:USDT | SHORT | 389.4 | 0.8413 | 0.83772 | 0.8092 | True | True | 0.779 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
