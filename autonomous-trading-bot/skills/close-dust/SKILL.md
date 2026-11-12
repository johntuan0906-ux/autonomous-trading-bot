---
name: close-dust
description: Dùng khi cần đóng một vị thế quá nhỏ (notional < 5 USDT) mà sàn từ chối; gồm thứ tự thử và mã lỗi Binance đã đo thật.
metadata:
  openclaw:
    requires:
      bins: [python]
---

# Đóng "dust" (notional < 5 USDT) — chỉ có MỘT đường chạy được

Đo thật 11/11 trên TESTNET (AXS, 0,83 USDT). Thử theo thứ tự và **ghi mã lỗi** thay vì mò:

| Cách thử | Kết quả | Mã lỗi |
|---|---|---|
| Market + `reduceOnly: true` | sàn từ chối | `-2022 ReduceOnly Order is rejected` |
| Market KHÔNG `reduceOnly` | sàn từ chối vì notional < 5 | `-4164 Order's notional must be ≥ 5` |
| `STOP_MARKET closePosition` qua endpoint thường | phải dùng Algo API | `-4120` |
| Algo API, trigger cách xa | treo, **không** kích hoạt | (không có mã) |
| Algo API, trigger sát giá | từ chối | `-2021 Order would immediately trigger` |
| **Nâng vị thế lên ≥ 5 USDT (1 lệnh cùng chiều) rồi đóng TOÀN BỘ bằng market không `reduceOnly`** | **thành công** | — |

## Quy trình (dùng chính code của bot)

1. `python positions.py` — xác nhận qty + notional thật trên sàn.
2. Nâng cùng chiều để notional ≥ 5 USDT (giữ `LEVERAGE`, không đổi margin type).
3. Đóng **tổng** vị thế (gồm cả phần vừa nâng) bằng đường `_close_exact` của bot (market, không
   `reduceOnly`) — chấp nhận trả thêm phí, đổi lấy việc sạch vị thế.
4. Kiểm: `python positions.py` phải in `DA PHANG <symbol>`; nếu không, ghi mã lỗi vào `CONTEXT.md`.

## Không được làm

- Không gửi `reduceOnly` cho dust (đã biết chắc `-2022`).
- Không để vị thế dust nằm lại "cho xong": nó làm rác journal, re-arm SL mỗi vòng, và làm lệch
  `managed_state` (bot tưởng còn quản lý). Nếu 3 lần đóng thất bại, bot ghi `dust_skip.json` — chỉ dùng
  khi đã chấp nhận bỏ quản lý.
