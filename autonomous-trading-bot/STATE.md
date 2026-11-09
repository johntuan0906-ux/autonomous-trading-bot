# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 09/11/2026 14:46:26 · commit `?`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `77604` · round `74` · nhịp tim cách đây 58.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3014 lệnh đóng, WR 41.04%, E(R) 0.234, PnL -1035.85$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 92 | 45.65 | 2.119 | 1.076 | 0.3723 | 14.29 |
| 14 ngày | 107 | 41.12 | 1.808 | 0.773 | 0.3113 | -64.99 |
| 30 ngày | 2571 | 37.73 | 1.96 | 0.742 | 0.2726 | -1132.31 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 1.076 < 1.1; PF($) cua so 14 ngay = 0.773 < 1.1; PF($) cua so 30 ngay = 0.742 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 764 lần cập nhật trọng số · Hội đồng AI: **11 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (13)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000BONK/USDT:USDT | SHORT | 41666.0 | 0.002677 | 0.002773 | 0.002485 | False | False | 0.0 |
| 1000PEPE/USDT:USDT | LONG | 12106.0 | 0.0051324 | 0.004802 | 0.005792 | False | False | 0.0 |
| ARB/USDT:USDT | LONG | 448.3 | 0.1715 | 0.162578 | 0.189344 | False | False | 0.37 |
| ASTER/USDT:USDT | SHORT | 148.0 | 0.6437 | 0.67064 | 0.58982 | False | False | 0.65 |
| BR/USDT:USDT | SHORT | 237.0 | 0.4221 | 0.43893 | 0.38844 | False | False | 0.107 |
| CYBER/USDT:USDT | SHORT | 199.5 | 0.269 | 0.289046 | 0.228908 | False | False | 0.599 |
| DOT/USDT:USDT | SHORT | 117.3 | 0.8721 | 0.906186 | 0.803928 | False | False | 0.566 |
| ETH/USDT:USDT | SHORT | 0.049 | 2152.88 | 2233.168052 | 1992.303896 | False | False | 0.814 |
| GALA/USDT:USDT | SHORT | 66666.0 | 0.001523 | 0.001583 | 0.001403 | False | False | 0.7 |
| GTC/USDT:USDT | LONG | 216.8 | 0.185 | 0.166556 | 0.221888 | False | False | 0.271 |
| IO/USDT:USDT | SHORT | 830.2 | 0.1142 | 0.119018 | 0.104564 | False | False | 0.789 |
| LSK/USDT:USDT | SHORT | 479.0 | 0.1699 | 0.17824 | 0.15322 | False | False | 0.312 |
| QNT/USDT:USDT | LONG | 0.3 | 198.3 | 188.030586 | 218.838828 | False | False | 0.252 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
