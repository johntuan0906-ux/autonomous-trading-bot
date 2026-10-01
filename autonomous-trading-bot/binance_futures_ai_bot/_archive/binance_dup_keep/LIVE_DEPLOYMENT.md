# LIVE DEPLOYMENT

1. Copy `.env.example` thành `.env`.
2. Điền `BINANCE_API_KEY` và `BINANCE_API_SECRET`.
3. Kiểm tra `MODE=live`, `DRY_RUN=false`, `ENABLE_LIVE_TRADING=YES`.
4. API key: chỉ cấp quyền Futures trading cần thiết; không cấp quyền withdrawal/transfer; giới hạn IP nếu có thể.
5. Chạy `pytest -q`.
6. Chạy `python run.py`.

Bot sẽ tự động:
- quét BTCUSDT/ETHUSDT/SOLUSDT/XRPUSDT;
- chỉ giữ tối đa 1 vị thế;
- chọn LONG/SHORT;
- đặt SL/TP;
- ngừng mở lệnh khi risk controls/news blackout kích hoạt.

`ENABLE_LIVE_TRADING=YES` chỉ là khóa khởi động một lần; bot không hỏi xác nhận ở mỗi lệnh.

Không có cơ chế nào đảm bảo lợi nhuận. Live futures có thể gây thua lỗ nhanh, đặc biệt khi dùng đòn bẩy.
