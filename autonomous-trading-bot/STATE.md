# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 15:01:58 · commit `5432cd4`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `64932` · round `None` · nhịp tim cách đây 4.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 807 lệnh đóng, WR 57.25%, E(R) 0.0145, PnL -65.09$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 578 | 54.84 | 1.006 | 0.934 | 0.0016 | -91.18 |
| 14 ngày | 761 | 57.03 | 1.073 | 0.978 | 0.0186 | -38.61 |
| 30 ngày | 807 | 57.25 | 1.055 | 0.966 | 0.0145 | -65.09 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.006 < 1.2; PF($) cua so 7 ngay = 0.934 < 1.1; PF(R) cua so 14 ngay = 1.073 < 1.2; PF($) cua so 14 ngay = 0.978 < 1.1; PF(R) cua so 30 ngay = 1.055 < 1.2; PF($) cua so 30 ngay = 0.966 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 375 lần cập nhật trọng số · Hội đồng AI: **12 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ACE/USDT:USDT | LONG | 1775.5 | 0.1918 | 0.192492 | 0.19884 | True | True | 0.746 |
| AIOT/USDT:USDT | LONG | 10940.0 | 0.055 | 0.054086 | 0.057285 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 18935.0 | 0.0258561 | 0.025328 | 0.027176 | False | False | 0.272 |
| ALGO/USDT:USDT | SHORT | 3306.85 | 0.1218 | 0.12106600000000001 | 0.11802 | True | True | 0.985 |
| ALT/USDT:USDT | LONG | 71428.0 | 0.00838 | 0.00824 | 0.00873 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 3097.5 | 0.1528 | 0.151707 | 0.148765 | True | True | 1.177 |
| AR/USDT:USDT | SHORT | 217.8 | 3.952 | 3.997894 | 3.837265 | False | False | 0.131 |
| ARB/USDT:USDT | LONG | 5296.6 | 0.1897 | 0.187812 | 0.19442 | False | False | 0.106 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
