# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 08:42:23 · commit `ebb20dc`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `111` · nhịp tim cách đây 133.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3403.4 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 777 lệnh đóng, WR 56.76%, E(R) 0.0177, PnL -44.9$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 548 | 54.01 | 1.02 | 0.946 | 0.0054 | -70.99 |
| 14 ngày | 731 | 56.5 | 1.087 | 0.989 | 0.0221 | -18.42 |
| 30 ngày | 777 | 56.76 | 1.067 | 0.975 | 0.0177 | -44.9 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.020 < 1.2; PF($) cua so 7 ngay = 0.946 < 1.1; PF(R) cua so 14 ngay = 1.087 < 1.2; PF($) cua so 14 ngay = 0.989 < 1.1; PF(R) cua so 30 ngay = 1.067 < 1.2; PF($) cua so 30 ngay = 0.975 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 354 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 217864.0 | 0.0041889 | 0.004143 | 0.004304 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.2 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| APR/USDT:USDT | SHORT | 7874.0 | 0.05329 | 0.05456 | 0.050115 | False | False | 0.087 |
| ASTER/USDT:USDT | SHORT | 986.5 | 0.7086 | 0.7035339999999999 | 0.69593 | True | True | 1.5 |
| ATOM/USDT:USDT | SHORT | 207.655 | 1.848 | 1.834039 | 1.787805 | True | True | 1.08 |
| BTR/USDT:USDT | SHORT | 21459.0 | 0.04911 | 0.049576 | 0.047945 | False | False | 0.107 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
