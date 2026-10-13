# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 10:21:35 · commit `2bbd0e9`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `102888` · round `23` · nhịp tim cách đây 84.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3654.48 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 675 lệnh đóng, WR 57.33%, E(R) 0.0369, PnL 124.9$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 446 | 54.26 | 1.12 | 1.101 | 0.0318 | 98.81 |
| 14 ngày | 644 | 56.83 | 1.139 | 1.072 | 0.0348 | 99.85 |
| 30 ngày | 675 | 57.33 | 1.146 | 1.084 | 0.0369 | 124.9 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.120 < 1.2; PF(R) cua so 14 ngay = 1.139 < 1.2; PF($) cua so 14 ngay = 1.072 < 1.1; PF(R) cua so 30 ngay = 1.146 < 1.2; PF($) cua so 30 ngay = 1.084 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 303 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 143472.0 | 0.0039233 | 0.003993 | 0.003748 | False | False | 0.0 |
| ACE/USDT:USDT | SHORT | 2791.0 | 0.1789 | 0.182482 | 0.169945 | False | False | 0.084 |
| AKE/USDT:USDT | SHORT | 10718.0 | 0.0233455 | 0.0233221545 | 0.022181 | True | True | 0.479 |
| ASTER/USDT:USDT | SHORT | 1219.0 | 0.6878 | 0.696 | 0.6673 | False | False | 0.012 |
| ATOM/USDT:USDT | SHORT | 364.43 | 1.812 | 1.83944 | 1.7434 | False | False | 0.255 |
| AXL/USDT:USDT | SHORT | 3037.65 | 0.0563 | 0.056022999999999996 | 0.052185 | True | True | 0.668 |
| AXS/USDT:USDT | SHORT | 270.0 | 1.139 | 1.137861 | 1.092775 | True | True | 0.433 |
| BOME/USDT:USDT | SHORT | 273224.0 | 0.0007747 | 0.0007739253000000001 | 0.00073 | True | True | 0.306 |
| BR/USDT:USDT | SHORT | 444.5 | 0.45636 | 0.452569 | 0.428265 | True | True | 0.837 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
