# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 15:08:44 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `59544` · round `8` · nhịp tim cách đây 191.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4124.94 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 485 lệnh đóng, WR 58.97%, E(R) 0.0137, PnL 45.62$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 347 | 55.91 | 1.037 | 1.043 | 0.0091 | 28.14 |
| 14 ngày | 454 | 58.37 | 1.038 | 1.023 | 0.0091 | 20.57 |
| 30 ngày | 485 | 58.97 | 1.056 | 1.047 | 0.0137 | 45.62 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.037 < 1.2; PF($) cua so 7 ngay = 1.043 < 1.1; PF(R) cua so 14 ngay = 1.038 < 1.2; PF($) cua so 14 ngay = 1.023 < 1.1; PF(R) cua so 30 ngay = 1.056 < 1.2; PF($) cua so 30 ngay = 1.047 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 226 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000CAT/USDT:USDT | SHORT | 714285.0 | 0.002035 | 0.002049 | 0.002 | False | False | 0.286 |
| 1000RATS/USDT:USDT | LONG | 38461.0 | 0.03673 | 0.03647 | 0.03738 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 454545.0 | 0.005401 | 0.005423 | 0.005346 | False | False | 0.182 |
| 4/USDT:USDT | SHORT | 74626.0 | 0.01655 | 0.016684 | 0.016215 | False | False | 0.149 |
| AAVE/USDT:USDT | SHORT | 3.9 | 167.47 | 167.30253 | 164.304115 | True | True | 0.442 |
| ACU/USDT:USDT | SHORT | 8051.0 | 0.10217 | 0.103412 | 0.099065 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
