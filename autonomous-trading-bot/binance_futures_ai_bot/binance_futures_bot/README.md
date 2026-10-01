# Binance Futures Auto Trading Bot (Long/Short đa cặp, xoay vòng)

Bot giao dịch **Binance USDⓈ-M Futures** tự động hoàn toàn — tự phân tích,
tự vào lệnh, tự đặt SL/TP, tự thoát lệnh — xoay vòng giữa 4 cặp
`BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT` (có thể đổi trong cấu hình),
không cần xác nhận thủ công cho từng lệnh.

> ⚠️ **Đây KHÔNG phải lời khuyên đầu tư.** Giao dịch futures có đòn bẩy rủi
> ro rất cao và có thể mất toàn bộ vốn nhanh chóng. Xem mục
> [Cảnh báo rủi ro](#10--cảnh-báo-rủi-ro--đọc-kỹ-trước-khi-dùng-tiền-thật)
> trước khi chạy với tiền thật.

---

## 1. Bản đặc tả phần mềm (Software Spec)

Đây là bản đặc tả mà toàn bộ code trong package này hiện thực hoá — dùng để
tham khảo khi muốn mở rộng, tinh chỉnh hoặc đưa cho một AI/coder khác tiếp
tục phát triển.

```
MỤC TIÊU
- Bot giao dịch Futures Binance (USDⓈ-M), giao dịch cả hai chiều Long/Short.
- 4 cặp: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT — xoay vòng đánh giá mỗi chu kỳ.
- Mỗi symbol chỉ được PHÉP 1 vị thế mở tại một thời điểm (không trùng lệnh).
- Tự động so sánh độ mạnh tín hiệu giữa các cặp để ưu tiên khi số lệnh mở
  đồng thời bị giới hạn.
- Tự tính và đặt Stop-Loss / Take-Profit cho mọi lệnh (không có lệnh nào
  được mở mà thiếu SL).
- Tín hiệu vào/thoát lệnh dựa trên:
    (a) Phân tích kỹ thuật đa chỉ báo (EMA, RSI, MACD, Bollinger Bands, ATR)
    (b) Cảm xúc tin tức: kinh tế vĩ mô, Fed/lãi suất, chính trị, pháp lý,
        tin tức riêng từng đồng coin
- Hoàn toàn tự động: không chờ xác nhận của người dùng để vào/thoát lệnh.
- Có cơ chế an toàn tự động: giới hạn rủi ro mỗi lệnh theo % vốn, giới hạn
  số lệnh mở đồng thời, ngắt mạch khi lỗ trong ngày vượt ngưỡng, cooldown
  sau khi đóng lệnh trên một symbol.

KIẾN TRÚC
- exchange_client  : giao tiếp Binance Futures API (dữ liệu giá, tài khoản,
                      đặt/huỷ lệnh, đặt SL/TP qua Algo Order API)
- indicators        : tính chỉ báo kỹ thuật, gộp thành 1 điểm số [-1, 1]
- news_sentiment     : lấy tin tức, chấm điểm cảm xúc, gộp thành 1 điểm số [-1, 1]
- signal_engine      : kết hợp 2 điểm số trên theo trọng số -> LONG/SHORT/HOLD
- risk_manager       : tính khối lượng lệnh, SL/TP theo ATR, ngắt mạch, cooldown
- position_manager    : đồng bộ trạng thái vị thế từ sàn, đảm bảo không trùng lệnh
- trade_executor     : điều phối mở/đóng lệnh thực tế
- main               : vòng lặp chính, chạy định kỳ theo cycle_interval_seconds
```

---

## 2. Cấu trúc thư mục

```
binance_futures_bot/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── config/
│   └── config.yaml          # toàn bộ tham số chiến lược/rủi ro
├── bot/
│   ├── main.py               # vòng lặp chính
│   ├── config_loader.py
│   ├── logger_setup.py
│   ├── exchange_client.py    # giao tiếp Binance Futures (REST, qua python-binance)
│   ├── indicators.py         # EMA/RSI/MACD/Bollinger/ATR -> điểm kỹ thuật
│   ├── news_sentiment.py     # CryptoPanic + NewsAPI -> điểm tin tức
│   ├── signal_engine.py      # gộp điểm -> LONG/SHORT/HOLD + so sánh giữa các cặp
│   ├── risk_manager.py       # position sizing, SL/TP, circuit breaker
│   ├── position_manager.py   # đảm bảo không trùng lệnh, xoay vòng
│   ├── trade_executor.py     # thực thi lệnh
│   ├── notifier.py           # thông báo Telegram (tuỳ chọn)
│   └── backtest.py           # backtest đơn-cặp + quét tham số (xem mục 7)
└── tests/
    ├── test_indicators.py    # unit test không cần mạng/API key
    └── test_backtest.py      # unit test công thức win-rate/PF/drawdown
```

---

## 3. Cài đặt

Yêu cầu Python 3.9+.

```bash
cd binance_futures_bot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Mở file .env và điền BINANCE_API_KEY / BINANCE_API_SECRET
```

Tạo API key tại **Binance Futures Testnet** (khuyến nghị dùng trước):
https://testnet.binancefuture.com — hoàn toàn miễn phí, dùng tiền ảo.

---

## 4. Cấu hình

Hai nơi cấu hình:

- **`.env`** — thông tin nhạy cảm: API key/secret, bật/tắt testnet,
  bật/tắt DRY_RUN, API key nguồn tin tức (tuỳ chọn), Telegram (tuỳ chọn).
- **`config/config.yaml`** — toàn bộ tham số chiến lược: danh sách cặp,
  khung thời gian, % rủi ro mỗi lệnh, số lệnh mở đồng thời tối đa, hệ số
  ATR cho SL/TP, ngưỡng tín hiệu, trọng số kỹ thuật/tin tức, v.v. Đã có
  giá trị mặc định hợp lý — đọc kỹ comment trong file để tinh chỉnh.

**Hai cờ an toàn quan trọng nhất trong `.env`:**

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `USE_TESTNET` | `true` | `true` = sàn thử nghiệm (tiền ảo) |
| `DRY_RUN` | `true` | `true` = chỉ mô phỏng, không gửi lệnh thật lên sàn (kể cả trên mainnet) |

Bot sẽ **chỉ thực sự đặt lệnh bằng tiền thật** khi cả hai đều được đặt
`false` — đây là quyết định người dùng phải tự đưa ra một cách chủ động.

---

## 5. Chạy bot

```bash
# Cách 1: chạy trực tiếp
python -m bot.main

# Cách 2: cài đặt như package rồi chạy lệnh có sẵn
pip install -e .
binance-futures-bot
```

Bot sẽ chạy liên tục (vòng lặp vô hạn), quét lại toàn bộ 4 cặp mỗi
`cycle_interval_seconds` giây (mặc định 300s = 5 phút). Nhấn `Ctrl+C` để
dừng an toàn (bot sẽ không huỷ các lệnh SL/TP đã đặt trên sàn — vị thế
vẫn được bảo vệ khi bot tắt).

Log được in ra console và ghi vào `logs/bot.log` (tự xoay vòng khi đầy).

### Chạy nền dài hạn

Khuyến nghị chạy bằng `systemd`, `tmux`/`screen`, `pm2`, hoặc Docker để
bot không bị dừng khi đóng terminal hay mất kết nối SSH.

### Kiểm thử nhanh (không cần API key)

```bash
python -m pytest tests/ -v
```

---

## 6. Cơ chế an toàn đã tích hợp sẵn

Vì yêu cầu là bot **tự vào/thoát lệnh hoàn toàn tự động, không chờ người
dùng quyết định**, các giới hạn dưới đây đóng vai trò "người giám sát tự
động" thay cho con người:

- **Không lệnh nào thiếu SL** — mọi lệnh MARKET vào lệnh đều được theo
  sau ngay bằng lệnh SL (STOP_MARKET) và TP (TAKE_PROFIT_MARKET) đặt
  thẳng trên sàn qua Algo Order API của Binance.
- **Position sizing theo % rủi ro** — khối lượng mỗi lệnh được tính sao
  cho nếu SL bị chạm, mức lỗ đúng bằng `risk_per_trade_pct` % vốn, không
  phụ thuộc đòn bẩy đặt bao nhiêu.
- **Giới hạn số lệnh mở đồng thời** (`max_concurrent_positions`) — không
  để bot dồn hết vốn vào cùng lúc 4 cặp.
- **Ngắt mạch lỗ ngày** (`max_daily_loss_pct`) — tự động dừng mở lệnh
  mới (không đóng lệnh đang có) nếu tổng lỗ trong ngày vượt ngưỡng.
- **Cooldown sau khi đóng lệnh** — tránh vào lại ngay một symbol vừa
  đóng lệnh (dễ bị "trade liên tục" khi thị trường đi ngang/nhiễu).
- **Không trùng lệnh** — `position_manager` luôn đồng bộ trực tiếp từ
  sàn trước khi quyết định, đảm bảo mỗi symbol tối đa 1 vị thế.
- **DRY_RUN mặc định bật** — bot mới cài sẽ không gửi lệnh thật cho đến
  khi người dùng chủ động tắt.

Những cơ chế trên **giảm** rủi ro chứ không loại bỏ — vẫn có thể mất tiền
do trượt giá mạnh, mất kết nối API đúng lúc thị trường biến động, lỗi hạ
tầng sàn, hoặc đơn giản là chiến lược sai hướng trong giai đoạn đó.

---

## 7. Backtest — kiểm định chiến lược trước khi tin tưởng chạy live

### Vì sao "đặt tiêu chí win-rate/PF" không phải chuyện set 1 con số

Với chiến lược dạng SL/TP cố định theo ATR, ba đại lượng sau ràng buộc
lẫn nhau qua công thức:

```
Profit Factor = (win-rate × R:R) / (1 − win-rate)
R:R = tp_atr_multiplier / sl_atr_multiplier   (xấp xỉ, nếu không bị thoát sớm)
win-rate hoà vốn (PF=1.0) = 1 / (1 + R:R)
```

Ví dụ: với R:R = 2:1 (mặc định của bot, `sl_atr_multiplier=1.5` /
`tp_atr_multiplier=3.0`), win-rate hoà vốn ≈ 33.3%. Ở win-rate 35%, PF lý
thuyết ≈ 1.08 — đúng hướng nhưng biên rất mỏng, dễ bị phí giao dịch +
funding rate + trượt giá ăn hết. **Win-rate không phải tham số bạn set
trực tiếp** — nó là kết quả phát sinh từ `long_threshold`/`short_threshold`
(độ chọn lọc tín hiệu) + R:R + hành vi thật của thị trường. Cách duy nhất
biết chắc một bộ cấu hình có đạt tiêu chí (vd. win-rate≥35% và PF≥1.0) hay
không là chạy trên dữ liệu lịch sử thật.

### Cách dùng `bot/backtest.py`

Không cần API key — dùng endpoint dữ liệu nến **công khai** của Binance
Futures.

```bash
# Backtest 1 cấu hình (dùng đúng config.yaml hiện tại) trên 180 ngày gần nhất
python -m bot.backtest --symbol BTCUSDT --days 180

# Quét lưới nhiều mức threshold/R:R, in bảng so sánh + đánh dấu cấu hình
# nào đạt win-rate≥35% và PF≥1.0 (với số lệnh đủ tin cậy thống kê)
python -m bot.backtest --symbol BTCUSDT --days 180 --sweep --min-trades 30
```

Chạy riêng cho từng cặp trong 4 cặp (BTCUSDT/ETHUSDT/SOLUSDT/XRPUSDT) vì
mỗi coin có đặc tính biến động khác nhau — cấu hình tối ưu cho BTC chưa
chắc tối ưu cho XRP.

### Giới hạn của backtest này — đọc kỹ trước khi tin số liệu

1. **`news_score` luôn = 0 (trung lập)** trong backtest — không có nguồn
   dữ liệu tin tức lịch sử miễn phí đủ tốt để mô phỏng lùi thời gian. Số
   liệu backtest phản ánh **hiệu suất thuần phân tích kỹ thuật**, chưa
   tính phần tin tức thật (phần tin tức chỉ phát huy tác dụng khi chạy
   live với API key thật).
2. **Không mô phỏng funding rate** (phí 8h/lần) — chỉ có phí giao dịch
   ước lượng qua `--fee-bps`. Lệnh giữ qua nhiều chu kỳ funding sẽ có PF
   thật thấp hơn số backtest báo ra.
3. **Đơn giản hoá intrabar**: nếu cả SL và TP cùng nằm trong biên độ 1
   nến, giả định SL bị chạm trước (kịch bản thận trọng, không phải luôn
   đúng thực tế).
4. **Hiệu suất quá khứ không đảm bảo cho tương lai** — dùng công cụ này
   để so sánh *tương đối* giữa các cấu hình và hiểu cơ chế, không phải để
   lấy một con số PF rồi tin chắc nó sẽ lặp lại khi chạy live.

---

## 8. Giới hạn của phần tín hiệu tin tức — đọc kỹ

Module `news_sentiment.py` dùng **VADER** (mô hình chấm điểm cảm xúc dựa
trên từ điển, nhẹ, chạy offline) cộng thêm một danh sách từ khoá trọng số
thủ công (ví dụ "rate hike" → tiêu cực, "etf approval" → tích cực). Đây
là một bộ lọc **heuristic đơn giản**, KHÔNG phải mô hình NLP tài chính
chuyên sâu, và không có gì đảm bảo nó phản ánh đúng tác động thực tế của
một tin tức lên giá. Các quỹ định lượng chuyên nghiệp dùng hạ tầng phức
tạp hơn rất nhiều (dữ liệu độ trễ thấp, mô hình NLP huấn luyện riêng cho
tài chính, kiểm định thống kê nghiêm ngặt). Hãy coi điểm tin tức ở đây là
một tín hiệu **bổ trợ** (mặc định chỉ chiếm 40% trọng số so với 60% của
phân tích kỹ thuật), không phải nguồn "alpha" đáng tin cậy một mình nó.

Không có `CRYPTOPANIC_API_KEY` / `NEWSAPI_API_KEY` trong `.env`? Bot vẫn
chạy bình thường — điểm tin tức sẽ luôn là 0 (trung lập), quyết định lúc
đó hoàn toàn dựa vào phân tích kỹ thuật.

---

## 9. Lưu ý kỹ thuật quan trọng về Binance API

Kể từ **2025-12-09**, Binance yêu cầu các lệnh điều kiện (STOP_MARKET,
TAKE_PROFIT_MARKET, STOP, TAKE_PROFIT, TRAILING_STOP_MARKET) trên
USDⓈ-M Futures phải đặt qua **Algo Order API** (`/fapi/v1/algoOrder`)
thay vì endpoint lệnh thường — gửi qua endpoint cũ sẽ bị từ chối với lỗi
`-4120`. Package này đã dùng đúng `futures_create_algo_order(...)`
(có sẵn từ `python-binance >= 1.0.37`) cho toàn bộ SL/TP; xem
`bot/exchange_client.py` nếu cần đối chiếu hoặc cập nhật khi Binance
thay đổi API trong tương lai.

---

## 10. ⚠️ Cảnh báo rủi ro — đọc kỹ trước khi dùng tiền thật

- Đây **không phải lời khuyên tài chính/đầu tư**, và đây không phải cố
  vấn tài chính. Đây là phần mềm được viết theo yêu cầu kỹ thuật, không
  phải khuyến nghị giao dịch.
- Giao dịch futures có đòn bẩy có thể khiến bạn **mất nhanh hơn nhiều**
  so với giao dịch spot, kể cả toàn bộ số vốn đã nạp vào ví futures.
- **Không có chiến lược nào được đảm bảo sinh lời.** Package có kèm công
  cụ backtest (mục 7) để bạn tự kiểm định trên dữ liệu lịch sử thật —
  nhưng dù backtest ra PF>1, hiệu suất quá khứ vẫn không đảm bảo cho
  tương lai, và backtest ở đây chưa tính được phần tin tức/funding rate.
- Bot chạy **hoàn toàn tự động theo đúng yêu cầu ban đầu** — điều đó
  đồng nghĩa nó sẽ tiếp tục vào lệnh ngay cả khi thị trường bất thường,
  trừ khi cơ chế ngắt mạch (mục 6) được kích hoạt. Nên theo dõi log định
  kỳ, đừng "chạy rồi quên".
- Khuyến nghị mạnh: chạy trên **testnet** ít nhất vài tuần, quan sát kỹ
  hành vi thật của bot, rồi mới cân nhắc chuyển sang mainnet với **số
  vốn nhỏ** bạn chấp nhận mất hoàn toàn, trước khi tăng dần quy mô.
- Chỉ giao dịch với số tiền bạn có thể chấp nhận mất.

---

## 11. Mở rộng thêm

Một vài hướng nâng cấp tự nhiên nếu muốn phát triển tiếp:

- Mở rộng `backtest.py` từ đơn-cặp sang đa-cặp (portfolio-level), mô
  phỏng đúng luôn `max_concurrent_positions` giữa 4 cặp thay vì test
  riêng lẻ từng cặp.
- Thay VADER bằng mô hình NLP tài chính chuyên biệt hơn (vd. FinBERT) để
  chấm điểm tin tức chính xác hơn.
- Thêm trailing-stop (Binance đã hỗ trợ `TRAILING_STOP_MARKET` qua cùng
  Algo Order API) để khoá lợi nhuận khi giá đi đúng hướng xa.
- Lưu lịch sử lệnh vào database (SQLite/Postgres) thay vì chỉ log ra file,
  phục vụ phân tích hiệu suất theo thời gian.
