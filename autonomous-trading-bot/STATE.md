# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 05:21:32 · commit `0d84a91`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `73` · nhịp tim cách đây 107.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3652.08 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 627 lệnh đóng, WR 56.14%, E(R) 0.0256, PnL 36.42$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 398 | 52.01 | 1.049 | 1.012 | 0.0134 | 10.33 |
| 14 ngày | 596 | 55.54 | 1.09 | 1.009 | 0.0228 | 11.37 |
| 30 ngày | 627 | 56.14 | 1.1 | 1.026 | 0.0256 | 36.42 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.049 < 1.2; PF($) cua so 7 ngay = 1.012 < 1.1; PF(R) cua so 14 ngay = 1.090 < 1.2; PF($) cua so 14 ngay = 1.009 < 1.1; PF(R) cua so 30 ngay = 1.100 < 1.2; PF($) cua so 30 ngay = 1.026 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 272 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 114942.5 | 0.0040105 | 0.0040064895 | 0.003901 | True | True | 0.517 |
| AERO/USDT:USDT | SHORT | 895.2 | 0.8941 | 0.90527 | 0.866175 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 10548.5 | 0.024146 | 0.0239737 | 0.022961 | True | True | 0.864 |
| ALGO/USDT:USDT | LONG | 5668.9 | 0.12184 | 0.120076 | 0.12625 | False | False | 0.136 |
| ATOM/USDT:USDT | SHORT | 463.73 | 1.817 | 1.838564 | 1.76309 | False | False | 0.0 |
| AVAX/USDT:USDT | SHORT | 72.0 | 10.353 | 10.491136 | 10.00766 | False | False | 0.21 |
| AXS/USDT:USDT | SHORT | 472.0 | 1.195 | 1.1932939999999999 | 1.16853 | True | True | 0.661 |
| BANK/USDT:USDT | SHORT | 27777.0 | 0.02782 | 0.02818 | 0.02692 | False | False | 0.222 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
