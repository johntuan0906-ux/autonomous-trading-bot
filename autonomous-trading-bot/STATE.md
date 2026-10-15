# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)

> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:
> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.

- **Cập nhật**: 15/10/2026 19:52:10 · commit `112c600`
- **Chế độ**: TESTNET (demo) · `DRY_RUN=False` · `LIVE_CONFIRM=False`
- **Bot**: pid `45772` · round `171` · nhịp tim cách đây 10.8s (watchdog 360s) → ĐANG CHẠY
- **Ví demo**: ? USDT
- **Kill-switch**: ⚠️ TRIPPED — 6 consecutive losses (muc 12)

## Hiệu suất (journal: 925 lệnh đóng, WR 59.03%, E(R) 0.0432, PnL 197.8$)

| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |
|---|---|---|---|---|---|---|
| 7 ngày | 682 | 56.74 | 1.127 | 1.071 | 0.0357 | 122.66 |
| 14 ngày | 879 | 58.93 | 1.186 | 1.109 | 0.0483 | 224.27 |
| 30 ngày | 925 | 59.03 | 1.163 | 1.089 | 0.0432 | 197.8 |

## Cổng sang LIVE

- `live_ready.py`: **CHUA HOAN THANH** — PF(R) cua so 7 ngay = 1.127 < 1.2; PF($) cua so 7 ngay = 1.071 < 1.1; PF(R) cua so 14 ngay = 1.186 < 1.2; PF(R) cua so 30 ngay = 1.163 < 1.2; PF($) cua so 30 ngay = 1.089 < 1.1; kill-switch dang TRIPPED (6 consecutive losses (muc 12)) — chay `python risk.py --reset`
- `live_guard.py`: OK
- Tự động sang LIVE: **TẮT (`AUTO_LIVE_ARMED=false`)** · ĐÃ ĐỔI 1 LẦN

## Cấu hình rủi ro

- risk/lệnh `1.0%` · trần tổng `2.0%` · leverage `8` · MAX_POSITIONS `4` · trần size `1000.0` USDT
- Learner: 416 lần cập nhật trọng số · Hội đồng AI: **8 model**

## Ngưỡng rủi ro theo ví THẬT (3 mức)

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |
|---|---|---|---|---|
| < 20 | **giảm lệnh** | 1.0% | 1 | SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 20 – < 62 | **cân bằng** | 0.5% | 2 | SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 62 – < 100 | **cân bằng + BTC** | 1.0% | 2 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT |
| 100 trở lên | **an toàn** | 1.0% | 4 | BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT + ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT |

_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._

## Vị thế đang quản lý (0)

_không có vị thế nào trong `managed_state.json`_

---

Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · Số liệu thô: `logs/state_snapshot.json`
