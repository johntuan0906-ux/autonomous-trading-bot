# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 05:01:33 · commit `d9cce7d`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `66` · nhịp tim cách đây 42.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3371.11 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 882 lệnh đóng, WR 58.73%, E(R) 0.0225, PnL 16.52$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 653 | 57.12 | 1.051 | 0.994 | 0.0139 | -9.57 |
| 14 ngày | 836 | 58.61 | 1.103 | 1.022 | 0.0267 | 43.0 |
| 30 ngày | 882 | 58.73 | 1.085 | 1.008 | 0.0225 | 16.52 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.051 < 1.2; PF($) cua so 7 ngay = 0.994 < 1.1; PF(R) cua so 14 ngay = 1.103 < 1.2; PF($) cua so 14 ngay = 1.022 < 1.1; PF(R) cua so 30 ngay = 1.085 < 1.2; PF($) cua so 30 ngay = 1.008 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 396 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005052 | 0.0051 | 0.004932 | False | False | 0.146 |
| ACE/USDT:USDT | LONG | 2927.0 | 0.1861 | 0.182684 | 0.19464 | False | False | 0.088 |
| ADA/USDT:USDT | SHORT | 3974.0 | 0.2278 | 0.230316 | 0.22151 | False | False | 0.159 |
| AKE/USDT:USDT | LONG | 8164.5 | 0.0265464 | 0.0273568 | 0.028076 | True | True | 1.823 |
| ALGO/USDT:USDT | SHORT | 6476.6 | 0.11559 | 0.117134 | 0.11173 | False | False | 0.246 |
| ALT/USDT:USDT | SHORT | 75757.0 | 0.00799 | 0.008122 | 0.00766 | False | False | 0.227 |
| ARB/USDT:USDT | SHORT | 5035.2 | 0.1817 | 0.183686 | 0.176735 | False | False | 0.151 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
