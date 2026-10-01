# Binance Futures AI Rotation Bot (BTC/SOL/ETH/XRP)

Bot nghiên cứu/triển khai cho Binance USDⓈ-M Futures với 4 cặp:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- XRPUSDT

## Mục tiêu
Bot tự động:
1. Thu thập nến đa khung thời gian.
2. Tính tín hiệu kỹ thuật: EMA, RSI, MACD, ATR, ADX, Bollinger Bands, volume z-score, breakout.
3. Thu thập tin RSS/public feed và chấm điểm sentiment/risk theo từ khóa crypto, Fed, lãi suất, CPI, chiến tranh, bầu cử, regulation, ETF...
4. Chấm điểm 4 cặp rồi **chỉ chọn tối đa 1 vị thế toàn danh sách tại một thời điểm** (xoay vòng).
5. Tính SL/TP từ ATR + cấu hình RR.
6. Tự ngừng mở lệnh khi có risk-off, news blackout, drawdown, volatility shock hoặc tín hiệu không đủ mạnh.
7. Có `DRY_RUN=true` mặc định và `MODE=testnet` mặc định.

> Đây là phần mềm giao dịch tự động. Không có chiến lược nào đảm bảo lợi nhuận. Hãy backtest/paper trade/testnet trước live. API key nên tắt quyền rút tiền và giới hạn IP.

## Binance API
Thiết kế dùng REST trực tiếp để giảm phụ thuộc SDK bên thứ ba. Binance hiện vẫn mô tả USDⓈ-M Futures order/conditional-order flow và symbol filters trong Developer Docs; các trigger stop/take-profit có thể dùng MARK_PRICE hoặc CONTRACT_PRICE. Tham khảo docs chính thức trước khi chuyển sang live vì API có thể thay đổi.

## Cấu trúc
```text
binance_futures_ai_bot/
  .env.example
  requirements.txt
  pyproject.toml
  README.md
  config.yaml
  run.py
  bot_prompt.md
  binance_futures_ai_bot/
    config.py
    models.py
    engine.py
    indicators.py
    exchange/binance.py
    news/feeds.py
    news/scorer.py
    strategy/scorer.py
    risk/manager.py
    storage/db.py
  tests/test_indicators.py
```

## Cài đặt
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
```

## Chạy test
```bash
pytest -q
```

## Chạy bot
Profile hiện tại đã ưu tiên **LIVE**: `MODE=live`, `DRY_RUN=false`. Bot vẫn yêu cầu `ENABLE_LIVE_TRADING=YES` và API key trước khi được phép gửi lệnh.

```bash
python run.py
```

Để bật live, `.env` cần:
```env
MODE=live
DRY_RUN=false
ENABLE_LIVE_TRADING=YES
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

Thiết lập mặc định/risk hiện tại:
- `MODE=live` trong `.env.example`; mã nguồn từ chối live nếu chưa bật `ENABLE_LIVE_TRADING=YES`
- `DRY_RUN=false`
- 4 cặp xoay vòng
- 1 position max
- rủi ro mỗi lệnh 0.5% equity
- daily loss limit 2%
- max drawdown 8%

## Lưu ý về live
API key chỉ nên có quyền Futures trading cần thiết, không bật quyền rút/chuyển tiền và nên giới hạn IP trong Binance. Binance yêu cầu API key/signature cho các endpoint giao dịch; các endpoint signed dùng HMAC SHA256 và timestamp/recvWindow. citeturn472178search5turn610249search1

**Lưu ý ngày 2026-09-16:** cấu hình hiện tại có macro blackout cho 2026-09-15 và 2026-09-16, nên engine sẽ không mở vị thế mới trong các ngày này. Đây là risk-control chủ động, không phải lỗi kết nối.

## Lưu ý về news
Không thể “xem mọi thứ trên Internet”. Package dùng mô hình feed mở + bộ từ khóa. Có thể mở rộng `config.yaml -> news.feeds` bằng RSS/API hợp pháp khác. Tin tức không được phép một mình quyết định lệnh: nó chỉ điều chỉnh điểm tín hiệu/risk regime.
