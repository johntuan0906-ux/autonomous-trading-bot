# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/11/2026 13:36:24 · commit `948c43e`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `65600` · round `203` · nhịp tim cách đây 86.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3168.74 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 3039 lệnh đóng, WR 41.03%, E(R) 0.2315, PnL -1044.35$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 109 | 46.79 | 2.107 | 1.368 | 0.3491 | 58.83 |
| 14 ngày | 126 | 41.27 | 1.724 | 0.844 | 0.2744 | -44.13 |
| 30 ngày | 2237 | 35.14 | 2.113 | 0.706 | 0.3173 | -1003.68 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF($) cua so 14 ngay = 0.844 < 1.1; PF($) cua so 30 ngay = 0.706 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.4%` · trần tổng `1.6%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 768 lần cập nhật trọng số · Hội đồng AI: **5 model**

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
| 1000BONK/USDT:USDT | SHORT | 37037.0 | 0.002601 | 0.002709 | 0.002385 | False | False | 0.0 |
| 1000SHIB/USDT:USDT | SHORT | 23333.1 | 0.004295 | 0.0042907050000000006 | 0.004055 | False | False | 0.0 |
| ACE/USDT:USDT | SHORT | 1024.0 | 0.11 | 0.113906 | 0.102188 | False | False | 0.819 |
| AERO/USDT:USDT | SHORT | 119.1 | 0.5347 | 0.5341653 | 0.487696 | True | True | 1.762 |
| AVAX/USDT:USDT | SHORT | 31.0 | 8.099096774194 | 8.43571 | 7.37758 | False | False | 0.214 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
