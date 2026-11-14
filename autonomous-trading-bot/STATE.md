# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/11/2026 19:36:47 · commit `395be61`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `65600` · round `665` · nhịp tim cách đây 29.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3185.85 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3043 lệnh đóng, WR 41.01%, E(R) 0.2308, PnL -1055.45$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 106 | 48.11 | 2.11 | 1.431 | 0.3578 | 60.49 |
| 14 ngày | 122 | 43.44 | 1.661 | 0.931 | 0.2475 | -18.34 |
| 30 ngày | 2125 | 33.04 | 2.1 | 0.576 | 0.3173 | -1336.52 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay = 0.931 < 1.1; PF($) cua so 30 ngay = 0.576 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 771 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| 1000BONK/USDT:USDT | SHORT | 29166.2 | 0.002687 | 0.0026843130000000002 | 0.002495 | False | False | 0.0 |
| 1000PEPE/USDT:USDT | SHORT | 12635.0 | 0.0045624 | 0.0045578376000000006 | 0.004118 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 35087.0 | 0.004161 | 0.004275 | 0.003933 | False | False | 0.061 |
| ACE/USDT:USDT | SHORT | 716.8 | 0.11 | 0.10989 | 0.102188 | True | True | 1.69 |
| AERO/USDT:USDT | SHORT | 205.4 | 0.4563 | 0.47577 | 0.41736 | False | False | 0.318 |
| CKB/USDT:USDT | SHORT | 111111.0 | 0.000904 | 0.00094 | 0.000832 | False | False | 0.556 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
