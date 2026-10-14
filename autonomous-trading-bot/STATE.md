# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 09:42:24 · commit `269409d`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `126` · nhịp tim cách đây 69.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3396.74 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 779 lệnh đóng, WR 56.87%, E(R) 0.0189, PnL -35.15$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 550 | 54.18 | 1.026 | 0.953 | 0.0071 | -61.24 |
| 14 ngày | 733 | 56.62 | 1.092 | 0.995 | 0.0234 | -8.67 |
| 30 ngày | 779 | 56.87 | 1.072 | 0.981 | 0.0189 | -35.15 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.026 < 1.2; PF($) cua so 7 ngay = 0.953 < 1.1; PF(R) cua so 14 ngay = 1.092 < 1.2; PF($) cua so 14 ngay = 0.995 < 1.1; PF(R) cua so 30 ngay = 1.072 < 1.2; PF($) cua so 30 ngay = 0.981 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 356 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.2 |
| ADA/USDT:USDT | SHORT | 2338.5 | 0.2374 | 0.2371626 | 0.232055 | True | True | 0.468 |
| AERO/USDT:USDT | SHORT | 599.5 | 0.904 | 0.90147 | 0.88315 | True | True | 0.803 |
| AIN/USDT:USDT | SHORT | 14492.0 | 0.04466 | 0.04535 | 0.042935 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| APR/USDT:USDT | SHORT | 7874.0 | 0.05329 | 0.05456 | 0.050115 | False | False | 0.291 |
| ATOM/USDT:USDT | SHORT | 207.655 | 1.848 | 1.8330389999999999 | 1.787805 | True | True | 1.121 |
| BTR/USDT:USDT | SHORT | 21459.0 | 0.04911 | 0.049576 | 0.047945 | False | False | 0.129 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
