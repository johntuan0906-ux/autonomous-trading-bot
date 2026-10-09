# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/10/2026 16:35:49 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `105092` · round `1` · nhịp tim cách đây 3.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 4355.38 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 387 lệnh đóng, WR 60.98%, E(R) 0.0486, PnL 122.62$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 293 | 58.7 | 1.23 | 1.171 | 0.0472 | 96.36 |
| 14 ngày | 356 | 60.39 | 1.214 | 1.135 | 0.0457 | 97.58 |
| 30 ngày | 387 | 60.98 | 1.219 | 1.15 | 0.0486 | 122.62 |

## Cổng sang LIVE

- `live_ready.py`: **HOAN THANH**
- `live_guard.py`: OK
- Tự động sang LIVE: **BẬT** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 172 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (5)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| AVAX/USDT:USDT | SHORT | 76.0 | 10.391 | 10.522352 | 10.06262 | False | False | 0.0 |
| BTC/USDT:USDT | SHORT | 0.0486 | 82608.7 | 82814.424098 | 82094.389755 | False | False | 0.0 |
| DOGE/USDT:USDT | SHORT | 23474.0 | 0.08501 | 0.085436 | 0.083945 | False | False | 0.0 |
| SOL/USDT:USDT | SHORT | 14.22 | 110.5 | 111.202766 | 108.743085 | False | False | 0.0 |
| XRP/USDT:USDT | SHORT | 1440.0 | 1.3996 | 1.406544 | 1.38224 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
