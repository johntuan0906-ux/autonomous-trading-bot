# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 23:19:42 · commit `385afeb`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `90444` · round `36` · nhịp tim cách đây 62.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3488.94 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 736 lệnh đóng, WR 56.93%, E(R) 0.0287, PnL 29.56$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 507 | 54.04 | 1.076 | 1.003 | 0.0205 | 3.47 |
| 14 ngày | 690 | 56.67 | 1.136 | 1.037 | 0.0342 | 56.03 |
| 30 ngày | 736 | 56.93 | 1.111 | 1.018 | 0.0287 | 29.56 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.076 < 1.2; PF($) cua so 7 ngay = 1.003 < 1.1; PF(R) cua so 14 ngay = 1.136 < 1.2; PF($) cua so 14 ngay = 1.037 < 1.1; PF(R) cua so 30 ngay = 1.111 < 1.2; PF($) cua so 30 ngay = 1.018 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 334 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| 1000SHIB/USDT:USDT | SHORT | 172413.0 | 0.005174 | 0.005232 | 0.005029 | False | False | 0.0 |
| AERO/USDT:USDT | SHORT | 396.35 | 0.896 | 0.8948069999999999 | 0.864465 | True | True | 0.674 |
| AIOT/USDT:USDT | LONG | 6587.0 | 0.0558 | 0.054282 | 0.059595 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 2365.15 | 0.1201 | 0.11945700000000001 | 0.114815 | True | True | 0.804 |
| ALT/USDT:USDT | SHORT | 55555.0 | 0.00811 | 0.00829 | 0.00766 | False | False | 0.056 |
| APR/USDT:USDT | SHORT | 4821.0 | 0.0526 | 0.054674 | 0.047415 | False | False | 0.154 |
| APT/USDT:USDT | SHORT | 675.1 | 0.8217 | 0.836512 | 0.78467 | False | False | 0.29 |
| QNT/USDT:USDT | SHORT | 0.85 | 209.21 | 206.235798 | 194.63101 | True | True | 1.01 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
