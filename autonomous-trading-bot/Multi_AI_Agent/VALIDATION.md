# Kết quả kiểm chứng

Ngày thực hiện: 01/10/2026.

- Môi trường: Linux, Python 3.12.14.
- SDK: OpenAI 2.54.0; Pydantic 2.13.5; python-dotenv 1.2.4.
- Lab gốc, chạy bằng unittest: **17 tests, OK**.
- Bổ sung ClinePass 1.1.0: **12 tests, OK** (29 test trong toàn bộ dự án).
- Chạy CLI `doctor`: exit code 0, không gọi mạng.
- Chạy CLI mock `handoff`: completed, 4 lượt mô phỏng.
- Chạy CLI mock `group`: completed, 8 lượt mô phỏng.
- Chạy CLI mock `parallel`: completed, 4 lượt mô phỏng.
- Đầu vào CLI sử dụng `examples/review_task.txt` và `examples/buggy_stats.py`.
- Trường hợp OpenAI thiếu key: exit code 2, thông báo cấu hình rõ ràng, không gửi request.
- Đọc cú pháp tất cả file Python và cấu hình JSON của VS Code: thành công.

Các test dùng OpenAI SDK thật để tạo request, nhưng lớp HTTP được thay bằng
`httpx.MockTransport`. Không có API key thật, không gửi request suy luận đến
OpenAI và không đo chất lượng câu trả lời AI trong quá trình kiểm chứng này.

Phần ClinePass dùng `httpx.AsyncClient` với `httpx.MockTransport` để xác nhận
endpoint, bearer header, đúng model ID, và `stream: false`. Test đặt hàng rào
đồng bộ để cả 14 nhánh phải vào HTTP handler trước khi một nhánh được trả lời;
finalizer chỉ được gọi sau đủ 14 kết quả. Đây là bằng chứng chạy đồng thời phía
client, không phải đo concurrency thực tế của tài khoản ClinePass.

Đã kiểm tra retry và ngân sách, lỗi model 404 không chuyển model khác, lưu
13 kết quả khi 1 model lỗi, timeout và cancellation giữ lại báo cáo, phản hồi
bị cắt không được đánh dấu thành công, và việc rút gọn đầu vào finalizer được
ghi rõ. CLI mock đủ 14 model chạy không cần HTTP client hoặc key, kể cả khi
môi trường có proxy không hợp lệ. CLI thiếu CLINE_API_KEY dừng trước khi gọi mạng.

Không gọi API Cline thật. Chạy `cline_multi.py check --provider clinepass`
để kiểm tra key/quota tại máy bạn; lệnh này sử dụng quota thật.

Chưa chạy trực tiếp trên Windows/macOS. Hướng dẫn Windows dùng đường dẫn
interpreter trong `.venv` để tránh phụ thuộc activation của shell.

Để xác nhận trên máy bạn, cài requirements và chạy:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py doctor --live
```

Lệnh thứ hai cần API key/quota và có thể phát sinh phí API. Sau đó chạy một
nhiệm vụ có tiêu chí chấp nhận rõ bằng `--provider openai` để đánh giá kết quả.
