# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 02:42:19 · commit `321b9d2`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `22` · nhịp tim cách đây 150.5s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3405.05 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 760 lệnh đóng, WR 56.32%, E(R) 0.02, PnL -30.27$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 531 | 53.3 | 1.03 | 0.955 | 0.0083 | -56.36 |
| 14 ngày | 714 | 56.02 | 1.097 | 0.998 | 0.0247 | -3.79 |
| 30 ngày | 760 | 56.32 | 1.076 | 0.983 | 0.02 | -30.27 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.030 < 1.2; PF($) cua so 7 ngay = 0.955 < 1.1; PF(R) cua so 14 ngay = 1.097 < 1.2; PF($) cua so 14 ngay = 0.998 < 1.1; PF(R) cua so 30 ngay = 1.076 < 1.2; PF($) cua so 30 ngay = 0.983 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 337 lần cập nhật trọng số · Hội đồng AI: **14 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (6)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000PEPE/USDT:USDT | LONG | 156494.0 | 0.0042109 | 0.004147 | 0.004371 | False | False | 0.236 |
| 1000SHIB/USDT:USDT | SHORT | 250000.0 | 0.005216 | 0.005256 | 0.005116 | False | False | 0.15 |
| AIN/USDT:USDT | SHORT | 7530.0 | 0.04427 | 0.045598 | 0.04095 | False | False | 0.0 |
| AIOT/USDT:USDT | LONG | 8278.0 | 0.0555 | 0.054292 | 0.05852 | False | False | 0.0 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.206 |
| APE/USDT:USDT | SHORT | 5714.0 | 0.1493 | 0.15105 | 0.144925 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
