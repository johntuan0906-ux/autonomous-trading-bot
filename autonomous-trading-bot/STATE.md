# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 03:17:12 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `119320` · round `214` · nhịp tim cách đây 17.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 448 lệnh đóng, WR 60.27%, E(R) 0.0267, PnL 100.59$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 310 | 57.42 | 1.116 | 1.158 | 0.0273 | 83.11 |
| 14 ngày | 417 | 59.71 | 1.097 | 1.1 | 0.0227 | 75.55 |
| 30 ngày | 448 | 60.27 | 1.112 | 1.118 | 0.0267 | 100.59 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.116 < 1.2; PF(R) cua so 14 ngay = 1.097 < 1.2; PF(R) cua so 30 ngay = 1.112 < 1.2
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 216 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| ADA/USDT:USDT | LONG | 3293.5 | 0.2526 | 0.2528526 | 0.256395 | True | True | 0.395 |
| AVAX/USDT:USDT | SHORT | 76.0 | 10.363986842105264 | 10.566858 | 10.255855 | False | False | 0.0 |
| BTC/USDT:USDT | LONG | 0.1092 | 83027.8 | 82936.291202 | 83256.571995 | False | False | 0.298 |
| DOGE/USDT:USDT | LONG | 30487.0 | 0.08613 | 0.085802 | 0.08695 | False | False | 0.244 |
| LINK/USDT:USDT | LONG | 119.57 | 13.118 | 13.03437 | 13.327075 | False | False | 0.179 |
| SOL/USDT:USDT | LONG | 27.45 | 110.41 | 110.045776 | 111.32056 | False | False | 0.082 |
| XRP/USDT:USDT | SHORT | 1440.0 | 1.3995 | 1.407094 | 1.393815 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
