# Autonomous Binance Futures Trading Bot (USDT-M)

Bot tự trị 100%: quét 4 cặp `BTC/ETH/SOL/XRP-USDT`, chấm **Composite Alpha Score**
(Technical Momentum 80% + Macro Sentiment 20%), mở tới **4 vị thế**
(MAX_POSITIONS=4, hedge 2 chiều), SL `2.0×ATR` / TP `5.0×ATR`
(sweep tốt nhất: PF 1.314), kill-switch tự ngắt (lỗ ngày ≥2%).

## 1. Cài đặt

```bash
pip install -e ".[dev]"
# hoặc: pip install ccxt pandas numpy requests feedparser vaderSentiment python-dotenv pydantic
cp .env.example .env   # điền API key
```

> Windows chưa có Python: `winget install Python.Python.3.12`, mở terminal mới rồi chạy tiếp.

## 2. Chạy

```bash
python main.py --once   # chạy 1 vòng scan (dry-run mặc định)
python main.py          # vòng lặp liên tục
```

`DRY_RUN=true` (mặc định) = không gửi lệnh thật, chỉ log quyết định.

### Chạy nền độc lập VS Code (tuần testnet)

```bash
pythonw run_forever.py   # supervisor: tự restart khi crash, không hiện cửa sổ
```

- Auto-start khi đăng nhập Windows: giá trị `TradingBotTurbo` trong
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (đã ghi qua lệnh).
- Kill: `Stop-Process -Id (Get-Content logs\.supervisor.lock)` rồi xóa giá trị Run trên.
- Log: `logs/turbo_err.log` (marker `[supervisor]` trước/sau mỗi lần restart).

## 3. Kiến trúc

| File | Vai trò |
|---|---|
| `config.py` | Cấu hình từ `.env`, validate R:R ≥ 1:2 |
| `indicators.py` | EMA/RSI/MACD/ATR + `technical_score` ∈ [-1,+1] |
| `sentiment.py` | CryptoPanic + RSS (CoinDesk/CT/Fed) + VADER/LLM → [-1,+1] |
| `ranking.py` | Composite alpha + xếp hạng + `sentiment_veto` |
| `risk.py` | `atr_levels`, `position_size`, `KillSwitch` |
| `portfolio.py` | Chặn trùng symbol, Single Best Setup |
| `exchange.py` | Wrapper ccxt Binance Futures (testnet, reduce-only SL/TP) |
| `bot.py` | Vòng lặp tự trị scan→rank→size→execute→monitor |
| `position_sync.py` | **P0-1:** adopt vị thế đang mở THẬT trên sàn khi khởi động lại |
| `managed_state.py` | **P0-1:** lưu mốc 1R/partial/BE/booked_pnl để R không sai sau restart |
| `run_forever.py` | Supervisor + **watchdog nhịp tim** (bot treo vẫn bị kill/restart) |
| `turbo_demo.py` | Runner demo: 4 cặp song song, learner, kill-switch, heartbeat |
| `agents.py` | **Phase 1:** tầng multi-AI agent (macro/critic/review) — chỉ cố vấn, shadow, có trần chi phí + circuit breaker |
| `reconcile.py` | **P0:** đối chiếu journal với fill thật của sàn, ghi bù CLOSE bị thiếu |
| `monitor_report.py` | Gate LIVE: n/PF/2 chiều/strategy âm/BLOCKED_LEARN (`--strict`) |
| `main.py` | Entry point |

## 4. Logic quyết định

1. **Score kỹ thuật** mỗi cặp: trend EMA50/200 (±0.40) + RSI (±0.30) + MACD (±0.20) + breakout 20 nến (±0.10).
2. **Score tin tức**: trung bình VADER headlines CryptoPanic+RSS (FED/CoinDesk...), cache 5 phút.
3. **Alpha** = 0.80·tech + 0.20·sent. Cặp đạt `MIN_ALPHA_SCORE` (0.05) và hơn cặp kế ≥ `MIN_EDGE` (0.05) được mở (tối đa `MAX_POSITIONS`=4).
4. **Veto**: sentiment ≤ -0.5 chặn LONG (FUD vĩ mô), ≥ +0.5 chặn SHORT (stimulus); tin "urgent" (>20 bài) cũng chặn.
5. **Overlap**: đã có vị thế symbol đó → chặn; cooldown 60s giữa 2 lệnh cùng symbol.
6. **Risk**: SL/TP từ ATR, size = risk% / |entry-SL|; kill-switch khi lỗ ngày ≥2%, ATR% ≥2% hoặc ≥5 lỗi API liên tiếp.

## 5. Test

```bash
python -m unittest discover -s tests -v
```

## 6. Live trading checklist

1. `BINANCE_TESTNET=false`, nhập key Futures đã bật Hedge/Futures permission.
2. `DRY_RUN=false`, `BALANCE_USDT` = số dư thật, `LEVERAGE`/`RISK_PER_TRADE_PCT` nhỏ trước.
3. Chạy thử testnet ≥ 1 tuần, theo dõi log OPEN/CLOSE/BLOCKED/KILLED.
4. Đánh giá bằng `monitor_report.py` (journal ghi OPEN+CLOSE nên tính được WR/PF):

   ```bash
   python monitor_report.py --log logs/turbo_err.log --days 7
   ```

   Monitor in `LOG STATUS` cho **cả toàn bộ lịch sử** lẫn **N ngày gần nhất**
   (`--ops-days`, mặc định 3) để phân biệt số cũ (trước khi sửa label P0-7) với
   phản hồi hiện tại của learner; `KILL/STOPPED` luôn được quét toàn bộ (không
   bao giờ quên kill-switch).

### Tiêu chí chuyển testnet → LIVE

