# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 17:20:24 · commit `fc73d2e`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `26956` · round `15` · nhịp tim cách đây 41.0s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3390.46 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 824 lệnh đóng, WR 57.89%, E(R) 0.0193, PnL -22.62$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 595 | 55.8 | 1.032 | 0.966 | 0.0087 | -48.71 |
| 14 ngày | 778 | 57.71 | 1.093 | 1.002 | 0.0237 | 3.86 |
| 30 ngày | 824 | 57.89 | 1.074 | 0.988 | 0.0193 | -22.62 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.032 < 1.2; PF($) cua so 7 ngay = 0.966 < 1.1; PF(R) cua so 14 ngay = 1.093 < 1.2; PF($) cua so 14 ngay = 1.002 < 1.1; PF(R) cua so 30 ngay = 1.074 < 1.2; PF($) cua so 30 ngay = 0.988 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 376 lần cập nhật trọng số · Hội đồng AI: **11 model**

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
| 1000PEPE/USDT:USDT | LONG | 226244.0 | 0.0041822 | 0.004138 | 0.004292 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 13404.0 | 0.025596 | 0.02485 | 0.027461 | False | False | 0.0 |
| APE/USDT:USDT | SHORT | 6242.0 | 0.148 | 0.149602 | 0.143995 | False | False | 0.062 |
| APT/USDT:USDT | SHORT | 992.8 | 0.8133 | 0.823372 | 0.78812 | False | False | 0.0 |
| AR/USDT:USDT | SHORT | 181.2 | 3.887 | 3.942172 | 3.74907 | False | False | 0.0 |
| ATOM/USDT:USDT | SHORT | 249.5 | 1.824 | 1.8010199999999998 | 1.7739 | True | True | 1.647 |
| QNT/USDT:USDT | SHORT | 1.4 | 213.37 | 211.073302 | 204.70349 | True | True | 1.163 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
