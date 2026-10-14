# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 14/10/2026 11:12:25 · commit `699a0f5`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `52440` · round `148` · nhịp tim cách đây 110.1s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3370.9 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 785 lệnh đóng, WR 57.07%, E(R) 0.0186, PnL -35.97$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 556 | 54.5 | 1.025 | 0.953 | 0.0069 | -62.06 |
| 14 ngày | 739 | 56.83 | 1.091 | 0.994 | 0.0231 | -9.49 |
| 30 ngày | 785 | 57.07 | 1.071 | 0.98 | 0.0186 | -35.97 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.025 < 1.2; PF($) cua so 7 ngay = 0.953 < 1.1; PF(R) cua so 14 ngay = 1.091 < 1.2; PF($) cua so 14 ngay = 0.994 < 1.1; PF(R) cua so 30 ngay = 1.071 < 1.2; PF($) cua so 30 ngay = 0.980 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 362 lần cập nhật trọng số · Hội đồng AI: **14 model**

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
| 1000SHIB/USDT:USDT | SHORT | 333333.0 | 0.005189 | 0.005219 | 0.005114 | False | False | 0.2 |
| ACE/USDT:USDT | LONG | 3201.0 | 0.1983 | 0.195176 | 0.20611 | False | False | 0.0 |
| ADA/USDT:USDT | SHORT | 2310.5 | 0.2376 | 0.237282 | 0.23219 | True | True | 0.647 |
| AKE/USDT:USDT | SHORT | 15870.0 | 0.0251139 | 0.025744 | 0.023539 | False | False | 0.239 |
| ALGO/USDT:USDT | SHORT | 3875.95 | 0.12006 | 0.11993994 | 0.116835 | True | True | 0.341 |
| APE/USDT:USDT | SHORT | 6127.0 | 0.153 | 0.154632 | 0.14892 | False | False | 0.245 |
| APR/USDT:USDT | SHORT | 3937.0 | 0.05329 | 0.05323671 | 0.050115 | True | True | 0.465 |
| ARB/USDT:USDT | LONG | 4314.0 | 0.1921 | 0.189782 | 0.197895 | False | False | 0.0 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
