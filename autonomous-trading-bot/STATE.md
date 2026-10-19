# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 19/10/2026 17:00:06 · commit `d8722de`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `38284` · round `27` · nhịp tim cách đây 171.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3328.7 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 952 lệnh đóng, WR 58.3%, E(R) 0.0347, PnL 133.13$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 362 | 64.92 | 1.306 | 1.235 | 0.0826 | 226.41 |
| 14 ngày | 762 | 56.96 | 1.151 | 1.072 | 0.0411 | 133.36 |
| 30 ngày | 952 | 58.3 | 1.13 | 1.058 | 0.0347 | 133.13 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 14 ngay = 1.151 < 1.2; PF($) cua so 14 ngay = 1.072 < 1.1; PF(R) cua so 30 ngay = 1.130 < 1.2; PF($) cua so 30 ngay = 1.058 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `0.25%` · trần tổng `1.0%` · leverage `8` · MAX_POSITIONS `1` · trần size `1000.0` USDT
- Learner: 430 lần cập nhật trọng số · Hội đồng AI: **6 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (13)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 59808.0 | 0.0041158 | 0.004074 | 0.004221 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 1438.0 | 0.2205 | 0.222238 | 0.216155 | False | False | 0.288 |
| AIN/USDT:USDT | LONG | 1876.5 | 0.04107 | 0.041157 | 0.042735 | True | True | 0.631 |
| AIOT/USDT:USDT | LONG | 2042.0 | 0.0531 | 0.053394 | 0.05463 | True | True | 0.98 |
| APE/USDT:USDT | SHORT | 1586.0 | 0.1427 | 0.145934 | 0.140565 | False | False | 0.0 |
| ARB/USDT:USDT | LONG | 893.4 | 0.199 | 0.196202 | 0.205995 | False | False | 0.143 |
| AVAX/USDT:USDT | SHORT | 31.0 | 9.776 | 9.854864 | 9.57884 | False | False | 0.279 |
| AXL/USDT:USDT | LONG | 1155.3 | 0.0578 | 0.056298 | 0.060505 | False | False | 0.2 |
| AXS/USDT:USDT | SHORT | 93.0 | 1.007 | 1.005993 | 0.98939 | True | True | 0.426 |
| BNB/USDT:USDT | LONG | 1.21 | 727.33 | 724.749348 | 732.20663 | False | False | 0.0 |
| CKB/USDT:USDT | LONG | 125000.0 | 0.001499 | 0.00147 | 0.001533 | False | False | 0.0 |
| DASH/USDT:USDT | LONG | 2.8145 | 49.16 | 49.237959000000004 | 50.270205 | True | True | 0.676 |
| ENA/USDT:USDT | SHORT | 1247.0 | 0.1908 | 0.192804 | 0.18579 | False | False | 0.2 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
