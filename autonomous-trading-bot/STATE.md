# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 00:09:09 · commit `c03d1f2`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3836` · round `36` · nhịp tim cách đây 37.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3395.64 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 867 lệnh đóng, WR 58.48%, E(R) 0.0217, PnL 5.58$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 638 | 56.74 | 1.046 | 0.987 | 0.0126 | -20.51 |
| 14 ngày | 821 | 58.34 | 1.101 | 1.017 | 0.0259 | 32.06 |
| 30 ngày | 867 | 58.48 | 1.083 | 1.003 | 0.0217 | 5.58 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.046 < 1.2; PF($) cua so 7 ngay = 0.987 < 1.1; PF(R) cua so 14 ngay = 1.101 < 1.2; PF($) cua so 14 ngay = 1.017 < 1.1; PF(R) cua so 30 ngay = 1.083 < 1.2; PF($) cua so 30 ngay = 1.003 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 388 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| ACE/USDT:USDT | LONG | 2783.0 | 0.1895 | 0.185908 | 0.19848 | False | False | 0.223 |
| AIN/USDT:USDT | SHORT | 9276.0 | 0.04015 | 0.041228 | 0.037455 | False | False | 0.121 |
| AKE/USDT:USDT | LONG | 15923.0 | 0.025881 | 0.025253 | 0.027451 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 5405.4 | 0.11684 | 0.11869 | 0.112215 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.262 |
| APT/USDT:USDT | SHORT | 858.5 | 0.7967 | 0.808348 | 0.76758 | False | False | 0.0 |
| AXL/USDT:USDT | LONG | 2327.7 | 0.0596 | 0.06292600000000001 | 0.06497 | True | True | 2.048 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
