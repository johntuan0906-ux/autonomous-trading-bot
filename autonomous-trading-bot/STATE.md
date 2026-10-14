# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 19:46:28 · commit `f29eb4e`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `44348` · round `1` · nhịp tim cách đây 14.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 836 lệnh đóng, WR 58.13%, E(R) 0.0218, PnL -0.0$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 607 | 56.18 | 1.046 | 0.982 | 0.0123 | -26.09 |
| 14 ngày | 790 | 57.97 | 1.104 | 1.015 | 0.0262 | 26.47 |
| 30 ngày | 836 | 58.13 | 1.084 | 1.0 | 0.0218 | -0.0 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.046 < 1.2; PF($) cua so 7 ngay = 0.982 < 1.1; PF(R) cua so 14 ngay = 1.104 < 1.2; PF($) cua so 14 ngay = 1.015 < 1.1; PF(R) cua so 30 ngay = 1.084 < 1.2; PF($) cua so 30 ngay = 1.000 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 378 lần cập nhật trọng số · Hội đồng AI: **9 model**

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
| 1000PEPE/USDT:USDT | LONG | 177304.0 | 0.0041094 | 0.004053 | 0.004249 | False | False | 0.229 |
| ADA/USDT:USDT | SHORT | 1058.0 | 0.2355 | 0.23188199999999998 | 0.22959 | True | True | 2.03 |
| AERO/USDT:USDT | LONG | 659.2 | 0.8913 | 0.876132 | 0.92922 | False | False | 0.0 |
| AIN/USDT:USDT | SHORT | 5656.0 | 0.03982 | 0.038542 | 0.03761 | True | True | 1.946 |
| AKE/USDT:USDT | LONG | 15822.0 | 0.025075 | 0.024443 | 0.026655 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 5291.0 | 0.12084 | 0.12273 | 0.116115 | False | False | 0.185 |
| APE/USDT:USDT | SHORT | 5235.0 | 0.1468 | 0.14871 | 0.142025 | False | False | 0.209 |
| AR/USDT:USDT | SHORT | 45.3 | 3.887 | 3.8715859999999997 | 3.74907 | True | True | 0.779 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
