# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 09:39:17 · commit `dac5dd8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `70904` · round `235` · nhịp tim cách đây 6.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 345 lệnh đóng, WR 64.93%, E(R) 0.0818, PnL 200.68$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 260 | 65.0 | 1.572 | 1.47 | 0.105 | 214.76 |
| 14 ngày | 317 | 64.35 | 1.365 | 1.249 | 0.0758 | 158.78 |
| 30 ngày | 345 | 64.93 | 1.386 | 1.283 | 0.0818 | 200.68 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 158 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 100 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 3538.0 | 0.2321 | 0.234926 | 0.225035 | False | False | 0.212 |
| AVAX/USDT:USDT | SHORT | 79.0 | 10.21 | 10.335834 | 9.895415 | False | False | 0.167 |
| BTC/USDT:USDT | SHORT | 0.0381 | 81956.1 | 82218.295358 | 81300.611605 | False | False | 0.035 |
| DOGE/USDT:USDT | SHORT | 7987.0 | 0.08457 | 0.08448543 | 0.083005 | True | True | 0.351 |
| LINK/USDT:USDT | SHORT | 37.225 | 12.796 | 12.783204 | 12.460235 | True | True | 0.521 |
| SOL/USDT:USDT | SHORT | 5.77 | 109.32 | 111.05275 | 104.988125 | False | False | 0.162 |
| XRP/USDT:USDT | SHORT | 527.2 | 1.3879 | 1.3865120999999998 | 1.36419 | True | True | 0.411 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
