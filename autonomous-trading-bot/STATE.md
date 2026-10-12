# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 04:21:31 · commit `9b909a4`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `59` · nhịp tim cách đây 31.7s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3627.25 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 615 lệnh đóng, WR 55.28%, E(R) 0.0114, PnL -54.3$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 386 | 50.52 | 0.965 | 0.908 | -0.0097 | -80.39 |
| 14 ngày | 584 | 54.62 | 1.03 | 0.938 | 0.0077 | -79.35 |
| 30 ngày | 615 | 55.28 | 1.044 | 0.961 | 0.0114 | -54.3 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.965 < 1.2; PF($) cua so 7 ngay = 0.908 < 1.1; PF(R) cua so 14 ngay = 1.030 < 1.2; PF($) cua so 14 ngay = 0.938 < 1.1; PF(R) cua so 30 ngay = 1.044 < 1.2; PF($) cua so 30 ngay = 0.961 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 261 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 238095.0 | 0.005336 | 0.005378 | 0.005231 | False | False | 0.024 |
| ACE/USDT:USDT | SHORT | 1561.5 | 0.183 | 0.182817 | 0.174995 | True | True | 0.437 |
| ADA/USDT:USDT | SHORT | 2378.5 | 0.2426 | 0.2423574 | 0.237345 | True | True | 0.428 |
| AERO/USDT:USDT | SHORT | 882.9 | 0.8965 | 0.907826 | 0.868185 | False | False | 0.274 |
| AIOT/USDT:USDT | LONG | 10869.0 | 0.0545 | 0.05358 | 0.0568 | False | False | 0.217 |
| AKE/USDT:USDT | SHORT | 10548.5 | 0.024146 | 0.0240815 | 0.022961 | True | True | 0.636 |
| ALGO/USDT:USDT | LONG | 5868.5 | 0.12221 | 0.120506 | 0.12647 | False | False | 0.047 |
| APE/USDT:USDT | SHORT | 5630.0 | 0.152 | 0.153776 | 0.14756 | False | False | 0.225 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
