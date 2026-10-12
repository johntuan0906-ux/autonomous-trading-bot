# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 11:49:27 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3104` · round `3` · nhịp tim cách đây 159.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3786.18 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 559 lệnh đóng, WR 56.17%, E(R) 0.0086, PnL -0.49$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 393 | 53.44 | 1.063 | 1.041 | 0.0165 | 33.54 |
| 14 ngày | 528 | 55.49 | 1.017 | 0.977 | 0.0044 | -25.54 |
| 30 ngày | 559 | 56.17 | 1.033 | 1.0 | 0.0086 | -0.49 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.063 < 1.2; PF($) cua so 7 ngay = 1.041 < 1.1; PF(R) cua so 14 ngay = 1.017 < 1.2; PF($) cua so 14 ngay = 0.977 < 1.1; PF(R) cua so 30 ngay = 1.033 < 1.2; PF($) cua so 30 ngay = 1.000 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 247 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000CAT/USDT:USDT | SHORT | 625000.0 | 0.002039 | 0.002055 | 0.001999 | False | False | 0.063 |
| 1000CHEEMS/USDT:USDT | LONG | 2222222.0 | 0.0005265 | 0.000522 | 0.000536 | False | False | 0.067 |
| 1000SHIB/USDT:USDT | LONG | 166666.5 | 0.005482 | 0.005497 | 0.005557 | True | True | 1.0 |
| 1INCH/USDT:USDT | LONG | 7396.0 | 0.09897 | 0.099102 | 0.10066 | True | True | 0.695 |
| 1MBABYDOGE/USDT:USDT | LONG | 4347826.0 | 0.0003913 | 0.000389 | 0.000396 | False | False | 0.0 |
| AERO/USDT:USDT | LONG | 1107.4 | 0.9348 | 0.92577 | 0.957375 | False | False | 0.266 |
| AGT/USDT:USDT | SHORT | 35971.0 | 0.018443 | 0.018721 | 0.017748 | False | False | 0.284 |
| AIA/USDT:USDT | SHORT | 14970.0 | 0.0813 | 0.081968 | 0.07963 | False | False | 0.165 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
