---
name: drift-report
description: Dùng khi vừa sửa code (số lớp lỗi, số test, tên tool, mã reason_code) hoặc trước khi commit; kiểm tài liệu có còn khớp code không.
metadata:
  openclaw:
    requires:
      bins: [python]
---

# Tài liệu ↔ code: sửa TÀI LIỆU, đừng nới ngưỡng

`tools/drift_docs.py` đối chiếu từng khẳng định bằng số trong tài liệu với code thật (3 loại: số liệu,
tên tool, mã `reason_code`). Nó ra đời sau 3 lần tài liệu ghi số cũ (50 lớp/166 test trong khi code đã
51/176).

## Quy trình

```bash
python tools/drift_docs.py --check     # rc=0: sạch;  rc=1: có LECH
python tools/golden_set.py --check     # 45 ca / 14 cổng, cũng phát hiện DRIFT
python tools/bug_catalog.py --check    # số lớp + test chốt
```

## Cách xử lý từng loại kết quả

- **[LECH]** — tài liệu sai số: sửa **tài liệu** cho khớp code (hoặc sửa code nếu code sai). Không sửa
  ngưỡng so sánh, không thêm ngoại lệ.
- **[WARN]** — mã lớp lỗi trong tài liệu không có trong `bug_catalog.CLASSES`: thường là mã lịch sử đã
  gộp; nếu là mã mới thì phải thêm lớp vào catalog (kèm ≥1 test chốt), không để WARN tồn tại.
- **DRIFT của golden** — baseline chỉ hash **các key đã khai trong `expect.output`**, nên DRIFT nghĩa là
  hợp đồng đổi thật. Nếu chỉ là dữ liệu sống tăng theo ngày thì đó là lỗi của bài test (đã từng xảy ra:
  `jrn-feats-integrity` đọc journal sống ⇒ `n_checked` tăng mỗi ngày ⇒ DRIFT giả).

## Không được làm

- Không "sửa" bằng cách thêm file vào danh sách bỏ qua.
- Không commit khi `--check` còn rc≠0 (chuỗi kiểm tra này là điều kiện trước commit trong `OPERATIONS.md`).
