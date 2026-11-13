# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/11/2026 23:06:31 · commit `28e544d`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `65600` · round `348` · nhịp tim cách đây 104.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3160.06 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3042 lệnh đóng, WR 41.03%, E(R) 0.2312, PnL -1052.18$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 110 | 47.27 | 2.159 | 1.505 | 0.3617 | 75.56 |
| 14 ngày | 129 | 41.09 | 1.688 | 0.826 | 0.2656 | -51.96 |
| 30 ngày | 2176 | 33.87 | 2.113 | 0.652 | 0.32 | -1142.99 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay = 0.826 < 1.1; PF($) cua so 30 ngay = 0.652 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 770 lần cập nhật trọng số · Hội đồng AI: **5 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (4)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | SHORT | 18050.0 | 0.0045624 | 0.004784 | 0.004118 | False | False | 0.474 |
| ACE/USDT:USDT | SHORT | 1024.0 | 0.11 | 0.113906 | 0.102188 | False | False | 0.819 |
| ADA/USDT:USDT | SHORT | 872.0 | 0.1716 | 0.176184 | 0.162432 | False | False | 0.48 |
| AERO/USDT:USDT | LONG | 119.1 | 0.4884821998321 | 0.461424 | 0.536052 | False | False | 0.137 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