Chỉ flip `BINANCE_TESTNET=false` khi **tất cả** đạt (monitor tự in `READY FOR LIVE`):

> Ghi chú đọc số liệu (30/09/2026): `reconcile.py` (xem dưới) đã ghi bù 11 lệnh
> đóng bị thiếu trong journal bằng fill thật trên sàn. Các chỉ số dưới đây tính
> trên journal **sau khi đối chiếu**, không phải trên 35 lệnh "đẹp".

| Tiêu chí | Ngưỡng |
|---|---|
| Số lệnh đóng trong journal | ≥ **50** |
| Profit Factor (theo R) | ≥ **1.2** |
| Lệnh `KILLED` trong log | = 0 (không trigger kill-switch) |
| Lỗ ngày sâu nhất | < 2% (`MAX_DAILY_LOSS_PCT`) |
| Số ngày mẫu (sample) | ≥ **3** ngày có lệnh đóng (tránh mẫu 1 phiên) |
| Trải nghiệm 2 chiều | mỗi hướng LONG/SHORT ≥ **5** lệnh (mẫu 100% SHORT ⇒ PF vô nghĩa) |
| Backtest sweep `sweep.py` | PASS (gần nhất: SL 2.0/TP 5.0 → PF 1.314) |

**Cảnh báo (không chặn LIVE)**: `BLOCKED_LEARN` trong 3 ngày gần nhất > `OPENED`
⇒ learner đang chặn gần như mọi setup (nghi label P0-7 hoặc weight cũ trong
`logs/learner.json`). Block chỉ làm **giảm** số lệnh nên không tạo rủi ro tiền;
chiều nguy hiểm (learner đảo ngược ⇒ mở lệnh tồi) đã bị chốt `PF ≥ 1.2` bắt.
Thêm `--strict` nếu muốn nâng cảnh báo này thành lý do **chặn** LIVE.

Nếu PF < 1.2 → quay lại `sweep.py` tinh chỉnh SL/TP, **không** tăng leverage.
Sweep 30 ngày × 8 cặp (01/10): config hiện tại **rank #2/40, PF 1.148** — gần gate
nhưng chưa tới; grid đầy đủ trong `logs/sweep_grid_30d_8sym.json`. Khi journal đạt
≥50 lệnh thật: chạy lại grid, chỉ đổi cấu hình nếu cải thiện **cùng lúc** PF 30 ngày
và số liệu testnet thật (tránh overfit cửa sổ).
Nếu PF > 1.2 ổn định qua ≥ 100 lệnh → mới cân nhắc `LEVERAGE` 8 → 10 (risk/trade vẫn 1%).

### Tăng tốc thu mẫu testnet mà KHÔNG tăng risk

Chưa đủ 50 lệnh là lý do phổ biến nhất phải chờ testnet lâu. Cách an toàn nhất là
thêm cặp để **tăng cơ hội tìm setup đạt alpha**, không hạ ngưỡng vào lệnh:

```bash
# .env — mặc định 4 cặp; thêm cặp để quét song song nhiều hơn
EXTRA_SYMBOLS=ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT
```

- `active_symbols(cfg)` = `SYMBOLS` + `EXTRA_SYMBOLS` (khử trùng, giữ thứ tự);
  thêm cặp chỉ mở rộng *danh sách được xét*, `MIN_ALPHA_SCORE`/`MIN_EDGE`
  **giữ nguyên**.
- Risk mỗi lệnh vẫn 1%, và `portfolio.can_add_risk()` chặn khi tổng risk 1R vượt
  `MAX_TOTAL_RISK_PCT` (3%) ⇒ 3 vị thế × 1% là lệnh thứ 4 bị từ chối, **bất kể**
  universe có 4 hay 7 cặp (xem `tests/test_symbols_universe.py`).
- Cặp không được trùng trong `SYMBOLS` (config báo lỗi ngay) và phải là hợp đồng
  futures có trên sàn testnet.
- Đã có vị thế ở cặp nào thì cặp đó bị `SKIP_OPEN` cho tới khi đóng — thêm cặp chỉ
  giúp tăng số *lệnh song song*, không nhân đôi vị thế trên cùng cặp.

### Journal bị thiếu khi bot tắt — dùng `reconcile.py`

Bot tắt/restart trong lúc đang mở vị thế ⇒ sàn vẫn đóng vị thế bằng SL/TP nhưng
không ai ghi `CLOSE` vào `logs/journal.jsonl` ⇒ `monitor_report.py` thiếu lệnh
(n / WR / PF / LONG-SHORT), gate LIVE bị lệch (có thể "đẹp" hơn thực tế).

```bash
python reconcile.py            # xem trước (KHÔNG sửa gì): vòng lệnh tái tạo/quan hệ với journal
python reconcile.py --apply    # ghi bù CLOSE thật (backup logs/journal.jsonl.bak-*)
```

Cách làm: đọc fill thật (`fetch_my_trades`), tái tạo từng *vòng lệnh* theo khối
lượng có dấu (FIFO lot), rồi chỉ ghi bù vòng nào khớp được 1 `OPEN` trong journal
(cùng symbol/hướng/giá vào/qty/thời gian) mà chưa có `CLOSE`. R/PnL dùng đúng công
thức `trade_mgmt.trade_result` nên khớp định dạng bot ghi thật.

> Bài học 30/09/2026: cách ghép FIFO của monitor đã ghép **lệch** 11 `CLOSE` cho
> `OPEN` cũ hơn (journal khi đó thấy 18 "OPEN mồ côi"); reconcile dựa trên **fill**
> mới cho số liệu đúng. Sau ghi bù: **n = 46, PF ≈ 0.85** (trước đó tưởng 1.155) —
> đây là lý do gate vẫn chưa cho LIVE, và là lý do bot tự chạy reconcile ở boot.

