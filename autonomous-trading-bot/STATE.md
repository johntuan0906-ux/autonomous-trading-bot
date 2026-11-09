# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/11/2026 18:16:35 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `77604` · round `123` · nhịp tim cách đây 122.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3193.08 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3015 lệnh đóng, WR 41.03%, E(R) 0.2336, PnL -1039.88$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 93 | 45.16 | 2.052 | 1.053 | 0.3574 | 10.26 |
| 14 ngày | 108 | 40.74 | 1.765 | 0.762 | 0.2991 | -69.02 |
| 30 ngày | 2572 | 37.71 | 1.957 | 0.742 | 0.2721 | -1136.33 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 1.053 < 1.1; PF($) cua so 14 ngay = 0.762 < 1.1; PF($) cua so 30 ngay = 0.742 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 765 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (13)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 41666.0 | 0.002677 | 0.002773 | 0.002485 | False | False | 0.0 |
| 1000PEPE/USDT:USDT | LONG | 12106.0 | 0.0051324 | 0.004802 | 0.005792 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 734.0 | 0.1749 | 0.180348 | 0.164004 | False | False | 0.0 |
| ARB/USDT:USDT | LONG | 448.3 | 0.1715 | 0.162578 | 0.189344 | False | False | 0.729 |
| ASTER/USDT:USDT | SHORT | 148.0 | 0.6437 | 0.67064 | 0.58982 | False | False | 0.601 |
| CYBER/USDT:USDT | SHORT | 199.5 | 0.269 | 0.289046 | 0.228908 | False | False | 0.599 |
| DOT/USDT:USDT | SHORT | 117.3 | 0.8721 | 0.906186 | 0.803928 | False | False | 0.619 |
| ETH/USDT:USDT | SHORT | 0.049 | 2152.88 | 2233.168052 | 1992.303896 | False | False | 0.814 |
| GALA/USDT:USDT | SHORT | 66666.0 | 0.001523 | 0.001583 | 0.001403 | False | False | 0.8 |
| GTC/USDT:USDT | LONG | 216.8 | 0.185 | 0.166556 | 0.221888 | False | False | 0.271 |
| IO/USDT:USDT | SHORT | 830.2 | 0.1142 | 0.119018 | 0.104564 | False | False | 0.851 |
| LSK/USDT:USDT | SHORT | 479.0 | 0.1699 | 0.17824 | 0.15322 | False | False | 0.48 |
| QNT/USDT:USDT | LONG | 0.3 | 198.3 | 188.030586 | 218.838828 | False | False | 0.35 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
