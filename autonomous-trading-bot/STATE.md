# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 10:12:24 · commit `f577dee`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `133` · nhịp tim cách đây 153.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3393.65 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 781 lệnh đóng, WR 56.98%, E(R) 0.0193, PnL -31.11$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 552 | 54.35 | 1.029 | 0.956 | 0.0079 | -57.2 |
| 14 ngày | 735 | 56.73 | 1.094 | 0.997 | 0.0239 | -4.63 |
| 30 ngày | 781 | 56.98 | 1.074 | 0.983 | 0.0193 | -31.11 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.029 < 1.2; PF($) cua so 7 ngay = 0.956 < 1.1; PF(R) cua so 14 ngay = 1.094 < 1.2; PF($) cua so 14 ngay = 0.997 < 1.1; PF(R) cua so 30 ngay = 1.074 < 1.2; PF($) cua so 30 ngay = 0.983 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 358 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| 1000PEPE/USDT:USDT | LONG | 118203.0 | 0.0042123 | 0.0042165123 | 0.004317 | True | True | 0.423 |
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.2 |
| ACE/USDT:USDT | LONG | 3599.0 | 0.1959 | 0.193122 | 0.202845 | False | False | 0.0 |
| AIN/USDT:USDT | SHORT | 14492.0 | 0.04466 | 0.04535 | 0.042935 | False | False | 0.246 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| APR/USDT:USDT | SHORT | 3937.0 | 0.05329 | 0.05323671 | 0.050115 | True | True | 0.307 |
| ATOM/USDT:USDT | SHORT | 207.655 | 1.848 | 1.828039 | 1.787805 | True | True | 1.329 |
| BTR/USDT:USDT | SHORT | 21459.0 | 0.04911 | 0.049576 | 0.047945 | False | False | 0.129 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
