# MASTER PROMPT – Binance Futures Autonomous Rotation Bot

Bạn là kỹ sư hệ thống giao dịch định lượng. Xây bot Binance USDⓈ-M Futures cho BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT.

Yêu cầu bắt buộc:
- Bot tự động thu thập market data và news feed.
- Không hỏi người dùng mỗi lần vào/thoát lệnh.
- Chỉ tối đa 1 vị thế đang mở trên toàn bộ 4 symbol.
- Khi đang có vị thế, bỏ qua mọi tín hiệu mở vị thế khác.
- Rotation: định kỳ xếp hạng 4 symbol và chọn symbol có score cao nhất vượt ngưỡng.
- Long/Short dựa trên hợp nhất trend, momentum, volatility, volume, regime và news macro.
- Tín hiệu kỹ thuật: EMA 20/50/200, RSI, MACD, ATR, ADX, Bollinger Bands, breakout, volume z-score.
- Multi-timeframe: 5m, 15m, 1h, 4h.
- News: crypto, Fed/FOMC, rates, CPI, jobs, ETF, regulation, war/geopolitics, major political events.
- Tin tức chỉ là một thành phần; news shock có thể khóa giao dịch.
- SL/TP: ATR based, RR configurable; không đặt SL quá sát.
- Position sizing theo fixed fractional risk.
- Stop trading nếu daily loss hoặc max drawdown vượt giới hạn.
- Có cooldown sau lệnh thua, tránh overtrading.
- Chống duplicate client order IDs và duplicate positions.
- Đồng bộ symbol filters từ exchangeInfo: tickSize/stepSize/minQty.
- Có DRY_RUN/testnet mặc định.
- Có logging, SQLite trade journal, config file, unit tests.
- Xử lý lỗi mạng, timeout, rate limit, stale data, clock drift.
- Không giả định tin tức hoàn hảo; nếu news service lỗi thì giảm confidence, không tự động “đoán”.
- Không dùng leverage lớn mặc định.
- Không có chức năng rút/chuyển tiền.
- Không được tuyên bố chiến lược đảm bảo lợi nhuận.

Kiến trúc modules:
config -> market data -> indicators -> news -> signal scorer -> risk manager -> rotation engine -> execution -> journal.

Mục tiêu là code production-oriented nhưng an toàn: mặc định testnet/dry-run, live cần opt-in rõ ràng.
