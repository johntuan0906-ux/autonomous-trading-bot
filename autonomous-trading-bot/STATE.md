# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 10/11/2026 13:23:22 · commit `352dba2`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `112020` · round `202` · nhịp tim cách đây 109.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3165.15 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3026 lệnh đóng, WR 41.04%, E(R) 0.2332, PnL -1034.44$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 102 | 45.1 | 2.001 | 1.037 | 0.3327 | 7.12 |
| 14 ngày | 118 | 41.53 | 1.78 | 0.824 | 0.2943 | -51.29 |
| 30 ngày | 2562 | 37.86 | 1.97 | 0.75 | 0.2754 | -1085.24 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 7 ngay = 1.037 < 1.1; PF($) cua so 14 ngay = 0.824 < 1.1; PF($) cua so 30 ngay = 0.750 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 765 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| 1000BONK/USDT:USDT | LONG | 35087.0 | 0.002827 | 0.002713 | 0.003055 | False | False | 0.0 |
| 1000PEPE/USDT:USDT | LONG | 15589.7 | 0.0051276 | 0.0051327276 | 0.005488 | False | False | 0.0 |
| ACE/USDT:USDT | SHORT | 1346.0 | 0.1184 | 0.12137 | 0.11246 | False | False | 0.236 |
| AVAX/USDT:USDT | LONG | 6.0 | 8.726 | 8.089772 | 9.998456 | False | False | 0.047 |
| BNB/USDT:USDT | SHORT | 0.36 | 684.99 | 695.890398 | 663.189204 | False | False | 0.06 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
