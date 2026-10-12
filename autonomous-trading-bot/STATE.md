# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 06:51:33 · commit `00ccb35`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `95` · nhịp tim cách đây 105.3s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3682.07 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 636 lệnh đóng, WR 56.6%, E(R) 0.0293, PnL 61.89$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 407 | 52.83 | 1.072 | 1.04 | 0.0193 | 35.8 |
| 14 ngày | 605 | 56.03 | 1.106 | 1.028 | 0.0266 | 36.84 |
| 30 ngày | 636 | 56.6 | 1.115 | 1.044 | 0.0293 | 61.89 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.072 < 1.2; PF($) cua so 7 ngay = 1.040 < 1.1; PF(R) cua so 14 ngay = 1.106 < 1.2; PF($) cua so 14 ngay = 1.028 < 1.1; PF(R) cua so 30 ngay = 1.115 < 1.2; PF($) cua so 30 ngay = 1.044 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 281 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (10)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ACE/USDT:USDT | SHORT | 3498.0 | 0.1788 | 0.181658 | 0.171655 | False | False | 0.035 |
| AERO/USDT:USDT | SHORT | 447.6 | 0.8941 | 0.881985 | 0.866175 | True | True | 1.585 |
| AIN/USDT:USDT | LONG | 10482.0 | 0.04624 | 0.045286 | 0.048625 | False | False | 0.231 |
| AIOT/USDT:USDT | LONG | 8025.0 | 0.0551 | 0.053854 | 0.058215 | False | False | 0.241 |
| ALGO/USDT:USDT | SHORT | 5213.7 | 0.11885 | 0.120768 | 0.114055 | False | False | 0.021 |
| ALT/USDT:USDT | SHORT | 28409.0 | 0.00788 | 0.00787212 | 0.00744 | True | True | 0.455 |
| APE/USDT:USDT | SHORT | 2189.0 | 0.1484 | 0.1482516 | 0.14269 | True | True | 0.35 |
| APT/USDT:USDT | SHORT | 372.2 | 0.8041 | 0.802816 | 0.77052 | True | True | 0.596 |
| AR/USDT:USDT | SHORT | 64.25 | 3.789 | 3.783905 | 3.594475 | True | True | 0.565 |
| ARB/USDT:USDT | SHORT | 1773.0 | 0.1816 | 0.1814184 | 0.17455 | True | True | 0.532 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
