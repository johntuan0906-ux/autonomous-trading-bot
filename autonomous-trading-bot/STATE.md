# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 05:31:34 · commit `93279d9`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `73` · nhịp tim cách đây 116.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3373.68 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 883 lệnh đóng, WR 58.78%, E(R) 0.0242, PnL 31.39$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 654 | 57.19 | 1.059 | 1.003 | 0.0162 | 5.3 |
| 14 ngày | 837 | 58.66 | 1.11 | 1.03 | 0.0285 | 57.87 |
| 30 ngày | 883 | 58.78 | 1.092 | 1.015 | 0.0242 | 31.39 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.059 < 1.2; PF($) cua so 7 ngay = 1.003 < 1.1; PF(R) cua so 14 ngay = 1.110 < 1.2; PF($) cua so 14 ngay = 1.030 < 1.1; PF(R) cua so 30 ngay = 1.092 < 1.2; PF($) cua so 30 ngay = 1.015 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 397 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005052 | 0.0051 | 0.004932 | False | False | 0.146 |
| ACE/USDT:USDT | LONG | 2927.0 | 0.1861 | 0.182684 | 0.19464 | False | False | 0.088 |
| ADA/USDT:USDT | SHORT | 3974.0 | 0.2278 | 0.230316 | 0.22151 | False | False | 0.159 |
| ALGO/USDT:USDT | SHORT | 3238.3 | 0.11559 | 0.11547441 | 0.11173 | True | True | 0.395 |
| ALT/USDT:USDT | SHORT | 76923.0 | 0.00799 | 0.00812 | 0.007665 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 6024.0 | 0.1431 | 0.14476 | 0.13895 | False | False | 0.0 |
| APT/USDT:USDT | SHORT | 907.6 | 0.8124 | 0.823418 | 0.784855 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
