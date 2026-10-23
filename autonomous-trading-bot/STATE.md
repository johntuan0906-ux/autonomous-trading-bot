# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 23/10/2026 20:48:13 · commit `84929d9`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `75016` · round `552` · nhịp tim cách đây 73.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3216.9 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3336 lệnh đóng, WR 44.87%, E(R) 1.315, PnL -1031.05$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 2392 | 39.63 | 6.78 | 0.633 | 1.8199 | -1165.89 |
| 14 ngày | 2927 | 42.57 | 5.787 | 0.756 | 1.4924 | -1128.27 |
| 30 ngày | 3334 | 44.9 | 5.374 | 0.815 | 1.3164 | -1011.1 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.633 < 1.1; PF($) cua so 14 ngay = 0.756 < 1.1; PF($) cua so 30 ngay = 0.815 < 1.1
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
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (4)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| APR/USDT:USDT | SHORT | 2164.0 | 0.02624 | 0.031784 | -0.001084 | False | False | 0.186 |
| APT/USDT:USDT | LONG | 150.4 | 0.8302 | 0.750428 | 1.223362 | False | False | 0.165 |
| CYBER/USDT:USDT | LONG | 544.2 | 0.322 | 0.29995 | 0.430675 | False | False | 0.499 |
| DOT/USDT:USDT | LONG | 131.9 | 1.1616 | 1.070656 | 1.609824 | False | False | 0.415 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
