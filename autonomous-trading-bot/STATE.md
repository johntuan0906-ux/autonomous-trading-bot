# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 08:21:34 · commit `03670aa`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `117` · nhịp tim cách đây 38.2s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 651 lệnh đóng, WR 57.3%, E(R) 0.0376, PnL 120.52$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 422 | 54.03 | 1.123 | 1.103 | 0.0325 | 94.43 |
| 14 ngày | 620 | 56.77 | 1.142 | 1.072 | 0.0355 | 95.48 |
| 30 ngày | 651 | 57.3 | 1.149 | 1.084 | 0.0376 | 120.52 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.123 < 1.2; PF(R) cua so 14 ngay = 1.142 < 1.2; PF($) cua so 14 ngay = 1.072 < 1.1; PF(R) cua so 30 ngay = 1.149 < 1.2; PF($) cua so 30 ngay = 1.084 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 296 lần cập nhật trọng số · Hội đồng AI: **15 model**

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
| AIOT/USDT:USDT | LONG | 4012.5 | 0.0551 | 0.055155100000000006 | 0.058215 | True | True | 0.401 |
| AKE/USDT:USDT | SHORT | 20661.0 | 0.023031 | 0.023515 | 0.021821 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 3474.0 | 0.1433 | 0.146178 | 0.136105 | False | False | 0.0 |
| ARB/USDT:USDT | SHORT | 2974.4 | 0.1778 | 0.181162 | 0.169395 | False | False | 0.0 |
| ATOM/USDT:USDT | SHORT | 335.61 | 1.783 | 1.812796 | 1.70851 | False | False | 0.0 |
| AVAX/USDT:USDT | SHORT | 55.0 | 10.033 | 10.212562 | 9.584095 | False | False | 0.0 |
| AXL/USDT:USDT | SHORT | 6067.9 | 0.0554 | 0.057048 | 0.05128 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
