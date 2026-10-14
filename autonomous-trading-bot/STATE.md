# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 03:01:31 · commit `32841ba`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `89760` · round `36` · nhịp tim cách đây 127.6s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: 3403.64 USDT
- **Kill-switch**: bình thường

## Hiệu suất (journal: 875 lệnh đóng, WR 58.63%, E(R) 0.025, PnL 36.57$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 646 | 56.97 | 1.063 | 1.007 | 0.0172 | 10.48 |
| 14 ngày | 829 | 58.5 | 1.115 | 1.033 | 0.0294 | 63.05 |
| 30 ngày | 875 | 58.63 | 1.095 | 1.018 | 0.025 | 36.57 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.063 < 1.2; PF($) cua so 7 ngay = 1.007 < 1.1; PF(R) cua so 14 ngay = 1.115 < 1.2; PF($) cua so 14 ngay = 1.033 < 1.1; PF(R) cua so 30 ngay = 1.095 < 1.2; PF($) cua so 30 ngay = 1.018 < 1.1
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 391 lần cập nhật trọng số · Hội đồng AI: **8 model**

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
| 1000SHIB/USDT:USDT | SHORT | 208333.0 | 0.005052 | 0.0051 | 0.004932 | False | False | 0.0 |
| ACE/USDT:USDT | LONG | 2927.0 | 0.1861 | 0.182684 | 0.19464 | False | False | 0.088 |
| ADA/USDT:USDT | SHORT | 3974.0 | 0.2278 | 0.230316 | 0.22151 | False | False | 0.04 |
| AERO/USDT:USDT | SHORT | 784.4 | 0.8813 | 0.894048 | 0.84943 | False | False | 0.204 |
| AIOT/USDT:USDT | SHORT | 10964.0 | 0.0495 | 0.050412 | 0.04722 | False | False | 0.0 |
| AKE/USDT:USDT | LONG | 7961.5 | 0.025881 | 0.0264415 | 0.027451 | True | True | 1.393 |
| ALGO/USDT:USDT | SHORT | 2702.7 | 0.11684 | 0.115675 | 0.112215 | True | True | 1.13 |
| ARB/USDT:USDT | SHORT | 1840.9 | 0.1842 | 0.181958 | 0.17741 | True | True | 1.325 |

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
