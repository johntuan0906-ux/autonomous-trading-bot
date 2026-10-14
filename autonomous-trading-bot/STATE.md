# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 01:01:30 · commit `0b22a2a`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `7` · nhịp tim cách đây 56.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3397.36 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 872 lệnh đóng, WR 58.6%, E(R) 0.0259, PnL 43.87$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 643 | 56.92 | 1.068 | 1.011 | 0.0184 | 17.78 |
| 14 ngày | 826 | 58.47 | 1.119 | 1.037 | 0.0303 | 70.34 |
| 30 ngày | 872 | 58.6 | 1.099 | 1.021 | 0.0259 | 43.87 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.068 < 1.2; PF($) cua so 7 ngay = 1.011 < 1.1; PF(R) cua so 14 ngay = 1.119 < 1.2; PF($) cua so 14 ngay = 1.037 < 1.1; PF(R) cua so 30 ngay = 1.099 < 1.2; PF($) cua so 30 ngay = 1.021 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 390 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| 1000PEPE/USDT:USDT | SHORT | 178253.0 | 0.0040849 | 0.004141 | 0.003945 | False | False | 0.0 |
| AIN/USDT:USDT | SHORT | 4638.0 | 0.04015 | 0.040109849999999996 | 0.037455 | True | True | 0.306 |
| AKE/USDT:USDT | LONG | 15923.0 | 0.025881 | 0.025253 | 0.027451 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 5405.4 | 0.11684 | 0.11869 | 0.112215 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.262 |
| APT/USDT:USDT | SHORT | 858.5 | 0.7967 | 0.808348 | 0.76758 | False | False | 0.0 |
| ARB/USDT:USDT | SHORT | 1840.9 | 0.1842 | 0.1840158 | 0.17741 | True | True | 0.479 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
