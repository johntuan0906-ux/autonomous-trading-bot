# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 11/11/2026 08:23:40 · commit `12edbc8`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `112020` · round `483` · nhịp tim cách đây 17.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3180.18 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3027 lệnh đóng, WR 41.06%, E(R) 0.2333, PnL -1032.9$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 102 | 46.08 | 2.073 | 1.113 | 0.3462 | 20.61 |
| 14 ngày | 118 | 42.37 | 1.834 | 0.868 | 0.3067 | -36.81 |
| 30 ngày | 2472 | 37.66 | 2.015 | 0.742 | 0.2862 | -1041.31 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay = 0.868 < 1.1; PF($) cua so 30 ngay = 0.742 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 767 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| 1000BONK/USDT:USDT | LONG | 35087.0 | 0.002827 | 0.002713 | 0.003055 | False | False | 0.009 |
| 1000PEPE/USDT:USDT | LONG | 13059.0 | 0.0053273 | 0.005021 | 0.005939 | False | False | 0.341 |
| ACE/USDT:USDT | LONG | 1058.0 | 0.1183 | 0.113834 | 0.125732 | False | False | 0.045 |
| AVAX/USDT:USDT | LONG | 6.0 | 8.726 | 8.089772 | 9.998456 | False | False | 0.047 |
| BNB/USDT:USDT | SHORT | 0.252 | 684.99 | 684.30501 | 663.189204 | True | True | 1.285 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
