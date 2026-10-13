# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 20:11:24 · commit `8b2a35e`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `21952` · round `None` · nhịp tim cách đây 28.9s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 711 lệnh đóng, WR 57.1%, E(R) 0.0367, PnL 78.94$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 482 | 54.15 | 1.119 | 1.049 | 0.0318 | 52.85 |
| 14 ngày | 665 | 56.84 | 1.173 | 1.074 | 0.0429 | 105.41 |
| 30 ngày | 711 | 57.1 | 1.144 | 1.05 | 0.0367 | 78.94 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.119 < 1.2; PF($) cua so 7 ngay = 1.049 < 1.1; PF(R) cua so 14 ngay = 1.173 < 1.2; PF($) cua so 14 ngay = 1.074 < 1.1; PF(R) cua so 30 ngay = 1.144 < 1.2; PF($) cua so 30 ngay = 1.050 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 318 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (8)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 178571.0 | 0.005179 | 0.005235 | 0.005039 | False | False | 0.161 |
| AIN/USDT:USDT | SHORT | 7530.0 | 0.04264 | 0.04259736 | 0.04098 | True | True | 0.301 |
| ALT/USDT:USDT | SHORT | 66666.0 | 0.00808 | 0.00823 | 0.007705 | False | False | 0.067 |
| APT/USDT:USDT | SHORT | 726.2 | 0.8237 | 0.83747 | 0.789275 | False | False | 0.225 |
| AR/USDT:USDT | SHORT | 172.0 | 3.873 | 3.93112 | 3.7277 | False | False | 0.0 |
| ARB/USDT:USDT | SHORT | 4336.5 | 0.1844 | 0.186706 | 0.178635 | False | False | 0.0 |
| AXS/USDT:USDT | SHORT | 720.0 | 1.133 | 1.146886 | 1.098285 | False | False | 0.216 |
| BANK/USDT:USDT | SHORT | 15243.5 | 0.02744 | 0.02741256 | 0.02662 | True | True | 0.366 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
