# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 08:12:23 · commit `c6f753e`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `104` · nhịp tim cách đây 67.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3400.91 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 774 lệnh đóng, WR 56.59%, E(R) 0.0166, PnL -53.53$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 545 | 53.76 | 1.014 | 0.939 | 0.0038 | -79.62 |
| 14 ngày | 728 | 56.32 | 1.082 | 0.984 | 0.021 | -27.05 |
| 30 ngày | 774 | 56.59 | 1.063 | 0.971 | 0.0166 | -53.53 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.014 < 1.2; PF($) cua so 7 ngay = 0.939 < 1.1; PF(R) cua so 14 ngay = 1.082 < 1.2; PF($) cua so 14 ngay = 0.984 < 1.1; PF(R) cua so 30 ngay = 1.063 < 1.2; PF($) cua so 30 ngay = 0.971 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 351 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 2606.5 | 0.2378 | 0.2375622 | 0.233005 | True | True | 0.574 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| APR/USDT:USDT | SHORT | 7874.0 | 0.05329 | 0.05456 | 0.050115 | False | False | 0.0 |
| ASTER/USDT:USDT | SHORT | 986.5 | 0.7086 | 0.7058340000000001 | 0.69593 | True | True | 1.046 |
| ATOM/USDT:USDT | SHORT | 207.655 | 1.848 | 1.842039 | 1.787805 | True | True | 0.748 |
| AXS/USDT:USDT | SHORT | 540.0 | 1.144 | 1.142627 | 1.120865 | True | True | 0.648 |
| BR/USDT:USDT | SHORT | 921.5 | 0.42405 | 0.42362595 | 0.41049 | True | True | 0.343 |
| BTR/USDT:USDT | SHORT | 21459.0 | 0.04911 | 0.049576 | 0.047945 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
