# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 17/11/2026 02:04:53 · commit `4e0d25d`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `64792` · round `392` · nhịp tim cách đây 160.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3229.34 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3055 lệnh đóng, WR 40.95%, E(R) 0.2313, PnL -1052.19$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 27 | 33.33 | 1.22 | 0.783 | 0.1027 | -10.87 |
| 14 ngày | 132 | 41.67 | 1.69 | 0.913 | 0.2573 | -22.84 |
| 30 ngày | 2118 | 33.14 | 2.122 | 0.589 | 0.3234 | -1270.31 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 0.783 < 1.1; PF($) cua so 14 ngay [lenh BOT] = 0.734 < 1.1; PF(R) cua so 30 ngay [lenh BOT] = 0.654 < 1.2; PF($) cua so 30 ngay [lenh BOT] = 0.426 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 779 lần cập nhật trọng số · Hội đồng AI: **5 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 33337.0 | 0.002349 | 0.002469 | 0.002109 | False | False | 0.675 |
| 1000PEPE/USDT:USDT | SHORT | 24716.3 | 0.0039421 | 0.003938157899999999 | 0.003522 | True | True | 1.039 |
| ADA/USDT:USDT | SHORT | 550.0 | 0.1504 | 0.157708 | 0.135784 | False | False | 0.246 |
| BANK/USDT:USDT | SHORT | 3794.0 | 0.02148 | 0.02145852 | 0.017742 | True | True | 4.055 |
| BAT/USDT:USDT | SHORT | 295.3 | 0.1192600326624 | 0.09882 | 0.08451 | False | False | 1.352 |
| CKB/USDT:USDT | LONG | 54443.2 | 0.000833 | 0.000833833 | 0.000915 | True | True | 1.136 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
