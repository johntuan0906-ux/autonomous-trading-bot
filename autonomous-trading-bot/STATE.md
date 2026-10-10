# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 10/10/2026 08:17:48 · commit `?`
- **Chế độ**: **LIVE (TIỀN THẬT)** · `DRY_RUN=False` · `LIVE_CONFIRM=True`
- **Bot**: pid `42952` · round `462` · nhịp tim cách đây 9.4s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 22.0 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 435 lệnh đóng, WR 60.92%, E(R) 0.0395, PnL 122.45$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 297 | 58.25 | 1.208 | 1.215 | 0.046 | 104.97 |
| 14 ngày | 404 | 60.4 | 1.163 | 1.135 | 0.0363 | 97.4 |
| 30 ngày | 435 | 60.92 | 1.172 | 1.15 | 0.0395 | 122.45 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 14 ngay = 1.163 < 1.2; PF(R) cua so 30 ngay = 1.172 < 1.2
- `live_guard.py`: CHẶN — PF(R)=1.172 < 1.2 — heuristic chua co edge
- Tự động sang LIVE: **BẬT** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.5%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `2` · trần size `1000.0` USDT
- Learner: 208 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** ⬅ **hiện tại** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (3)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ADA/USDT:USDT | SHORT | 40.0 | 0.245 | 0.24773 | 0.238175 | False | False | 0.147 |
| AVAX/USDT:USDT | SHORT | 0.5 | 10.347 | 10.336653 | 10.118445 | True | True | 0.328 |
| SOL/USDT:USDT | SHORT | 0.18 | 109.33 | 109.917098 | 107.862255 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