Nguyên tắc an toàn:

- Bản ghi ghi bù đánh dấu `reconciled: true` + `recon_src: "exchange"` → lọc được.
- Vòng lệnh không có `OPEN` trong journal (lệnh tay của người dùng, ngoài cửa sổ
  fill) ⇒ **bỏ qua**, không đưa vào thống kê.
- Symbol còn vị thế mở trên sàn ⇒ bỏ qua (chưa đóng thì không ghi).
- Chạy lại nhiều lần không ghi trùng (backup 1 lần).
- Chỉ ghi log; **không** sửa `risk_state`/kill-switch, **không** gửi lệnh lên sàn.
- Boot (`turbo_demo.main`) tự chạy `RECONCILE_JOURNAL=true` (kể cả khi kill-switch
  đang ngưng), throttle `RECONCILE_MIN_INTERVAL_SEC=3600` để không gọi API liên tục
  khi supervisor spawn lại.

### Strategy gate: chặn setup thuộc strategy đang âm (không hạ ngưỡng entry)

Mục 15 tài liệu: *"một hệ thống PF tốt có thể che giấu strategy đang kéo hiệu suất
xuống"* → đo riêng từng nhóm setup (`logs/strategy_stats.json`) và **chặn nhóm âm**
bằng cách từ chối entry của nhóm đó (không sửa `MIN_ALPHA_SCORE`/`MIN_EDGE`, không
ảnh hưởng strategy khác).

```bash
# .env
STRATEGY_GATE=true     # false = tắt toàn bộ gate
STRAT_MIN_N=10         # AUTO: chỉ kết luận khi đủ mẫu
STRAT_AVG_R=0.10       # AUTO: avgR <= -0.10 + đủ mẫu -> chặn
STRATEGY_BLOCK=A_TREND_PULLBACK   # blocklist chủ động (cần bằng chứng backtest)
```

Hai tầng:

| Tầng | Điều kiện | Dùng khi |
|---|---|---|
| **AUTO** | `n ≥ STRAT_MIN_N` **và** `avgR ≤ −STRAT_AVG_R` (tự đọc `strategy_stats.json`) | Journal đủ mẫu → tự chặn, tự gỡ |
| **BLOCKLIST** | `STRATEGY_BLOCK` | Bằng chứng backtest rõ rệt nhưng journal **chưa đủ mẫu** |

Trạng thái 01/10/2026 — **A_TREND_PULLBACK bị đưa vào blocklist** vì âm bền qua
2 cửa sổ backtest độc lập (8 cặp, config LIVE hiện tại, file
`sweep_grid_30d_8sym.json` / `logs/strat_by_30d.txt`):

| Bằng chứng | A_TREND_PULLBACK | Nhóm khác |
|---|---|---|
| Journal testnet (sau reconcile) | n=3, avgR −0.59 (FIFO; `strategy_stats` n=3 sumR −0.14) | B n=6 +0.16, D n=7 +0.04, NONE n=28 −0.09 |
| Backtest 14 ngày × 8 cặp | n=162, avgR **−0.097**, net −78.9$ | B +0.172, D +0.061 |
| Backtest 30 ngày × 8 cặp | n=394, avgR **−0.056**, net **−113.75$** | B +0.102, D +0.026, NONE **+0.088** |

Bỏ A khỏi mẫu: 30 ngày còn lại sumR = +85.6R (1009 lệnh, E≈+0.085) — A chính là
nhóm kéo E(R) của hệ thống xuống. Gỡ chặn: xóa code khỏi `STRATEGY_BLOCK` (auto-gate
vẫn chặn lại khi `strategy_stats` đủ mẫu và âm). Monitor in dòng
`DA BI STRATEGY GATE chan o runtime` và **không** tính nó thành lý do chặn LIVE
(vì bot đã không mở lệnh mới nữa). Status log: `BLOCKED_STRAT`.

### Re-tune SL/TP: cửa sổ 30 ngày (chống overfit)

`python sweep.py` chỉ sweep 4 cặp/10 ngày → đã chạy lại **toàn bộ lưới 40 config
trên 8 cặp × 30 ngày** (file `logs/sweep_grid_30d_8sym.json`):

- **Config LIVE hiện tại (SL2.0/TP5.0/P0.3): rank #2/40**, PF 1.148, E +0.045,
  net +360$ → **giữ nguyên** (best còn lại 1.180 chênh trong noise, 2 config PASS
  đều SL2.5 nhưng PF thấp hơn).
- Kết luận: **không đổi SL/TP** — đổi cấu hình dựa trên cửa sổ ngắn là overfit.
  Re-tune lại sau khi journal đủ ≥50 lệnh thật (lúc đó chốt cho gate PF ≥ 1.2).

### 6b. Multi-AI agent (Phase 1: CHỈ CỐ VẤN — đang bật shadow)

Tầng `agents.py` cho phép nhiều "agent" (macro / critic / review) đưa **ý kiến**
`ALLOW | VETO | NO_OPINION` cho mỗi setup và sau mỗi lệnh đóng. **Phase 1 chỉ ghi
nhận** (`AGENTS_SHADOW=true`): quyết định vào journal dưới dạng `event=AGENT` để đo
lường, **không** đổi qty/SL/TP, không đặt/hủy lệnh, không chạm kill-switch.

```bash
python agents.py --selftest    # chạy thử offline (stub) — không cần key
python agents.py --stats       # ngân sách/chi phí/đã tối ưu + đếm AGENT trong journal
```

