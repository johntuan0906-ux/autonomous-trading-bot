# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 20:01:41 · commit `6d745b0`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `101832` · round `2` · nhịp tim cách đây 1.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 707 lệnh đóng, WR 57.0%, E(R) 0.0374, PnL 82.62$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 478 | 53.97 | 1.123 | 1.053 | 0.0329 | 56.53 |
| 14 ngày | 661 | 56.73 | 1.177 | 1.077 | 0.0438 | 109.1 |
| 30 ngày | 707 | 57.0 | 1.147 | 1.052 | 0.0374 | 82.62 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.123 < 1.2; PF($) cua so 7 ngay = 1.053 < 1.1; PF(R) cua so 14 ngay = 1.177 < 1.2; PF($) cua so 14 ngay = 1.077 < 1.1; PF(R) cua so 30 ngay = 1.147 < 1.2; PF($) cua so 30 ngay = 1.052 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 317 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000SHIB/USDT:USDT | SHORT | 178571.0 | 0.005179 | 0.005235 | 0.005039 | False | False | 0.0 |
| AIN/USDT:USDT | SHORT | 15060.0 | 0.04264 | 0.043304 | 0.04098 | False | False | 0.0 |
| AIOT/USDT:USDT | LONG | 13661.0 | 0.0541 | 0.053368 | 0.05593 | False | False | 0.0 |
| ALT/USDT:USDT | SHORT | 66666.0 | 0.00808 | 0.00823 | 0.007705 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 726.2 | 0.8237 | 0.83747 | 0.789275 | False | False | 0.022 |
| AXS/USDT:USDT | SHORT | 720.0 | 1.133 | 1.146886 | 1.098285 | False | False | 0.216 |
| BANK/USDT:USDT | SHORT | 30487.0 | 0.02744 | 0.027768 | 0.02662 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
