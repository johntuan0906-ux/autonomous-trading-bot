# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 04:51:31 · commit `1bcb2dd`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `91556` · round `66` · nhịp tim cách đây 81.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3681.38 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 617 lệnh đóng, WR 55.43%, E(R) 0.0118, PnL -51.67$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 388 | 50.77 | 0.968 | 0.911 | -0.009 | -77.76 |
| 14 ngày | 586 | 54.78 | 1.032 | 0.941 | 0.0081 | -76.72 |
| 30 ngày | 617 | 55.43 | 1.045 | 0.963 | 0.0118 | -51.67 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 0.968 < 1.2; PF($) cua so 7 ngay = 0.911 < 1.1; PF(R) cua so 14 ngay = 1.032 < 1.2; PF($) cua so 14 ngay = 0.941 < 1.1; PF(R) cua so 30 ngay = 1.045 < 1.2; PF($) cua so 30 ngay = 0.963 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 263 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** ⬅ **hiện tại** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (12)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| 1000SHIB/USDT:USDT | SHORT | 119047.5 | 0.005336 | 0.005261 | 0.005231 | True | True | 2.286 |
| ACE/USDT:USDT | SHORT | 1561.5 | 0.183 | 0.18100100000000002 | 0.174995 | True | True | 1.124 |
| ADA/USDT:USDT | SHORT | 2378.5 | 0.2426 | 0.238851 | 0.237345 | True | True | 2.284 |
| AIOT/USDT:USDT | LONG | 10869.0 | 0.0545 | 0.05358 | 0.0568 | False | False | 0.217 |
| AKE/USDT:USDT | SHORT | 10548.5 | 0.024146 | 0.0239848 | 0.022961 | True | True | 0.84 |
| APE/USDT:USDT | SHORT | 2815.0 | 0.152 | 0.149688 | 0.14756 | True | True | 1.802 |
| APR/USDT:USDT | SHORT | 3776.0 | 0.0731 | 0.07186200000000001 | 0.06979 | True | True | 1.435 |
| APT/USDT:USDT | SHORT | 541.45 | 0.8279 | 0.815817 | 0.804815 | True | True | 1.809 |
| AR/USDT:USDT | SHORT | 103.9 | 3.96 | 3.95604 | 3.83973 | True | True | 0.686 |
| ARB/USDT:USDT | SHORT | 2308.4 | 0.1866 | 0.184083 | 0.181185 | True | True | 1.662 |
| ASTER/USDT:USDT | SHORT | 1149.0 | 0.6995 | 0.6910749999999999 | 0.688625 | True | True | 2.437 |
| ATOM/USDT:USDT | SHORT | 463.73 | 1.817 | 1.838564 | 1.76309 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
