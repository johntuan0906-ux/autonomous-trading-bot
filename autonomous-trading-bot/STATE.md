# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/10/2026 21:39:02 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `72448` · round `5` · nhịp tim cách đây 44.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 522 lệnh đóng, WR 56.7%, E(R) -0.0037, PnL -40.38$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 384 | 53.12 | 0.944 | 0.925 | -0.0142 | -57.86 |
| 14 ngày | 491 | 56.01 | 0.963 | 0.935 | -0.0091 | -65.43 |
| 30 ngày | 522 | 56.7 | 0.985 | 0.963 | -0.0037 | -40.38 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.944 < 1.2; PF($) cua so 7 ngay = 0.925 < 1.1; PF(R) cua so 14 ngay = 0.963 < 1.2; PF($) cua so 14 ngay = 0.935 < 1.1; PF(R) cua so 30 ngay = 0.985 < 1.2; PF($) cua so 30 ngay = 0.963 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 231 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000000MOG/USDT:USDT | LONG | 18726.5 | 0.1105 | 0.109966 | 0.111835 | False | False | 0.0 |
| 1000CAT/USDT:USDT | SHORT | 625000.0 | 0.002028 | 0.002044 | 0.001988 | False | False | 0.0 |
| 1000FLOKI/USDT:USDT | SHORT | 72463.0 | 0.02702 | 0.027158 | 0.026675 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 416666.0 | 0.005407 | 0.005431 | 0.005347 | False | False | 0.0 |
| 1INCH/USDT:USDT | SHORT | 17921.0 | 0.09729 | 0.097848 | 0.095895 | False | False | 0.0 |
| 1MBABYDOGE/USDT:USDT | LONG | 2272727.0 | 0.0003862 | 0.00038679999999999997 | 0.000391 | True | True | 0.773 |
| AAVE/USDT:USDT | SHORT | 7.8 | 167.62 | 168.894176 | 164.43456 | False | False | 0.173 |
| ACT/USDT:USDT | LONG | 44247.0 | 0.01109 | 0.010864 | 0.011655 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