| Guardrail | Cơ chế |
|---|---|
| Chỉ cố vấn | `agents.py` không import `risk/portfolio/bot`; test `test_module_khong_the_doi_hanh_vi_trading` chặn hồi quy |
| Fail-open | Lỗi provider / JSON sai / hết ngân sách ⇒ `NO_OPINION`, không bao giờ ném lỗi vào vòng lặp |
| Trần chi phí | `AGENT_DAILY_CALLS` + `AGENT_DAILY_BUDGET_USD` (mặc định 200 call / 1$/ngày), lưu `logs/agent_state.json` |
| Circuit breaker | `AGENT_MAX_ERRORS` lỗi liên tiếp ⇒ tự TẮT agent (không spam log/API) |
| Cache | `AGENT_CACHE_SEC=900` — payload làm tròn nên cùng 1 nến = 1 cuộc gọi |
| Không rò dữ liệu | Payload chỉ có chỉ số thị trường (không số dư/key/vị thế) |

**Nhánh provider (Phase 2)** — `stub` (offline) đang chạy; các lựa chọn thật:

| `AGENT_PROVIDER` | Dùng gì để trả tiền | Cần chuẩn bị | Ghi chú |
|---|---|---|---|
| `copilot_cli` | **subscription Copilot** (AI credits của gói) — không cần API key | `npm install -g @github/copilot` + `copilot login` (hoặc `COPILOT_GITHUB_TOKEN` = PAT v2 quyền *Copilot Requests*) | Đường **chính thức** cho automation (docs: *"suitable for headless use such as automation"*); CLI chạy `-p` non-interactive, bot dùng `stdin=DEVNULL` + timeout nên không thể treo |
| `vscode_lm` | **subscription Copilot** qua VS Code | Mở `vscode_lm_bridge/` trong VS Code → lệnh *Copilot LM Bridge: Start server* | Dùng Language Model API chính thức (`vscode.lm`); VS Code phải đang mở; có rate-limit |
| `openai` / `anthropic` | API key trả theo token | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Ổn định nhất, dễ dự toán chi phí (gọi REST, không cần SDK) |
| `openai_compatible` | BYOK bất kỳ | `AGENT_COMPAT_BASE_URL` + `AGENT_COMPAT_MODEL` (+ key) | Azure/OpenRouter/Ollama/vLLM… (Ollama = 0đ nhưng máy này không GPU) |

> ⚠️ **Không** dùng endpoint nội bộ của extension Copilot Chat (`api.githubcopilot.com`)
> hay trích token của extension để gọi trực tiếp: đó không phải API công khai, vi phạm
> điều khoản Copilot và có thể bị khoá tài khoản. Hai đường hợp lệ để "mượn" gói
> Copilot là `copilot_cli` (CLI chính thức) và `vscode_lm` (Language Model API).

**Trạng thái Phase 2 (01/10/2026) — route `copilot_cli` đã CHẠY THẬT ✅**

Xác thực bằng `COPILOT_GITHUB_TOKEN` = PAT fine-grained quyền **Copilot Requests** (trong `.env`),
không dùng API key của OpenAI/Anthropic. Kết quả đo với CLI thật (GitHub Copilot CLI 1.0.90):

| Hạng mục | Kết quả |
|---|---|
| `python agents.py --doctor` | `[OK] da xac thuc` + provider sẵn sàng (tự xoá circuit breaker sau khi login) |
| 3 lượt thật | `macro VETO conf=0.72` · `critic VETO conf=0.65` · `review ALLOW conf=0.55` (nhận xét thật: *"đạt TP nhưng chỉ 0.62R — thấp hơn mục tiêu 2R"*) |
| Độ trễ | ~12–13s/lượt ⇒ vote chạy **luồng riêng**: `agent_vote_setup` trả về trong **0.001s**, vòng lặp trading KHÔNG bị chặn |
| Chi phí | ~$0.0004/lượt (ước lượng); trần `AGENT_DAILY_CALLS=50` + `AGENT_DAILY_BUDGET_USD=1.0` |
| Ổn định | 3/3 thành công, `errors=0`, không trip breaker, journal ghi `event=AGENT` |

Hai "bẫy Windows" đã gặp — đã sửa, đều có test chống hồi quy:

1. **`copilot.cmd` làm hỏng prompt JSON**: wrapper npm chuyển tiếp `%*` qua cmd.exe nên dấu `"` bị phá
   (model trả lời lan man thay vì JSON). *Sửa*: gọi thẳng `node …\npm-loader.js` qua
   `AGENT_COPILOT_BIN=node <npm prefix>\node_modules\@github\copilot\npm-loader.js`.
2. **`UnicodeDecodeError` (cp1252)**: CLI trả UTF-8 nhưng `subprocess` decode theo code page Windows ⇒
   hỏng cả lượt vote. *Sửa*: `encoding="utf-8", errors="replace"`.

Thêm nữa, `copilot` trên PATH là **shim** của extension (hỏi `Install GitHub Copilot CLI? (y/N)`) —
provider phát hiện shim, báo lỗi rõ, fail-open ⇒ bot không thể treo.

**Lộ trình lên quyền hành động:**

| Phase | Nội dung | Trạng thái |
|---|---|---|
| 1 | Shadow: ghi ý kiến, không đổi hành vi | ✅ xong (macro/critic/review, async, budget, breaker) |
| 2 | Provider thật (Copilot CLI) | ✅ xong — xác thực bằng PAT, model Auto → `claude-sonnet-5` |
| 3 | Agent phân tích → **đề xuất** chỉnh strategy, qua **gate tất định** | ✅ xong (`--reflect`, `--proposals`, `--apply`) |
| 4 | **Cấp quyền hành động** cho agent — chỉ khi có bằng chứng shadow | ✅ cơ chế xong, đang **khoá** (chưa đủ bằng chứng) |
| 5 | **Interlock LIVE** — chặn cứng khi sang tiền thật (`live_guard.py`) | ✅ xong (đã nối vào `turbo_demo.main()`) |

