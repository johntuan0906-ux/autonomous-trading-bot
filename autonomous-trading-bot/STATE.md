# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 07:42:23 · commit `ccd9a99`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `97` · nhịp tim cách đây 62.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 770 lệnh đóng, WR 56.36%, E(R) 0.0156, PnL -62.01$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 541 | 53.42 | 1.008 | 0.933 | 0.0023 | -88.1 |
| 14 ngày | 724 | 56.08 | 1.077 | 0.978 | 0.02 | -35.53 |
| 30 ngày | 770 | 56.36 | 1.059 | 0.966 | 0.0156 | -62.01 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.008 < 1.2; PF($) cua so 7 ngay = 0.933 < 1.1; PF(R) cua so 14 ngay = 1.077 < 1.2; PF($) cua so 14 ngay = 0.978 < 1.1; PF(R) cua so 30 ngay = 1.059 < 1.2; PF($) cua so 30 ngay = 0.966 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 347 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| 1000PEPE/USDT:USDT | LONG | 78247.0 | 0.0042109 | 0.004220649999999999 | 0.004371 | True | True | 0.653 |
| ACE/USDT:USDT | LONG | 1414.5 | 0.1955 | 0.1956955 | 0.204335 | True | True | 0.396 |
| AERO/USDT:USDT | SHORT | 972.5 | 0.9 | 0.910282 | 0.874295 | False | False | 0.146 |
| AIOT/USDT:USDT | LONG | 12787.0 | 0.0549 | 0.054118 | 0.056855 | False | False | 0.128 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.206 |
| ALT/USDT:USDT | LONG | 79365.0 | 0.00834 | 0.008214 | 0.008655 | False | False | 0.238 |
| APR/USDT:USDT | SHORT | 7874.0 | 0.05329 | 0.05456 | 0.050115 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
