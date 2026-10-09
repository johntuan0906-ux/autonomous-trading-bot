# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 12:12:55 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `48700` · round `128` · nhịp tim cách đây 24.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4430.54 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 364 lệnh đóng, WR 63.46%, E(R) 0.0672, PnL 173.71$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 279 | 63.08 | 1.443 | 1.375 | 0.0844 | 187.79 |
| 14 ngày | 335 | 62.69 | 1.274 | 1.183 | 0.0583 | 124.44 |
| 30 ngày | 364 | 63.46 | 1.311 | 1.231 | 0.0672 | 173.71 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT**

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 165 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| ADA/USDT:USDT | SHORT | 4878.0 | 0.2346 | 0.23665 | 0.229475 | False | False | 0.049 |
| AVAX/USDT:USDT | SHORT | 37.5 | 10.273 | 10.257385000000001 | 9.941075 | True | True | 0.618 |
| BTC/USDT:USDT | SHORT | 0.0427 | 82293.5 | 82527.563294 | 81708.341765 | False | False | 0.001 |
| DOGE/USDT:USDT | SHORT | 18656.0 | 0.08489 | 0.085426 | 0.08355 | False | False | 0.168 |
| LINK/USDT:USDT | SHORT | 76.61 | 12.803 | 12.933526 | 12.476685 | False | False | 0.0 |
| SOL/USDT:USDT | SHORT | 7.97 | 110.14 | 111.393438 | 107.006405 | False | False | 0.239 |
| XRP/USDT:USDT | SHORT | 1209.4 | 1.3941 | 1.402368 | 1.37343 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