### Multi-AI ClinePass — 14 model cùng làm 1 việc (code/phân tích, KHÔNG dùng để trade)

`Multi_AI_Agent/` là harness: gửi **1 nhiệm vụ** cho **14 model ClinePass song song** (mỗi model 1 vai:
phân rã yêu cầu, phản biện logic, thiết kế API, ca kiểm thử, an toàn dữ liệu…) rồi **1 finalizer**
(`cline-pass/glm-5.3`) đọc tất cả báo cáo và tổng hợp thành `report.md`. Nó **không chạy code** và
**không tự sửa file** — kết quả là đề xuất để người dùng (hoặc Cline) triển khai.

Wrapper của dự án `clinepass_review.py` gom **dữ liệu thật của bot** làm context rồi gọi harness:

```bash
python clinepass_review.py --list                      # xem task/bundle có sẵn
python clinepass_review.py --task safety_audit --bundle safety      # mock (offline, 0 quota)
python clinepass_review.py --task code_review --file turbo_demo.py --provider clinepass --tg
python clinepass_review.py --task strategy_review --bundle strategy --group all
python clinepass_review.py --engine lab --mode consensus --task live_readiness --provider openai
```

| Thành phần | Ý nghĩa |
|---|---|
| `--task` | `code_review` / `strategy_review` / `safety_audit` / `live_readiness` (mẫu trong `tasks/*.txt`) |
| `--bundle` | gom dữ liệu bot: `bot_state` (journal + monitor + log) / `strategy` / `safety` (risk, agent votes) / `none` |
| `--engine` | `clinepass` (14 model) hoặc `lab` (`Multi_AI_Agent/main.py`, 4 chế độ group/handoff/parallel/consensus) |
| `--provider` | `mock` (**mặc định**, offline) · `clinepass` (cần `CLINE_API_KEY`) · `openai` (lab, cần key) |
| `--file` | thêm file context (lặp lại được), ví dụ `--file exchange.py --file bot.py` |
| `--tg` | gửi tóm tắt `report.md` lên Telegram |

- Kết quả: `logs/clinepass/outputs/clinepass_<ts>_<id>/report.md` (+ `run.json`, `events.jsonl`);
  bundle: `logs/clinepass/bundle_<kind>_<ts>.md` (đã bị `.gitignore` chặn).
- **Bí mật**: bundle **không bao giờ** chứa API key (có test khẳng định) và harness tự từ chối file
  `.env*`/`secret`/`credential`.
- **Giới hạn cần biết**: harness nhận ≤ 20.000 ký tự context (biến `CLINE_MAX_CONTEXT_CHARS`) và
  ≤ 6.000 ký tự nhiệm vụ; file context phải là `.py/.md/.txt/.json/.toml/.yaml/.yml/.csv`.
- Cài đặt: `python -m pip install -r Multi_AI_Agent/requirements-clinepass.txt` (httpx, dotenv).
  Engine `lab` cần thêm `-r Multi_AI_Agent/requirements.txt` (openai, pydantic).
  Kiểm tra harness còn nguyên vẹn: `cd Multi_AI_Agent && python -m unittest discover -s tests -t .`
  (31 test; trên Windows nên đặt `PYTHONUTF8=1` để đọc/ghi file UTF-8 đúng).
- **Một key dùng cho hai việc**: `CLINE_API_KEY` vừa chạy hội đồng 14 model, vừa có thể làm provider
  cho hội đồng trading nội bộ (`AGENT_PROVIDER=openai_compat` + `AGENT_COMPAT_*`, xem `.env.example`).

### Phase 3b/4b — Council: hội đồng 2 vòng + chủ toạ (01/10)

Ngoài macro/critic độc lập, bật `AGENTS_COUNCIL=true` để chạy **hội đồng** cho mỗi setup mới:

```
vòng 1: macro  → đọc dữ liệu thị trường
vòng 2: critic → đọc dữ liệu + Ý KIẾN CỦA MACRO ('peer') → đồng ý/phản đối
vòng 3: arbiter (chủ toạ) → đọc CẢ HAI ('council') → quyết định cuối
```

**Quy tắc quorum tất định** (`agents._final_from_council`, không phụ thuộc LLM):

| macro | critic | kết quả |
|---|---|---|
| VETO | VETO | **VETO** (đồng thuận chặn — chủ toạ không ghi đè được) |
| ALLOW | ALLOW | **ALLOW** (chủ toạ không chặn được đồng thuận cho phép) |
| VETO | ALLOW | **chủ toạ quyết** (`consensus=split`) |
| thiếu phiếu | — | chủ toạ quyết (`arbiter_only`) |

- Chạy thử ngay 1 phiên thật: `python agents.py --council-test SOL/USDT:USDT SHORT`
- Đo bằng chứng **riêng** cho hội đồng: `python agents.py --authority` in hai khối `[SETUP]` và
  `[COUNCIL]`; đổi nguồn cấp quyền veto bằng `AGENT_VETO_SOURCE=COUNCIL` khi khối COUNCIL đủ mẫu.
- `AGENT_TG_VOTES=true`: mỗi phiên hội đồng (không tính cache) gửi 1 tin Telegram:
  `🧠 COUNCIL SOL SHORT -> VETO (arbiter_only)` + ý kiến từng vai.
- Khi veto được cấp quyền, đường veto cũng dùng **hội đồng** nếu `AGENTS_COUNCIL=true`
  (macro+critic+chủ toạ, quorum tất định) thay vì 1 phiếu critic.
