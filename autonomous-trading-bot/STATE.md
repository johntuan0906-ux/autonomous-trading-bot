# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 28/10/2026 06:19:32 · commit `fa7ea16`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `47488` · round `600` · nhịp tim cách đây 179.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3202.56 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3344 lệnh đóng, WR 44.77%, E(R) 1.3104, PnL -1090.47$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 9 | 0.0 | 0.096 | 0.096 | -0.6656 | -71.88 |
| 14 ngày | 2572 | 41.25 | 6.409 | 0.722 | 1.6988 | -1035.98 |
| 30 ngày | 3313 | 44.55 | 5.374 | 0.795 | 1.3219 | -1115.52 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.096 < 1.2; PF($) cua so 7 ngay = 0.096 < 1.1; PF($) cua so 14 ngay = 0.722 < 1.1; PF($) cua so 30 ngay = 0.795 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.2%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 457 lần cập nhật trọng số · Hội đồng AI: **6 model**

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
| ADA/USDT:USDT | SHORT | 650.0 | 0.2075 | 0.225952 | 0.116558 | False | False | 0.379 |
| AERO/USDT:USDT | LONG | 263.2 | 0.6900999999999999 | 0.660616 | 0.752668 | False | False | 0.655 |
| AIOT/USDT:USDT | LONG | 1295.7 | 0.0616 | 0.061661600000000004 | 0.093547 | True | True | 1.728 |
| APT/USDT:USDT | SHORT | 145.5 | 0.7186 | 0.801032 | 0.312328 | False | False | 0.518 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
