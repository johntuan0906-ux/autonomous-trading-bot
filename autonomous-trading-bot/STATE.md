# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 11:42:25 · commit `5505bf5`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `156` · nhịp tim cách đây 14.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 787 lệnh đóng, WR 57.18%, E(R) 0.0188, PnL -34.29$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 558 | 54.66 | 1.026 | 0.954 | 0.0072 | -60.38 |
| 14 ngày | 741 | 56.95 | 1.092 | 0.995 | 0.0233 | -7.81 |
| 30 ngày | 787 | 57.18 | 1.072 | 0.981 | 0.0188 | -34.29 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.026 < 1.2; PF($) cua so 7 ngay = 0.954 < 1.1; PF(R) cua so 14 ngay = 1.092 < 1.2; PF($) cua so 14 ngay = 0.995 < 1.1; PF(R) cua so 30 ngay = 1.072 < 1.2; PF($) cua so 30 ngay = 0.981 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 364 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.2 |
| ACE/USDT:USDT | LONG | 3201.0 | 0.1983 | 0.195176 | 0.20611 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 4170.0 | 0.237 | 0.239398 | 0.231005 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| APE/USDT:USDT | SHORT | 6127.0 | 0.153 | 0.154632 | 0.14892 | False | False | 0.245 |
| ARB/USDT:USDT | LONG | 4314.0 | 0.1921 | 0.189782 | 0.197895 | False | False | 0.043 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
