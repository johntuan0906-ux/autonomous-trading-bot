# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 13/10/2026 22:49:41 · commit `274f156`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `90444` · round `29` · nhịp tim cách đây 63.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 731 lệnh đóng, WR 56.77%, E(R) 0.0268, PnL 14.27$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 502 | 53.78 | 1.065 | 0.99 | 0.0177 | -11.82 |
| 14 ngày | 685 | 56.5 | 1.127 | 1.027 | 0.0323 | 40.75 |
| 30 ngày | 731 | 56.77 | 1.103 | 1.008 | 0.0268 | 14.27 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.065 < 1.2; PF($) cua so 7 ngay = 0.990 < 1.1; PF(R) cua so 14 ngay = 1.127 < 1.2; PF($) cua so 14 ngay = 1.027 < 1.1; PF(R) cua so 30 ngay = 1.103 < 1.2; PF($) cua so 30 ngay = 1.008 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 329 lần cập nhật trọng số · Hội đồng AI: **15 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (10)

| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |
|---|---|---|---|---|---|---|---|---|
| ACE/USDT:USDT | LONG | 2994.0 | 0.1932 | 0.18986 | 0.20155 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 1489.5 | 0.235 | 0.23476499999999997 | 0.22661 | True | True | 0.387 |
| AERO/USDT:USDT | SHORT | 792.7 | 0.896 | 0.908614 | 0.864465 | False | False | 0.0 |
| ALGO/USDT:USDT | SHORT | 2365.15 | 0.1201 | 0.11970700000000001 | 0.114815 | True | True | 0.686 |
| APE/USDT:USDT | SHORT | 2291.0 | 0.1491 | 0.148391 | 0.143645 | True | True | 0.825 |
| APR/USDT:USDT | SHORT | 4821.0 | 0.0526 | 0.054674 | 0.047415 | False | False | 0.154 |
| APT/USDT:USDT | SHORT | 675.1 | 0.8217 | 0.836512 | 0.78467 | False | False | 0.155 |
| AR/USDT:USDT | SHORT | 73.75 | 3.945 | 3.925896 | 3.77552 | True | True | 0.782 |
| ATOM/USDT:USDT | SHORT | 183.04 | 1.821 | 1.8126579999999999 | 1.75271 | True | True | 0.805 |
| QNT/USDT:USDT | SHORT | 0.85 | 209.21 | 208.125798 | 194.63101 | True | True | 0.686 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
