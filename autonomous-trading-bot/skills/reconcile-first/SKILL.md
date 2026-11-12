---
name: reconcile-first
description: Dùng trước KHI KẾT LUẬN bất cứ điều gì về tiền (lãi/lỗ, chiến lược tốt/xấu, có nên gỡ kill-switch) trên tài khoản LIVE.
metadata:
  openclaw:
    requires:
      bins: [python]
---

# Kết luận về tiền phải đi qua 2 tool — trước, không phải sau

Đo thật 09/11: journal LIVE ghi **+124,50 USDT**, ví thật **27,90 USDT**; trong 102 vòng lệnh thì
**99 vòng do người đặt tay** (−4,61 USDT), bot 0 vòng trong cửa sổ đó. Nếu tin journal, kết luận sẽ
ngược hoàn toàn (tưởng chiến lược lãi, trong khi bot không hề vào lệnh).

## Thứ tự bắt buộc

```bash
python positions.py                 # [1] vị thế THẬT trên sàn (nguồn sự thật duy nhất)
python reconcile.py                 # [2] đối soát journal <-> fill thật (dry-run)
python reconcile.py --apply         # [3] chỉ khi cần bù CLOSE thiếu (tự tạo backup)
```

Chỉ sau 3 bước đó mới được đọc `journal.pnl`, `council_eval`, `lessons`.

## Cách đọc

- `positions.py` tách rõ **vị thế bot quản lý** vs **"MO TAY - bot KHONG quan ly"**. Vị thế tay KHÔNG
  tính vào hiệu suất chiến lược, kể cả khi nó lãi.
- `reconcile.py` giữ **2 ngăn riêng**: `closes` (khớp OPEN trong journal ⇒ của bot) và
  `unmatched_episodes` (không có OPEN ⇒ do người). Không gộp.
- `equity` là sự thật duy nhất về tiền; `journal.pnl` là lịch sử ghi chép, có thể thiếu dòng.

## Không được làm

- Không gỡ kill-switch dựa trên journal. Kill-switch tính từ `equity`, và chỉ được gỡ bằng
  `python tools/restart_bot.py --target <instance> --reset` sau khi đã đối soát.
- Không sửa `risk_state.json` bằng tay.
