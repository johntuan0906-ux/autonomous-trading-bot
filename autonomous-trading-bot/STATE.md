# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 23:39:08 · commit `d74f8c5`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3836` · round `29` · nhịp tim cách đây 44.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 866 lệnh đóng, WR 58.55%, E(R) 0.0229, PnL 16.17$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 637 | 56.83 | 1.052 | 0.994 | 0.0142 | -9.92 |
| 14 ngày | 820 | 58.41 | 1.107 | 1.023 | 0.0272 | 42.65 |
| 30 ngày | 866 | 58.55 | 1.088 | 1.008 | 0.0229 | 16.17 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.052 < 1.2; PF($) cua so 7 ngay = 0.994 < 1.1; PF(R) cua so 14 ngay = 1.107 < 1.2; PF($) cua so 14 ngay = 1.023 < 1.1; PF(R) cua so 30 ngay = 1.088 < 1.2; PF($) cua so 30 ngay = 1.008 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 387 lần cập nhật trọng số · Hội đồng AI: **8 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 167785.0 | 0.0040564 | 0.004116 | 0.003906 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 322.9 | 0.8688 | 0.8616429999999999 | 0.830085 | True | True | 0.962 |
| AIN/USDT:USDT | SHORT | 9276.0 | 0.04015 | 0.041228 | 0.037455 | False | False | 0.121 |
| AKE/USDT:USDT | LONG | 15923.0 | 0.025881 | 0.025253 | 0.027451 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 5405.4 | 0.11684 | 0.11869 | 0.112215 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 4370.0 | 0.142 | 0.144288 | 0.13628 | False | False | 0.262 |
| AXL/USDT:USDT | LONG | 2327.7 | 0.0596 | 0.0596596 | 0.06497 | True | True | 0.512 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