- Vẫn **shadow 100%**: hội đồng chỉ ghi journal + Telegram, không tự đổi qty/SL/TP/kill-switch.

### Phase 5 — interlock LIVE (không thể vô tình sang tiền thật)

Trước đây đổi `BINANCE_TESTNET=false` là bot chạy tiền thật ngay. Giờ **không thể**:
`turbo_demo.main()` gọi `live_guard.enforce()` TRƯỚC mọi vòng trade và **thoát** nếu chưa đủ điều kiện.

```bash
python live_guard.py        # checklist bất cứ lúc nào (không gọi sàn, không gọi LLM)
```

| Blocker | Ngưỡng |
|---|---|
| Xác nhận tay | `LIVE_CONFIRM=true` trong `.env` |
| Bằng chứng | `n(CLOSE) ≥ 50` **và** `PF(R) ≥ 1.2` (cùng nguồn với `monitor_report`) |
| Trần rủi ro | `MAX_TOTAL_RISK_PCT ≤ 2.0` |
| Đòn bẩy | `LEVERAGE ≤ 10`; **và** `≤ 8` nếu `PF < 1.5` |
| Kill-switch | phải sạch (không tripped) |

Trạng thái hiện tại (testnet): không chặn gì; nhưng nếu đổi sang LIVE **ngay bây giờ** sẽ bị chặn vì
`n=46/50`, `PF=0.852/1.2`, `risk=3%/2%` — tức là bạn buộc phải thu thập thêm dữ liệu trước.

### Phase 4 — quyền VETO có điều kiện (đang khoá, fail-safe)

```bash
python agents.py --authority        # kiểm tra đã đủ bằng chứng để cấp quyền chưa
# .env: AGENTS_VETO_ENABLED=true (mặc định false) để thực sự cho phép chặn lệnh
python agents.py --auto-apply       # (tuỳ chọn) tự áp dụng block/unblock — cần AGENT_AUTO_APPLY=true
```

**Điều kiện cấp quyền** (tất định, tính từ journal — không dùng LLM):
so khớp mỗi bản ghi `AGENT/SETUP` với lệnh đóng đầu tiên cùng symbol+hướng trong 48h, rồi so 2 nhóm:

| Điều kiện | Ngưỡng |
|---|---|
| Số lệnh nhóm VETO | `n_veto ≥ AGENT_VETO_MIN_N` (10) |
| VETO phải tệ hơn ALLOW | `avgR_veto ≤ avgR_allow − AGENT_VETO_MIN_GAP` (0.15R) |
| Chỉ chặn khi | `VETO` **và** `confidence ≥ AGENT_VETO_MIN_CONF` (0.7) |

Trạng thái hiện tại: `granted=False` (`n_veto=0/10`) ⇒ **bot không bị chặn lệnh nào bởi agent**.

**Bất biến an toàn** (đã test `tests/test_agents.py`, 346 test):
- Veto **chỉ được bỏ qua 1 lệnh** (giảm rủi ro). Không thể tăng size, đổi SL/TP, đóng lệnh, hay chạm kill-switch.
- Mọi lỗi/timeout/hết ngân sách ⇒ **fail-open**: lệnh vẫn được mở (`veto_decision` trả `block=False`).
- Mặc định `AGENTS_VETO_ENABLED=false`: kể cả khi đủ bằng chứng, phải bật tay mới có hiệu lực.
- Đường "đã cấp quyền → VETO chặn lệnh" có test tích hợp riêng, và ghi journal `status=VETO_ENFORCED` để đo lại sau này.
- `--auto-apply` mặc định tắt (`AGENT_AUTO_APPLY=false`) và chỉ áp dụng được `block/unblock` (kèm backup + audit `event=AGENT_APPLY`).

### Phase 3 — đề xuất chỉnh strategy (không tự áp dụng)

```bash
python agents.py --reflect          # 1 lượt: số liệu thật -> agent phân tích -> gate tất định
python agents.py --proposals 3      # xem đề xuất gần nhất (kèm trạng thái ACCEPTED/REJECTED)
python agents.py --apply 0 --yes    # áp dụng đề xuất #0 (CHỈ block/unblock; backup .env trước)
```

Cơ chế an toàn (đã test):

| Lớp | Chặn gì |
|---|---|
| `parse_proposals` | JSON sai/không đọc được ⇒ không có đề xuất nào |
| **Allowlist** | chỉ `block_strategy` / `unblock_strategy` / `watch_strategy` / `none`; target chỉ A/B/C/D |
| **Từ khoá cấm** | đề xuất chạm `risk/size/SL/TP/leverage/kill/margin` ⇒ **REJECT** |
| **Bằng chứng** | `block` cần `n ≥ REFLECT_MIN_N (20)` **và** `avgR ≤ −0.05`; `unblock` cần `avgR ≥ +0.05` |
| **Trần đề xuất** | tối đa 2 đề xuất được chấp nhận mỗi lần chạy |
| **apply** | chỉ nhận `block`/`unblock`; `dry-run` mặc định; ghi `.env` phải có `--yes` + tự tạo `.env.bak-*`; giữ nguyên CRLF |

Kết quả thật 01/10/2026 (`--reflect`, model Auto → `claude-sonnet-5`, 17.1s):
digest cho thấy A n=3 avgR −0.591, B n=6 +0.163, D n=7 +0.043, NONE n=30 −0.066 →
agent tự trả về `proposals: none` cho A (vì *"n=3 quá nhỏ, đã block sẵn"*) và
`watch_strategy` cho B ⇒ **không thay đổi cấu hình** — đúng tinh thần "chưa đủ bằng chứng thì không đụng".
Lượt `--apply` bị từ chối đúng thiết kế: *"type 'watch_strategy' khong duoc phep ap dung tu dong"*, `.env` hash không đổi.

