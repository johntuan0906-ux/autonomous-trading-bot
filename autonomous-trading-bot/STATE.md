# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 18:20:25 · commit `117c59a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `26956` · round `30` · nhịp tim cách đây 19.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3396.28 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 825 lệnh đóng, WR 57.94%, E(R) 0.0203, PnL -14.4$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 596 | 55.87 | 1.037 | 0.971 | 0.0101 | -40.49 |
| 14 ngày | 779 | 57.77 | 1.097 | 1.007 | 0.0247 | 12.08 |
| 30 ngày | 825 | 57.94 | 1.078 | 0.993 | 0.0203 | -14.4 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.037 < 1.2; PF($) cua so 7 ngay = 0.971 < 1.1; PF(R) cua so 14 ngay = 1.097 < 1.2; PF($) cua so 14 ngay = 1.007 < 1.1; PF(R) cua so 30 ngay = 1.078 < 1.2; PF($) cua so 30 ngay = 0.993 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 376 lần cập nhật trọng số · Hội đồng AI: **11 model**

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
| 1000PEPE/USDT:USDT | LONG | 226244.0 | 0.0041822 | 0.004138 | 0.004292 | False | False | 0.156 |
| AERO/USDT:USDT | LONG | 448.25 | 0.8972 | 0.8980972 | 0.925085 | True | True | 0.511 |
| AIN/USDT:USDT | SHORT | 5656.0 | 0.03982 | 0.03978018 | 0.03761 | True | True | 0.633 |
| AKE/USDT:USDT | LONG | 13404.0 | 0.025596 | 0.02485 | 0.027461 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 3121.0 | 0.148 | 0.14785199999999998 | 0.143995 | True | True | 0.375 |
| APT/USDT:USDT | SHORT | 992.8 | 0.8133 | 0.823372 | 0.78812 | False | False | 0.0 |
| AR/USDT:USDT | SHORT | 181.2 | 3.887 | 3.942172 | 3.74907 | False | False | 0.0 |
| ASTER/USDT:USDT | LONG | 2308.0 | 0.7001 | 0.695768 | 0.71093 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
