# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 14:42:30 · commit `5267a03`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `199` · nhịp tim cách đây 7.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3368.98 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 798 lệnh đóng, WR 57.52%, E(R) 0.0192, PnL -28.94$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 569 | 55.18 | 1.029 | 0.959 | 0.008 | -55.04 |
| 14 ngày | 752 | 57.31 | 1.093 | 0.999 | 0.0236 | -2.47 |
| 30 ngày | 798 | 57.52 | 1.074 | 0.984 | 0.0192 | -28.94 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.029 < 1.2; PF($) cua so 7 ngay = 0.959 < 1.1; PF(R) cua so 14 ngay = 1.093 < 1.2; PF($) cua so 14 ngay = 0.999 < 1.1; PF(R) cua so 30 ngay = 1.074 < 1.2; PF($) cua so 30 ngay = 0.984 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 375 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| ACE/USDT:USDT | LONG | 1775.5 | 0.1918 | 0.192392 | 0.19884 | True | True | 0.71 |
| AIOT/USDT:USDT | LONG | 10940.0 | 0.055 | 0.054086 | 0.057285 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 18935.0 | 0.0258561 | 0.025328 | 0.027176 | False | False | 0.272 |
| ALGO/USDT:USDT | SHORT | 3306.85 | 0.1218 | 0.12106600000000001 | 0.11802 | True | True | 0.985 |
| ALT/USDT:USDT | LONG | 71428.0 | 0.00838 | 0.00824 | 0.00873 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 3097.5 | 0.1528 | 0.152307 | 0.148765 | True | True | 0.805 |
| AR/USDT:USDT | SHORT | 217.8 | 3.952 | 3.997894 | 3.837265 | False | False | 0.087 |
| ARB/USDT:USDT | LONG | 5296.6 | 0.1897 | 0.187812 | 0.19442 | False | False | 0.106 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