> Ghi chú chi phí Copilot: mỗi lượt `copilot -p` = **1 premium request** + ~8 AIU + ~31k token
> cache-write (system prompt, không tái dùng giữa các tiến trình) ⇒ đặt `AGENT_DAILY_CALLS=10`
> (~300 premium request/tháng, vừa hạn mức Pro). Muốn tiết kiệm hơn thì chỉ chạy `--reflect`
> mỗi ngày một lần và để `macro/critic/review` chạy theo lệnh thật.

Đo lường: `python monitor_report.py` (P&L/WR) + đếm `AGENT` trong journal
(`count_agent_events`), đối chiếu nhóm `VETO` vs `ALLOW` trước khi cấp quyền.

## 7. Lớp an toàn bắt buộc trước khi LIVE (P0)

6 lỗi dưới đây đã được sửa (2026-09) vì **bản cũ có thể mất tiền thật** — chi tiết
trong `tests/test_p0_safety.py` (38 test):

| # | Vấn đề bản cũ | Cách sửa |
|---|---|---|
| P0-1 | Khởi động lại **quên vị thế đang mở** (`turbo_demo.py` chỉ `log.info` rồi bỏ qua) → mở trùng = gấp đôi risk, vị thế cũ mất quản lý | `position_sync.adopt()`: đọc vị thế thật + SL/TP đang treo → gán vào `portfolio`/`managed`; mốc 1R khôi phục từ `logs/managed_state.json` |
| P0-2 | **Kill-switch là dead code** trong runner thật (không có `bot.kill` nào trong vòng lặp) | Wire `kill.tripped` / `check()` / `register_close()` / `register_error()` vào `turbo_demo`; state lưu `logs/risk_state.json` → **restart KHÔNG xoá được lệnh ngưng** |
| P0-3 | Lỗi monitor → `_flatten()` rồi **vào lệnh mới ngay** | `_error` từ monitor ⇒ flatten + `break` (dừng hẳn), không mở lại |
| P0-4 | Không có idempotency; timeout mạng sau khi khớp ⇒ mở trùng | `clientOrderId` (`glow…`) cho MỌI lệnh + `position_qty()` kiểm tra vị thế thật trước khi kết luận thất bại |
| P0-5 | Không huỷ SL/TP treo cũ ⇒ 2–4 lệnh STOP/TP chồng nhau, có thể đóng nhầm vị thế MỚI | `cancel_symbol_orders()` TRƯỚC khi arm; đóng lệnh cũng dọn lệnh treo; partial re-arm theo qty còn lại |
| P0-6 | 4 vị thế × 1% = 4% > `MAX_DAILY_LOSS_PCT` 2%; DD tính trên `BALANCE_USDT` hardcode | `MAX_TOTAL_RISK_PCT` (trần risk danh mục, tính theo mốc 1R) + DD theo **equity thật đầu ngày** (`risk.note_equity`) |
| — | **Bot treo mà tiến trình vẫn sống** → supervisor không bao giờ restart, vị thế bị SL sàn đóng mà bot không biết | Heartbeat `logs/heartbeat.json` mỗi vòng + `WATCHDOG_SEC` (mặc định 180s): nhịp cũ ⇒ `taskkill` cây tiến trình + restart; mỗi vòng fetch có `ROUND_TIMEOUT_SEC` và `socket.setdefaulttimeout` |

Sau khi kill-switch trip, phải **kiểm tra nguyên nhân rồi mới mở lại**:

```bash
python risk.py             # xem logs/risk_state.json
python risk.py --reset     # xoá state -> cho phép trade lại
```

## 8. Chẩn đoán nhanh & hiệu năng IDE/AI

```bash
python positions.py            # "vị thế thật trên sàn" vs "lịch sử journal" vs managed_state
python positions.py --pair BTC # lọc 1 cặp
python live_guard.py           # điều kiện được phép sang LIVE (Phase 5)
python reconcile.py            # đối chiếu journal với FILL thật, ghi bù CLOSE thiếu
python telegram_report.py      # báo cáo trạng thái -> Telegram (--dry = chỉ in, --pair = 1 cặp)
python close_position.py --pair BTC/USDT:USDT --dry   # đóng vị thế MỞ TAY trên demo (bỏ --dry để chạy)
python arm_protection.py       # SL/TP trên sàn: xem trạng thái | --arm = thử đặt lại
python risk.py                 # kill-switch: xem state   |  --reset = mở lại
```

### Kill-switch: đọc sao cho khỏi nhầm

`logs/risk_state.json` **sống sót qua restart** (P0-2) — nghĩa là khi đã trip, bot **không**
tự mở lại dù sang ngày mới hay restart bao nhiêu lần. Điều dễ gây hiểu nhầm:

- `logs/turbo_err.log` có thể chứa **hàng nghìn dòng** `KILL-SWITCH dang NGUNG` — đó là log
  mỗi lần supervisor khởi động lại (mặc định 5 phút/lần), **không phải** số lần trip.
  Đếm đúng: chỉ dòng `ERROR KILL-SWITCH:` (không có chữ "dang NGUNG") mới là trip thật.
  `python telegram_report.py` in rõ cả hai con số này.
- Từ 2026-10-01, nếu **đang** bị chặn thì supervisor backoff dài hơn (600s → 1200 → 2400 → 3600,
  đổi bằng `SUPERVISOR_KILL_CAP_SEC`) thay vì restart mỗi 5 phút; muốn áp dụng phải khởi động
  lại supervisor (`taskkill /F /PID <pid trong logs/.supervisor.lock>` rồi `pythonw run_forever.py`).
