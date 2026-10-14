# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 03:31:32 · commit `5ea3f7f`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `44` · nhịp tim cách đây 27.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 876 lệnh đóng, WR 58.68%, E(R) 0.0256, PnL 41.7$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 647 | 57.03 | 1.066 | 1.01 | 0.018 | 15.61 |
| 14 ngày | 830 | 58.55 | 1.117 | 1.036 | 0.0299 | 68.18 |
| 30 ngày | 876 | 58.68 | 1.098 | 1.02 | 0.0256 | 41.7 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.066 < 1.2; PF($) cua so 7 ngay = 1.010 < 1.1; PF(R) cua so 14 ngay = 1.117 < 1.2; PF($) cua so 14 ngay = 1.036 < 1.1; PF(R) cua so 30 ngay = 1.098 < 1.2; PF($) cua so 30 ngay = 1.020 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 391 lần cập nhật trọng số · Hội đồng AI: **8 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (7)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005052 | 0.0051 | 0.004932 | False | False | 0.0 |
| ACE/USDT:USDT | LONG | 2927.0 | 0.1861 | 0.182684 | 0.19464 | False | False | 0.088 |
| ADA/USDT:USDT | SHORT | 3974.0 | 0.2278 | 0.230316 | 0.22151 | False | False | 0.04 |
| AERO/USDT:USDT | SHORT | 784.4 | 0.8813 | 0.894048 | 0.84943 | False | False | 0.204 |
| AIN/USDT:USDT | SHORT | 15673.0 | 0.04048 | 0.041118 | 0.038885 | False | False | 0.094 |
| AIOT/USDT:USDT | SHORT | 10964.0 | 0.0495 | 0.050412 | 0.04722 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 7961.5 | 0.025881 | 0.026780400000000003 | 0.027451 | True | True | 1.932 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
