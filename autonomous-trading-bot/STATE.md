# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 02:17:12 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `119320` · round `125` · nhịp tim cách đây 18.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4271.43 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 446 lệnh đóng, WR 60.09%, E(R) 0.0242, PnL 88.83$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 308 | 57.14 | 1.1 | 1.136 | 0.0236 | 71.35 |
| 14 ngày | 415 | 59.52 | 1.085 | 1.084 | 0.0199 | 63.78 |
| 30 ngày | 446 | 60.09 | 1.101 | 1.104 | 0.0242 | 88.83 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.100 < 1.2; PF(R) cua so 14 ngay = 1.085 < 1.2; PF($) cua so 14 ngay = 1.084 < 1.1; PF(R) cua so 30 ngay = 1.101 < 1.2
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 214 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| AVAX/USDT:USDT | SHORT | 76.0 | 10.363986842105264 | 10.566858 | 10.255855 | False | False | 0.0 |
| BTC/USDT:USDT | LONG | 0.1081 | 82974.0 | 82881.562264 | 83205.09434 | False | False | 0.016 |
| DOGE/USDT:USDT | LONG | 30487.0 | 0.08613 | 0.085802 | 0.08695 | False | False | 0.0 |
| LINK/USDT:USDT | LONG | 119.57 | 13.118 | 13.03437 | 13.327075 | False | False | 0.179 |
| SOL/USDT:USDT | LONG | 14.385 | 110.08 | 110.19008 | 110.94883 | True | True | 0.777 |
| XRP/USDT:USDT | SHORT | 1440.0 | 1.3995 | 1.407094 | 1.393815 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