- Muốn chạy lại: kiểm tra nguyên nhân (`python monitor_report.py`, `python risk.py`) rồi
  `python risk.py --reset`.

Ba nguồn dữ liệu **khác nhau hoàn toàn** — đừng nhầm khi đọc báo cáo:

| Nguồn | Ý nghĩa |
|---|---|
| `fetch_positions()` trên sàn | **Sự thật duy nhất** về vị thế đang mở |
| `journal.jsonl`: `OPEN` chưa ghép `CLOSE` | **Lịch sử ghi chép**, KHÔNG phải vị thế đang mở (dòng `journal-open(chua ghep)=N` của monitor là số này) |
| `logs/managed_state.json` | State bot dùng để quản SL/partial/trail; rỗng = bot không quản lý lệnh nào |
| Vị thế có trên sàn **nhưng không** có trong `managed_state` | **Vị thế mở tay** — bot bỏ qua (không SL/TP, không trailing) |

### Tăng tốc AI agent trong workspace này

**Đã dọn ngày 2026-10-01:** `memory-mcp/` (1.31 GB / 2244 file) và `memory-graph/` (84 MB) được
chuyển ra **`c:\Users\User\.vscode\Projects-vendor\`** — workspace còn **~62 MB / 616 file**
(trước: 1.4 GB / 2849 file). Nếu cần dùng lại 2 project đó, mở trực tiếp thư mục trong
`Projects-vendor\`; các lệnh trong `PREVIEW_README.md` phải trỏ tới đường dẫn mới.

Ngoài ra `.clineignore` + `.aiignore` (ở **gốc workspace**) chặn AI quét file rác/generated;
`autonomous-trading-bot/.gitignore` chặn `memory-mcp/`, `memory-graph/`, `logs/`, `*.db`,
`preview_*.svg`, `glow_map*.html`… khỏi repo. Muốn nhanh hơn nữa: mở **task mới** trong Cline khi
ngữ cảnh hội thoại đã dài (mỗi lượt trả lời phải đọc lại **toàn bộ** ngữ cảnh — đây là nguyên nhân
chính của "thinking rất lâu/treo").

### Kết luận sweep 01/10 (đọc trước khi mong đợi mốc LIVE)

- Cấu hình đang chạy `SL2.0_TP5.0_PARTIAL0.3_BE1.0_TRAIL1.0` là **tốt nhất trong 40 cấu hình** sweep:
  30 ngày × 8 cặp → n=1404, WR 68.2%, **PF 1.148**, net **+360**, DD 10.4% (`logs/sweep_grid_30d_8sym.json`).
- **Nhưng 14 ngày gần nhất chỉ PF 0.954 (net −46.7)** và journal live PF 0.899 ⇒ **edge không ổn định**;
  không cấu hình nào trong grid đạt PF ≥ 1.2 ⇒ **cổng LIVE đang chặn đúng**, đừng hạ ngưỡng.
- Đã bỏ **ETH** khỏi `SYMBOLS` (âm ở cả 2 cửa sổ: 30d −0.066R/171 lệnh, 14d −0.089R/75 lệnh).
  Bỏ ETH: 30d net +360 → +419, PF ~1.19. Muốn thử lại: thêm vào `SYMBOLS` rồi chạy `python sweep.py`.
- `SHORT` âm ở backtest (−0.02 / −0.10) nhưng **dương trên journal live (+0.03)** ⇒ chưa đủ bằng chứng
  để lọc theo hướng, giữ nguyên hai chiều.
- `MAX_TOTAL_RISK_PCT` đã hạ **3.0 → 2.0** (đúng chuẩn cổng LIVE, giảm trần rủi ro danh mục).

### SL/TP trên sàn bị chặn (`-4045`) — chuyện thật ngày 01/10

Binance **DEMO** có lúc trả `{"code":-4045,"msg":"Reach max stop order limit."}` cho **mọi** lệnh
stop (dù `GET /fapi/v1/openOrders` trả về `[]` — không có lệnh treo nào). Hệ quả: bot **không đặt
được SL/TP trên sàn**, vị thế chỉ được **bảo vệ bằng MONITOR phần mềm** (`bot._monitor` tự đóng khi
giá chạm SL/TP mỗi vòng) — chỉ an toàn khi bot đang chạy.

Cách nhận biết & xử lý:

```bash
python arm_protection.py           # vị thế nào có/không có SL/TP trên sàn
python arm_protection.py --arm     # thử arm lại (khi sàn cho phép trở lại)
python telegram_report.py          # cảnh báo này cũng được gửi vào Telegram
```

ADOPT khi không arm được sẽ log **ERROR** rõ ràng (`KHONG dat duoc SL/TP TREN SAN`, kèm `unarmed=[...]`)
và gửi Telegram, nhưng **không** coi là lỗi chết: vị thế vẫn vào `portfolio`/`managed` để monitor
phần mềm quản lý. Vì thế **đừng tắt bot** khi sàn đang chặn stop — tắt bot = mất luôn lớp bảo vệ.

**Tự "liền sẹo" (01/10):** demo trả `-4045` theo kiểu *hạn ngạch* (lúc cho, lúc chặn) nên:
- mở lệnh **không còn bị mất vị thế** khi arm lỗi (ghi sổ trước, arm sau — trước đây arm lỗi làm
  vòng lỗi và vị thế mồ côi: BTC short 0.0568 lúc 20:43);
- `_rearm_missing()` thử đặt lại SL/TP mỗi `PROTECT_RETRY_EVERY` vòng (mặc định 5, ~3–8 phút) và
  gửi Telegram khi thành công ⇒ không cần restart bot để có SL/TP trên sàn.

## 9. Cleanup

```bash
# dọn cache bytecode giữa các lần chạy test
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```
