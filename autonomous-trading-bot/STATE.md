# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 20:46:29 · commit `7e0d367`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `44348` · round `14` · nhịp tim cách đây 88.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3394.29 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 846 lệnh đóng, WR 58.39%, E(R) 0.0243, PnL 23.22$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 617 | 56.56 | 1.059 | 0.998 | 0.0158 | -2.87 |
| 14 ngày | 800 | 58.25 | 1.114 | 1.028 | 0.0287 | 49.7 |
| 30 ngày | 846 | 58.39 | 1.094 | 1.012 | 0.0243 | 23.22 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.059 < 1.2; PF($) cua so 7 ngay = 0.998 < 1.1; PF(R) cua so 14 ngay = 1.114 < 1.2; PF($) cua so 14 ngay = 1.028 < 1.1; PF(R) cua so 30 ngay = 1.094 < 1.2; PF($) cua so 30 ngay = 1.012 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 382 lần cập nhật trọng số · Hội đồng AI: **9 model**

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
| 1000PEPE/USDT:USDT | LONG | 160513.0 | 0.0041353 | 0.004073 | 0.00429 | False | False | 0.026 |
| ACE/USDT:USDT | LONG | 3111.0 | 0.1918 | 0.188586 | 0.199835 | False | False | 0.187 |
| AKE/USDT:USDT | LONG | 7911.0 | 0.025075 | 0.025159 | 0.026655 | True | True | 0.698 |
| APT/USDT:USDT | SHORT | 873.2 | 0.8029 | 0.814352 | 0.77427 | False | False | 0.017 |
| ARB/USDT:USDT | SHORT | 3946.3 | 0.1842 | 0.186734 | 0.177865 | False | False | 0.0 |
| AXS/USDT:USDT | SHORT | 764.0 | 1.097 | 1.11008 | 1.0643 | False | False | 0.0 |
| BANK/USDT:USDT | SHORT | 39062.0 | 0.02688 | 0.027136 | 0.02624 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
