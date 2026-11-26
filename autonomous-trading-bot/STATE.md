# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 26/11/2026 16:06:25 · commit `8f28e00`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `21400` · round `222` · nhịp tim cách đây 1.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 1000.0 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3085 lệnh đóng, WR 41.1%, E(R) 0.2371, PnL -966.27$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 23 | 56.52 | 3.904 | 3.303 | 0.9119 | 63.33 |
| 14 ngày | 47 | 46.81 | 2.951 | 2.478 | 0.6314 | 85.52 |
| 30 ngày | 177 | 42.37 | 1.915 | 1.045 | 0.3419 | 16.89 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 30 ngay [lenh BOT] = 1.010 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 785 lần cập nhật trọng số · Hội đồng AI: **3 model**

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
| AIOT/USDT:USDT | LONG | 331.0 | 0.0907 | 0.0907907 | 0.107632 | True | True | 1.217 |
| BANK/USDT:USDT | SHORT | 7326.0 | 0.01514 | 0.015686 | 0.014048 | False | False | 0.897 |
| CKB/USDT:USDT | LONG | 83333.0 | 0.000805 | 0.000757 | 0.000901 | False | False | 1.0 |
| FIL/USDT:USDT | LONG | 212.7 | 0.5479 | 0.529102 | 0.585496 | False | False | 0.053 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
