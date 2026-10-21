# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 21/10/2026 12:53:24 · commit `29bfd01`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `2204` · round `29` · nhịp tim cách đây 42.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3335 lệnh đóng, WR 44.89%, E(R) 1.3157, PnL -1018.6$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2532 | 41.0 | 6.514 | 0.735 | 1.7286 | -948.97 |
| 14 ngày | 3106 | 43.53 | 5.601 | 0.789 | 1.4093 | -1044.69 |
| 30 ngày | 3335 | 44.89 | 5.369 | 0.814 | 1.3157 | -1018.6 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.735 < 1.1; PF($) cua so 14 ngay = 0.789 < 1.1; PF($) cua so 30 ngay = 0.814 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.2%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 455 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (4)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| APT/USDT:USDT | LONG | 150.4 | 0.8302 | 0.750428 | 1.223362 | False | False | 0.033 |
| CFX/USDT:USDT | LONG | 3541.0 | 0.05521 | 0.051822 | 0.071908 | False | False | 0.0 |
| CYBER/USDT:USDT | LONG | 544.2 | 0.322 | 0.29995 | 0.430675 | False | False | 0.0 |
| DOT/USDT:USDT | LONG | 131.9 | 1.1616 | 1.070656 | 1.609824 | False | False | 0.057 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
