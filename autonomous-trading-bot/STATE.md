# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 18:50:29 · commit `f68ea89`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `26956` · round `37` · nhịp tim cách đây 164.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 827 lệnh đóng, WR 57.92%, E(R) 0.0193, PnL -22.54$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 598 | 55.85 | 1.032 | 0.966 | 0.0087 | -48.63 |
| 14 ngày | 781 | 57.75 | 1.093 | 1.002 | 0.0236 | 3.93 |
| 30 ngày | 827 | 57.92 | 1.074 | 0.988 | 0.0193 | -22.54 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.032 < 1.2; PF($) cua so 7 ngay = 0.966 < 1.1; PF(R) cua so 14 ngay = 1.093 < 1.2; PF($) cua so 14 ngay = 1.002 < 1.1; PF(R) cua so 30 ngay = 1.074 < 1.2; PF($) cua so 30 ngay = 0.988 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 378 lần cập nhật trọng số · Hội đồng AI: **11 model**

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
| 1000PEPE/USDT:USDT | LONG | 226244.0 | 0.0041822 | 0.004138 | 0.004292 | False | False | 0.179 |
| AERO/USDT:USDT | LONG | 448.25 | 0.8972 | 0.8980972 | 0.925085 | True | True | 0.565 |
| AIN/USDT:USDT | SHORT | 5656.0 | 0.03982 | 0.039552 | 0.03761 | True | True | 0.803 |
| AKE/USDT:USDT | LONG | 13404.0 | 0.025596 | 0.02485 | 0.027461 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 6596.3 | 0.12076 | 0.122276 | 0.11697 | False | False | 0.086 |
| AR/USDT:USDT | SHORT | 181.2 | 3.887 | 3.942172 | 3.74907 | False | False | 0.0 |
| ASTER/USDT:USDT | LONG | 1154.0 | 0.7001 | 0.7008000999999999 | 0.71093 | True | True | 0.3 |
| AXL/USDT:USDT | LONG | 4436.5 | 0.0625 | 0.060246 | 0.068135 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
