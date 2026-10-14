# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 15:17:32 · commit `f2b9565`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `27452` · round `1` · nhịp tim cách đây 10.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 810 lệnh đóng, WR 57.41%, E(R) 0.0173, PnL -41.69$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 581 | 55.08 | 1.021 | 0.951 | 0.0056 | -67.78 |
| 14 ngày | 764 | 57.2 | 1.085 | 0.991 | 0.0216 | -15.21 |
| 30 ngày | 810 | 57.41 | 1.066 | 0.978 | 0.0173 | -41.69 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.021 < 1.2; PF($) cua so 7 ngay = 0.951 < 1.1; PF(R) cua so 14 ngay = 1.085 < 1.2; PF($) cua so 14 ngay = 0.991 < 1.1; PF(R) cua so 30 ngay = 1.066 < 1.2; PF($) cua so 30 ngay = 0.978 < 1.1
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
| 1000PEPE/USDT:USDT | LONG | 1.0 | 0.0042063 | 0.004217350000000001 | 0.004291 | True | True | 0.822 |
| ACE/USDT:USDT | LONG | 1776.0 | 0.1918 | 0.194492 | 0.19884 | True | True | 1.456 |
| ADA/USDT:USDT | SHORT | 4566.0 | 0.2378 | 0.23999 | 0.232325 | False | False | 0.137 |
| AIOT/USDT:USDT | LONG | 10940.0 | 0.055 | 0.054086 | 0.057285 | False | False | 0.0 |
| ALT/USDT:USDT | LONG | 35714.0 | 0.00838 | 0.00838838 | 0.00873 | True | True | 0.5 |
| ARB/USDT:USDT | LONG | 2648.3 | 0.1897 | 0.190356 | 0.19442 | True | True | 0.847 |
| ATOM/USDT:USDT | SHORT | 499.0 | 1.824 | 1.84404 | 1.7739 | False | False | 0.1 |
| BAT/USDT:USDT | LONG | 1393.1 | 0.19272 | 0.185542 | 0.210665 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
