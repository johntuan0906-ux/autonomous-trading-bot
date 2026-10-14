# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 16:17:34 · commit `c36bbf5`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `64328` · round `2` · nhịp tim cách đây 22.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 814 lệnh đóng, WR 57.49%, E(R) 0.0167, PnL -46.32$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 585 | 55.21 | 1.018 | 0.948 | 0.0048 | -72.41 |
| 14 ngày | 768 | 57.29 | 1.082 | 0.989 | 0.0209 | -19.85 |
| 30 ngày | 814 | 57.49 | 1.064 | 0.976 | 0.0167 | -46.32 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.018 < 1.2; PF($) cua so 7 ngay = 0.948 < 1.1; PF(R) cua so 14 ngay = 1.082 < 1.2; PF($) cua so 14 ngay = 0.989 < 1.1; PF(R) cua so 30 ngay = 1.064 < 1.2; PF($) cua so 30 ngay = 0.976 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 375 lần cập nhật trọng số · Hội đồng AI: **12 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (9)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 226244.0 | 0.0041822 | 0.004138 | 0.004292 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 147058.5 | 0.005172 | 0.00516 | 0.005087 | True | True | 0.853 |
| ACE/USDT:USDT | LONG | 3720.0 | 0.1966 | 0.193912 | 0.20332 | False | False | 0.149 |
| AIN/USDT:USDT | SHORT | 6596.0 | 0.04271 | 0.042379 | 0.040815 | True | True | 0.937 |
| AKE/USDT:USDT | LONG | 14581.0 | 0.0259948 | 0.025309 | 0.02771 | False | False | 0.242 |
| ALGO/USDT:USDT | SHORT | 5820.7 | 0.1198 | 0.121518 | 0.115505 | False | False | 0.233 |
| ATOM/USDT:USDT | SHORT | 249.5 | 1.824 | 1.8110199999999999 | 1.7739 | True | True | 1.148 |
| BAT/USDT:USDT | LONG | 696.55 | 0.19272 | 0.19291272 | 0.210665 | True | True | 0.578 |
| QNT/USDT:USDT | SHORT | 1.4 | 213.37 | 212.37330199999997 | 204.70349 | True | True | 0.788 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
