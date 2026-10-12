# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 12/10/2026 11:19:25 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `3104` · round `None` · nhịp tim cách đây 24.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 556 lệnh đóng, WR 56.12%, E(R) 0.0103, PnL 8.42$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 396 | 52.53 | 1.045 | 1.019 | 0.0119 | 15.82 |
| 14 ngày | 525 | 55.43 | 1.024 | 0.985 | 0.0061 | -16.63 |
| 30 ngày | 556 | 56.12 | 1.04 | 1.007 | 0.0103 | 8.42 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.045 < 1.2; PF($) cua so 7 ngay = 1.019 < 1.1; PF(R) cua so 14 ngay = 1.024 < 1.2; PF($) cua so 14 ngay = 0.985 < 1.1; PF(R) cua so 30 ngay = 1.040 < 1.2; PF($) cua so 30 ngay = 1.007 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 246 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000CAT/USDT:USDT | SHORT | 625000.0 | 0.002039 | 0.002055 | 0.001999 | False | False | 0.0 |
| 1000LUNC/USDT:USDT | SHORT | 32894.0 | 0.05139 | 0.051694 | 0.05063 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | LONG | 333333.0 | 0.005482 | 0.005452 | 0.005557 | False | False | 0.0 |
| 1INCH/USDT:USDT | LONG | 14792.0 | 0.09897 | 0.098294 | 0.10066 | False | False | 0.0 |
| AGT/USDT:USDT | SHORT | 35971.0 | 0.018443 | 0.018721 | 0.017748 | False | False | 0.0 |
| AIA/USDT:USDT | SHORT | 14970.0 | 0.0813 | 0.081968 | 0.07963 | False | False | 0.0 |
| AIO/USDT:USDT | SHORT | 20000.0 | 0.0414 | 0.0419 | 0.04015 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
