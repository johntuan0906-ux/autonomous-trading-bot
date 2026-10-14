# CONTEXT.md — Ngữ cảnh hiện tại của dự án (đọc file này ĐẦU TIÊN)

> **Mục đích**: một chỗ duy nhất ghi *trạng thái + kiến thức đã kiểm chứng* của dự án, để khi mở lại VS Code / mở phiên chat mới (người hoặc AI) là **nhớ lại ngay**, không phải suy đoán lại.
> **Cập nhật lần cuối**: 12/10/2026 ~11:15 (sau khi ổn định quét 458 cặp trên 2 instance song song).
> **Quy tắc vàng**: mọi con số ở đây **có ngày** và **kèm lệnh tự kiểm chứng**. Số liệu hiệu suất thay đổi mỗi ngày → chạy lại lệnh ở §3 trước khi kết luận.

---

## 0. Khôi phục ngữ cảnh trong 60 giây (dành cho phiên AI mới)

**Đang chạy 2 instance SONG SONG** (từ 11/10): repo chính = **TESTNET** (demo, học), `../atb-live/` = **LIVE** (tiền thật ~19.7 USDT). Mỗi instance có `logs/`, `.env`, kill-switch RIÊNG; code dùng chung (sync bằng robocopy `*.py tools tests`). Cả hai quét **458 cặp** (nạp 522 → lọc sàn → ban BTC vĩnh viễn; danh sách trong `.env` `SYMBOLS` do `tools/apply_symbols.py` giữ, luôn trừ `logs/banned_pairs.json` của từng instance).

Đọc theo thứ tự: **CONTEXT.md (file này) → `OPERATIONS.md` (vận hành hằng ngày: 3 lệnh, shell, restart an toàn) → `STATE.md` → AGENTS.md → README.md mục 13–15 → `REPO_IDEAS.md` (9 repo tham khảo + việc áp dụng)**. Sau đó chạy:

```bash
python live_ready.py                 # còn thiếu cổng nào để sang LIVE
python monitor_report.py --days 7    # hiệu suất thật từ journal
python status.py                     # bot có sống? ví? vị thế? learner?
python agents.py --authority         # hội đồng AI đã có quyền chặn lệnh chưa
git log --oneline -10                # vừa thay đổi gì
python tools/apply_symbols.py --target both --dry-run   # xem danh sách cặp sẽ áp
```

Kiểm tra sức khoẻ vòng quét 458 cặp: đọc đuôi `logs/turbo_err.log` (mỗi instance) — không được có `FETCH_TIMEOUT`/`Connection pool is full`; `logs/heartbeat.json` phải tăng `round` mỗi ~300s.

---

## 1. Dự án là gì (1 đoạn)

Bot giao dịch **USDT-M Futures (Binance)** tự động trên Windows: vòng lặp `turbo_demo.py` quét 7 cặp → tính điểm tín hiệu (kỹ thuật + phái sinh + tin tức + learner) → đi qua các cổng an toàn **tất định** (risk, strategy block, learner score, urgent) → mở lệnh kèm SL/TP → `bot._monitor()` bảo vệ mỗi vòng. Ngoài ra có **hội đồng AI (LLM)** để *cố vấn* (chưa có quyền chặn lệnh) và **learner** học online trọng số từ kết quả thật.

## 2. Trạng thái hiện tại (12/10/2026 ~11:15 — số tự động xem `STATE.md`)

| Hạng mục | Giá trị | Ghi chú |
|---|---|---|
| Chế độ | **2 instance song song**: repo chính `BINANCE_TESTNET=true` (demo), `../atb-live` `BINANCE_TESTNET=false` (tiền thật ~19.7 USDT) | mốc tách `atb-live/logs/.split_ts`; code sync bằng robocopy |
| Cặp quét | **458 cặp**/instance (nạp 522 → lọc sàn → ban BTC vĩnh viễn) | `tools/apply_symbols.py --target both`; tôn trọng `logs/banned_pairs.json` |
| Vòng quét | `POLL_INTERVAL_SEC=300` (5 phút), `ROUND_TIMEOUT_SEC=280`, `SCAN_WORKERS=8` | 2 instance khởi động lệch ~90s để không chồng vòng 1 |
| Fetch | **cache OHLCV tăng dần** trong `exchange.py` (vòng đầu full; vòng sau chỉ ghep 8 nến; TF 1h+ TTL 900s; lỗi cooldown 120s) | hết `Connection pool is full`/`FETCH_TIMEOUT` nhờ cache + pool HTTP 32 |
| Kill-switch | LIVE: reset 12/10 ~10:50, baseline equity mới 19.70; TESTNET: reset ~11:05 (8 lệnh thua liên tiếp sáng 12/10 là thật, demo) | `risk.py --reset` chỉ có hiệu lực khi bot ĐÃ DỪNG (§6) |
| Vị thế LIVE | 0 vị thế mở trên sàn (12/10 ~11:00, `positions.py`) | các dòng OPEN cũ trong journal là lịch sử, không phải vị thế thật |
| `-4045` | **ĐÃ TÌM RA GỐC 12/10**: lệnh điều kiện ở **Algo Order API**, `fetch_open_orders` không thấy ⇒ re-arm mỗi 60s ⇒ **100 lệnh (TESTNET) / 200 (LIVE)** trùng lặp ⇒ chạm trần ⇒ `-4045` | đã vá `exchange.py` (`algo_orders`, `cancel_symbol_orders`, `fetch_protection`) + gom còn 1 SL/TP mỗi vị thế; xem `README §18.1`, `tools/orders_audit.py` |
| **Vị thế "bụi" mồ côi (LIVE, 13/10)** | Sau partial, phần còn lại nhỏ hơn minNotional ⇒ HEDGE mode không dùng được `reduceOnly` ⇒ sàn trả `-4164` ⇒ bot xoá khỏi sổ nhưng **vị thế VẪN nằm trên sàn, không SL/TP** (đo được: 1000PEPE/HYPE/ONDO trần) | đã vá: **bỏ qua partial nếu phần còn lại < minNotional** (`trade_mgmt.dust_notional`) + `_dust_close` **đọc lại vị thế thật**, nếu sàn vẫn giữ thì **giữ trong sổ + arm lại bảo vệ** (không bỏ rơi) |
| IP | `222.253.53.82` / `171.244.236.148` (dual-WAN) — đã whitelist đủ | không còn `-2015` |
| Hội đồng AI | 15 model; veto **KHÔNG được cấp quyền — đã đo dứt điểm 13/10 bằng luật `baseline`**: SETUP n_veto=57 avgR **+0.0210** vs baseline +0.0330 (gap **+0.012** — không phân biệt được); COUNCIL n_veto=33 avgR **+0.0717** vs baseline −0.0050 (gap **−0.077** = **NGƯỢC DẤU**, veto chặn nhầm lệnh tốt) | lý do thật: hội đồng trả **878 NO_OPINION** (model treo) nhưng chỉ **1 ALLOW** ⇒ luật cũ `n_allow≥10` là chờ vô định. Có **chốt chặn cứng** trong `agent_veto`: `gap_vs_baseline ≤ 0` ⇒ không bao giờ chặn. Đo lại: `python agents.py --authority --rule baseline` |
| **Vòng học (lessons) 13/10** | Bật `LESSONS_ENFORCE` cho **cả 2**: TESTNET ngưỡng `n≥20 & avgR≤−0.20`; LIVE `≤−0.15`. **Tác động đo thật** (`--impact`): TESTNET tránh **48.68 USDT** lỗ, LIVE tránh **62.46**, bỏ lỡ **0** | sinh lại: `python tools/learn_review.py --target live --impact`; đổi ngưỡng = sửa 1 dòng `.env` + restart |
| **Model local (13/10)** | **Đã chuyển sang llamafile** (không daemon): binary thin `llamafile-0.10.6-thin.exe` + `Llama-3.2-3B-Instruct-Q4_K_M.gguf` (1.9 GB), server `http://127.0.0.1:8080/v1`. Cả 2 instance: `AGENT_COUNCIL_LOCAL=llama3.2-3b-local` | bật: `python tools/llamafile_setup.py --start`; tắt: `--stop`; đổi về Ollama: `python tools/switch_local_model.py .env ollama`. Lưu ý: binary THIN phải dùng `--model` (không phải `-m`) |
| **Cầu dao agent (13/10)** | **LỖI THIẾT KẾ ĐÃ SỬA**: `AgentBudget` dùng **1 file state chung** → 5 lỗi liên tiếp từ Copilot (hết quota tháng) đã `disable` **TOÀN BỘ** tầng agent ⇒ **mọi provider** (cline-pass miễn phí, local) bị chặn suốt ngày ⇒ hội đồng im lặng (đo 48h: 328 bản ghi, **0 VETO / 0 ALLOW**) | nay cầu dao **theo từng provider** (`errors_by`/`disabled_by`); gỡ tay: `python agents.py --reset-budget`. Đã gỡ cho cả 2 instance |
| **Hội đồng: nguyên nhân còn lại 13/10** | Gateway ClinePass **còn sống** (`GET /api/v1/models` OK, 462 model) nhưng **id đã đổi**: id cũ trong dự án `cline-pass/glm-5.3` bị **HTTP 500**, trong khi id thật `anthropic/claude-haiku-5.5` chạy OK ⇒ 12/14 model hội đồng chết vì **alias lệch**, không phải hết quota | cần map lại alias → id gateway (`Multi_AI_Agent/models.clinepass.json` + `clinepass.py` gửi nguyên văn) hoặc dùng đường `AGENT_COMPAT_*` (OpenAI-compatible) với id hợp lệ |
| **Ngưỡng lessons 13/10** | Quét ngưỡng (`learn_review --sweep`): **−0.05** tiết kiệm 82.33 (TESTNET) / 62.46 (LIVE) mà **bỏ lỡ 0** ⇒ siết từ −0.20/−0.15 về **−0.05** cả 2 instance | xem lại mỗi tuần: `python tools/learn_review.py --target live --sweep` |
| **Adopt định kỳ 13/10** | `ADOPT_EVERY_ROUNDS=10`: cứ 10 vòng đọc lại vị thế thật, dọn entry "ma" + huỷ lệnh mồ côi | trước đây chỉ adopt lúc khởi động ⇒ LIVE giữ `BNB` trong `managed` khi sàn đã đóng |
| Kill-switch trip là THẬT | 08 lệnh thua liên tiếp 12/10 (AAVE r=-1.15, FLOKI -1.35, MOG -1.42, PEPE -1.37…) đúng thiết kế | sau reset, nếu thị trường tiếp tục xấu sẽ trip lại — đó là đúng ý |

Lệnh kiểm tra nhanh: `python _chk.py` → `logs/chk_out.txt` (script tạm, xoá sau khi ổn định); chính thức dùng `python status.py` + `python positions.py` (mỗi instance).

## 3. Hiệu suất hiện tại (đọc từ `logs/journal.jsonl`, ngày 09/10 ~00:10)

```
CONG HOAN THANH TESTNET -> LIVE | n_toan_bo=301/300 | PF(R)=1.616 | PF($)=1.492
  7 ngay    223  67.7%  PF(R)=1.935  PF($)=1.834  E(R)=+0.1471  PnL=+273.21$
  14 ngay   278  66.6%  PF(R)=1.573  PF($)=1.434  E(R)=+0.1076  PnL=+217.67$
  30 ngay   301  67.1%  PF(R)=1.616  PF($)=1.492  E(R)=+0.1178  PnL=+272.77$
VERDICT: HOAN THANH  (khong con cong nao bi chan)
```

⚠️ **Đây là số của tài khoản DEMO** — đừng kết luận "có lãi thật" từ bảng này (xem §5).

Làm mới: `python live_ready.py` · `python monitor_report.py --days 7` · `python monitor_report.py --days 14`.

---

## 4. Cổng LIVE và quy trình sang tiền thật

**Cổng 1 — `live_guard.py`** (tự chạy trong bot, chặn cứng): n≥50 · PF≥1.2 · `MAX_TOTAL_RISK_PCT`≤2% · `LEVERAGE`≤10 · kill-switch sạch · **`LIVE_CONFIRM=true`**.

**Cổng 2 — `live_ready.py`** (chặt hơn, chạy tay mỗi ngày): PF(R)≥1.2 **và** PF($)≥1.1 ở **mỗi** cửa sổ 7/14/30 ngày · n≥300 · risk/lev như trên · chiến lược có n≥10 & avgR≤−0.10 phải nằm trong `STRATEGY_BLOCK` · mỗi hướng LONG/SHORT ≥5 lệnh.

**Quy trình khi đạt**: sửa `.env` → `BINANCE_TESTNET=false` + `LIVE_CONFIRM=true` → restart bot. 20–30 lệnh LIVE đầu nên hạ `RISK_PER_TRADE_PCT=0.25–0.5` và `MAX_POSITIONS=3` để tự đo edge bằng tiền thật với rủi ro nhỏ.

---

## 5. Kiến thức đã kiểm chứng (không phải suy đoán) + giới hạn

1. **Hội đồng AI chưa từng chặn lệnh nào**: `BLOCKED_VETO = 0` trong toàn bộ log; quyết định ghi `[shadow]`. Cổng chặn lệnh thật đều tất định: `BLOCKED_STRAT=1651`, `BLOCKED_LEARN=782`, `BLOCKED_URGENT=16`.
2. **Đã vá lỗ hổng cấp quyền veto (08/10)**: trước đây chỉ cần **1 lệnh ALLOW** là đủ để "chứng minh VETO tệ hơn" ⇒ `[COUNCIL]` từng `granted=True` với `n_allow=1`. Nay đòi **cả hai nhóm** (`AGENT_VETO_MIN_ALLOW=10`). Sau khi sửa: `[COUNCIL] granted=False (n_veto=33/10, n_allow=1/10)` — khớp thực tế. Test chốt: `TestPhase4Authority::test_khong_cap_quyen_khi_thieu_mau_ALLOW`.
3. **`learner.py` KHÔNG phải deep learning**: logistic tuyến tính trên 20 feature, cập nhật trọng số theo thắng/thua, lưu `logs/learner.json` (docstring cũ ghi "deep-learning dạng nhẹ" — đã sửa).
4. **Sizing thật** (đo 100 lệnh gần nhất: SL trung vị **0.84%**, TP 2.11%, R:R 2.5): với risk 1% → notional ≈ **1.19× vốn/lệnh**, margin 8x ≈ **14.8% vốn/vị thế**, 4 vị thế ≈ **59% vốn làm margin** ⇒ phải chừa đệm margin.
5. **Notional tối thiểu thật của sàn** (tra ccxt, USDT-M): BTC **50$**, LINK **20$**, SOL/XRP/DOGE/ADA/AVAX **5$** ⇒ vốn nhỏ có thể không đặt được BTC.
6. **Bot tự `flatten + dung` khi monitor lỗi API** (đã xảy ra 2 lần tối 08/10) — thiết kế an toàn; trên LIVE sẽ tốn phí/slippage thật.
7. **Giới hạn phải nhớ**: số liệu là **demo** (fill lý tưởng); backtest dài hạn (sweep 01/10) chỉ **PF 1.148**, 14 ngày **0.954** ⇒ edge **chưa ổn định**; **không ai đảm bảo lợi nhuận**.
8. **Muse Code**: tài khoản hiện tại không đăng nhập được (`credential.login outcome="mint_failed"` 4/4 lần) vì chưa nạp credit ⇒ đã **tắt khỏi hội đồng**; muốn bật lại cần API key (`muse auth set` hoặc `META_API_KEY`). Chi tiết: README §10.1, §12.
9. **GitHub**: repo `git@github.com:johntuan0906-ux/autonomous-trading-bot.git`, SSH key `~/.ssh/id_ed25519` đã hoạt động; đẩy code bằng `tools\git-sync.cmd "msg"` (commit + push, chạy ngoài sandbox).

---

## 6. Vận hành (lệnh hay dùng)

| Việc | Lệnh |
|---|---|
| Sức khoẻ 2 instance (1 lệnh) | `python tools/ops.py` |
| Restart an toàn (dừng→reset→chạy) | `python tools/restart_bot.py --target both --reset --wait-flat` |
| Chọn/nạp danh sách cặp | `python tools/pick_symbols.py --target live --top 40` → `python tools/apply_symbols.py --target live` |
| Bot có sống? | `python status.py` (xem `supervisor lock pid=…`) |
| Xem vị thế thật trên sàn | `python positions.py` |
| Đối soát journal ↔ sàn | `python reconcile.py` |
| SL/TP có trên sàn chưa | `python arm_protection.py` (`--arm` để thử đặt lại) |
| Reset kill-switch | `python risk.py --reset` |
| Chạy lại bot | `pythonw run_forever.py` (chạy từ thư mục project) |
| Test toàn bộ | `python -m unittest discover -s tests` (hiện **555 test OK**) |
| Đẩy code lên GitHub | `tools\git-sync.cmd "mo ta thay doi"` |

⚠️ Khi sàn đang chặn SL/TP (`-4045`): **đừng tắt bot** — tắt là mất luôn lớp monitor mềm.

⚠️ **Gotcha kill-switch (09/10)**: `python risk.py --reset` **chỉ có tác dụng khi bot đã DỪNG** — bot đang chạy sẽ **ghi lại state cũ** (tripped=true) ngay sau đó vài giây ⇒ reset trơ, bot vẫn bị chặn. Quy trình đúng:

```bash
# 1) dung bot (kill supervisor + tien trinh con)
# 2) python risk.py --reset        -> "reset: True", logs/risk_state.json bi xoa
# 3) chay lai: pythonw run_forever.py
# => start_equity moi = equity hien tai -> ngan sach lo ngay 2% duoc cap lai
```

---

## 7. Bản đồ file quan trọng

| File | Việc gì |
|---|---|
| `turbo_demo.py` | vòng lặp chính, mở lệnh, `agent_authority_cached`, `agent_veto` |
| `bot.py` | quản lý vị thế, `_monitor()` (SL/TP/BE/trail), re-arm SL/TP, dọn dust |
| `strategy.py` | 3 chiến lược + `gate_check` (STRATEGY_BLOCK) |
| `indicators.py` / `derivatives.py` / `sentiment.py` | tín hiệu kỹ thuật / OI-funding-liquidations / tin tức RSS |
| `learner.py` | 20 feature + trọng số học online (`logs/learner.json`) |
| `agents.py` | hội đồng LLM, `agent_authority()`, `veto_decision()`, CLI `--authority/--ab-report/--eval-dataset` |
| `risk.py` / `portfolio.py` / `live_guard.py` / `live_ready.py` | rủi ro, danh mục, cổng LIVE (cứng / chặt hơn) |
| `journal.py` + `logs/journal.jsonl` | sổ mọi lệnh OPEN/CLOSE (có `feats`, `news_score`, `strategy`) |
| `monitor_report.py` | báo cáo WR/PF theo cửa sổ, đọc từ journal |
| `run_forever.py` | supervisor (tự restart, backoff, watchdog nhịp tim) |
| `tools/` | `muse.cmd`, `muse-nosandbox.cmd`, `git-sync.cmd` |
| `AGENTS.md` / `.clinerules` / `.github/copilot-instructions.md` | luật cho AI agent trong workspace |
| `README.md` | tài liệu đầy đủ theo mục 1→14 (mục 14 = kiểm chứng & giới hạn) |
| `CONTEXT.md` | **file này** — trạng thái hiện tại, đọc đầu tiên |
| `STATE.md` | **tự động sinh** bởi `state_sync.py` (số liệu mỗi 30 phút; ĐỪNG sửa tay) |
| `state_sync.py` | đồng bộ `STATE.md` + push GitHub + tự động sang LIVE (§11) |
| `check_live_key.py` | kiểm tra cặp key LIVE trong `.env` (đọc số dư THẬT, chỉ đọc) — §16 |
| `loss_report.py` | phân tích lỗ theo 7 chiều + đề xuất cụ thể — §17 |
| `restart_when_flat.py` | restart bot khi đã HẾT vị thế (an toàn, fail-safe) — §19.1 |
| `market_brief.py` | bản tin: tin tức + sentiment + bối cảnh + vì sao chưa vào lệnh + bot học được gì — §19.2 |

---

## 8. Việc đang mở / tiếp theo

- [x] **Đủ n≥300** (n=301) → `live_ready.py` = `HOAN THANH` (09/10 00:07).
- [x] **Sang LIVE thực chiến (11/10)**: 2 instance song song, `../atb-live` dùng key thật (~19.7 USDT), risk 0.5%, `MAX_POSITIONS=2`.
- [x] **Mở rộng lên 458 cặp** (12/10): cache OHLCV tăng dần, pool HTTP 32, SCAN_WORKERS=8, POLL 300s, SKIP_VOL/SKIP_DATA, ATR BTC cho kill-switch toàn cục, ban BTC vĩnh viễn (`pair_audit.py`).
- [x] **Sửa hạ tầng quét nhiều cặp**: `Connection pool is full` → pool 32; `FETCH_TIMEOUT` → cache tăng dần + cooldown lỗi 120s; `atr_levels` data xấu → SKIP_DATA; watcher chỉ đếm cặp của bot.
- [ ] Theo dõi LIVE: kill-switch trip 12/10 10:45 (daily loss 2.17% — PnL realized hôm trước, không phải lệnh mới); nếu 458 cặp gây thua lỗ liên tiếp trên LIVE, cân nhắc thu hẹp danh sách LIVE.
- [ ] Theo dõi `-4045`: **12/10 đã tìm ra gốc = lệnh điều kiện trùng lặp tích tụ ở Algo Order API** (đã vá `exchange.py` + gom còn 1 SL/TP mỗi vị thế). Kiểm tra định kỳ: `python tools/orders_audit.py --target live` — kỳ vọng **= 2 × số vị thế đang mở**; nhiều hơn ⇒ `--dedupe`.
- [ ] (tuỳ chọn) Bật veto thật cho hội đồng khi có đủ bằng chứng **cả 2 nhóm** (`python agents.py --authority` phải `granted=True`), rồi `AGENT_VETO_SOURCE=COUNCIL`.
- [ ] (tuỳ chọn) Muse: nạp credit → tạo API key → `muse auth set` → điền lại `AGENT_COUNCIL_MUSE_CLI`.
- [ ] (tuỳ chọn) I/O offload: ghi journal async, Telegram ở thread riêng.
- [ ] Dọn script tạm (`_chk.py`, `_g.py`, `_run_test.py`, các log `logs/*_out*.txt`) sau khi ổn định.

---

## 9. Thay đổi gần đây (git log)

| Commit | Ngày | Nội dung |
|---|---|---|
| `ee25859` | 08/10 23:32 | Vá cấp quyền veto (đòi đủ 2 nhóm) + docstring learner + README §14 |
| `5d753a0` | 08/10 16:26 | Thêm `live_ready.py` (cổng HOÀN THÀNH TESTNET) + 13 test |
| `b5a5391` | 08/10 16:11 | Verify sandbox Windows (owner `ProgramData\muse` → Administrators) |
| `4b9babc` | 08/10 16:03 | Bỏ **hoàn toàn** Muse khỏi hội đồng → còn 15 model |
| `8795fa7` | 08/10 15:47 | Sandbox setup + quyền `ProgramData\muse` |
| `7b1b39f` | 08/10 15:27 | Nối GitHub (SSH) + 3 script trong `tools/` |

---

## 10. Giữ file này luôn đúng (quan trọng)

- **Sửa gì đáng nhớ → cập nhật CONTEXT.md trong cùng commit đó** (nhất là §2 trạng thái, §5 bài học, §8 việc mở).
- Số liệu hiệu suất: **đừng chép số mới vào đây mỗi ngày** — chỉ cần ngày + lệnh làm mới; số cũ để nguyên làm mốc lịch sử.
- Nếu thấy điều gì **trái với file này** ⇒ tin **bằng chứng chạy được**, rồi **sửa file này**.

---

## 11. (09/10) Tự động hoá: bộ nhớ dự án + tự sang LIVE

| Việc | Cơ chế |
|---|---|
| **Bộ nhớ tự cập nhật** | `run_forever.py` gọi `state_sync.py --git --auto-live` mỗi `STATE_SYNC_SEC` (mặc định 1800s = 30 phút). Mỗi lần: sinh `STATE.md` (+ `logs/state_snapshot.json`) → `git add STATE.md` → commit → push nhánh hiện tại |
| **Tự sang LIVE** | 5 chốt: `AUTO_LIVE_ARMED=true` · `live_ready` OK · `live_guard` OK · **ví THẬT ≥ `AUTO_LIVE_MIN_EQUITY`** · chưa đổi lần nào (marker `logs/.live_flipped`) |
| **Khi đổi** | `.env`: `BINANCE_TESTNET=false`, `LIVE_CONFIRM=true`, `RISK_PER_TRADE_PCT=0.5`, `MAX_POSITIONS=3` (khởi đầu an toàn) + backup `.env.bak-live` + Telegram + ghi `STATE.md` → kill tiến trình con để supervisor restart với config mới |
| **Chạy tay** | `python state_sync.py` · `python state_sync.py --git` · `python state_sync.py --git --auto-live` |
| **Tắt tự động** | `.env`: `STATE_SYNC_SEC=0` (tắt sync) · `AUTO_LIVE_ARMED=false` (tắt tự sang LIVE) |

**Bug thật đã gặp & đã sửa (09/10 00:05)**: process do supervisor spawn (pythonw) **không chạy được** `subprocess.run(["git", ...])` → `[WinError 2]` dù `shutil.which("git")` tìm thấy ⇒ nay dùng **đường dẫn tuyệt đối** (`state_sync._git_bin()`, có test).

### 11.1 Ngưỡng rủi ro theo **ví THẬT** (dải 4 mức — `risk_tier.py`)

Khi sang LIVE, `state_sync.py` **áp mức theo số dư thật** và **tự lọc cặp theo min notional thật**:

| Equity thật (USDT) | Mức | risk/lệnh | MAX_POSITIONS | Cặp (sau khi lọc) | Notional/lệnh |
|---|---|---|---|---|---|
| `< 20` | **giảm lệnh** | 1.0% | **1** | SOL/XRP + ADA/DOGE/AVAX | ~8–16$ |
| `20 .. < 62` | **cân bằng** | 0.5% | **2** | SOL/XRP + alts (**LINK từ ~50$**) | 8–25$ |
| `62 .. < 100` | **cân bằng + BTC** | 1.0% | **2** | **+ BTC** (đủ min notional 50$) | 50–80$ |
| `>= 100` | **an toàn** | 1.0% | **4** | đủ (BTC + LINK) | ≥80$ |

- **Ngưỡng BTC** (min notional 50$): cần equity ≥ **62$** ở risk 1% (mức "cân bằng + BTC"), hoặc ≥ **124$** ở risk 0.5% ⇒ đó là lý do mức 62–100 dùng risk **1%** (để BTC vào được).
- **Lọc cặp tự động**: `notional = equity × risk% / SL(1.24%)` so với min notional từng cặp (BTC 50$, LINK 20$, alt 5$) ⇒ cặp chưa đủ bị **loại khỏi danh sách** (không để sàn từ chối lệnh).
- Ngưỡng tự sang LIVE: **`AUTO_LIVE_MIN_EQUITY=10`** (từ 10$ đã vào được lệnh alt với 1 vị thế).
- Xem trước: `python risk_tier.py 15` (giảm lệnh) · `python risk_tier.py 70` (có BTC) · `python risk_tier.py 150` (an toàn).
- Số liệu gốc: `logs/money_probe.py` (min notional ccxt + SL trung vị 1.24% + `risk.position_size` thật).

---

## 12. (09/10) Bài học từ phân tích lỗ — các việc cần quyết

Chạy `python loss_report.py` (chi tiết: README §17). Kết quả trên n=360 lệnh (tổng R +23.49 · tổng R âm 78.52):

| Phát hiện | Số liệu | Trạng thái |
|---|---|---|
| **BTC** = nguồn lỗ lớn nhất | n=68 · avgR −0.064 · **28% tổng lỗ** | ⏳ **chờ bạn quyết**: bỏ khỏi `SYMBOLS` (như đã bỏ ETH 01/10) |
| **D_RANGE_REVERSAL** âm rõ | n=24 · avgR **−0.190** | ✅ runtime auto-gate đã chặn (`STRATEGY_GATE=true`) |
| **FLATTEN** (đóng vị thế cưỡng bức do lỗi API) | n=81 · **25–38% tổng lỗ** | ⏳ xem tần suất `api errors` (nguồn: sàn demo chập chờn) |
| **Giữ lệnh > 8 giờ** | n=52 · avgR −0.076 · 19% lỗ | ⏳ cân nhắc max-hold (cần thêm code) |
| **SL** chiếm 64% số lần thoát | avgR +0.022 (gồm chốt lãi sau dời SL) | ⏳ cân nhắc nới SL (ATR) |
| **B_BREAKOUT_RETEST** tốt nhất | n=85 · WR 76.5% · avgR **+0.239** | 💡 nên ưu tiên |
| **COMPRESSION** chiếm 60% số lệnh | avgR +0.016 nhưng **67.8% tổng lỗ** | ⏳ cân nhắc siết ngưỡng vào lệnh |

**Nguyên tắc**: bot **KHÔNG** tự sửa config — đề xuất chỉ để bạn quyết; mọi thay đổi đi qua `.env` + restart bot.

---

## 13. (09/10) Key LIVE đã điền — và bẫy lỗi `-2015` do IP

Trạng thái: `BINANCE_LIVE_API_KEY`/`_SECRET` **đã điền** (64 ký tự, che dạng `K3IP20…DobC`). Đọc được ví THẬT: **21.96 USDT** ⇒ mức **`balanced`** (risk 0.5% · 2 vị thế; cặp SOL/XRP + ADA/DOGE/AVAX).

Nhưng: **đọc được NGẮT QUÃNG (2/6 · 3/5 · 1/5 lần)** với `-2015 Invalid API-key, IP, or permissions`.

**Bằng chứng quyết định (cùng key, cùng lúc)**: request ra bằng IP `171.244.236.148` → **OK** (đọc 21.99 USDT); request ra bằng `222.253.53.82` → **-2015** (Binance nêu đúng IP này trong message). ⇒ **key/secret/quyền ĐÚNG**, chỉ **IP bị chặn**: whitelist của key **thiếu `222.253.53.82`**. Máy có **2 đường ra Internet** (2 WAN/cân bằng tải) nên ~50% request đi nhầm đường; ipify và Binance có thể thấy IP khác nhau cho cùng 1 thời điểm.

**Việc cần làm (Binance side)**: API Management → key → **Edit restrictions** → **TẮT** *"Restrict access to trusted IPs only"* (khuyến nghị — không có IP tĩnh thì whitelist sẽ lỗi tiếp) hoặc thêm **cả** `222.253.53.82` **và** `171.244.236.148`; tick đủ *Enable Reading* & *Enable Futures* → Lưu → đợi 1–2 phút.

**Đã cải thiện code** (để lần sau chẩn đoán trong 10 giây):
- `exchange.fetch_balance_usdt` **ghi lại mã lỗi thật** vào `last_error` (trước đây nuốt lỗi ⇒ log chỉ có "không doc duoc").
- `exchange.request_ip_from_error()` — lấy **IP mà Binance thấy** trong message `-2015`.
- `state_sync.real_equity_health(cfg, tries=5)` — đọc ví **5 lần**, trả `ok_n/tries/stable`; **chốt 4b**: `decide_go_live(..., key_stable=...)` **CHẶN sang LIVE khi key không ổn định** (≥4/5 = 80%). Đo thực tế: **1/5 ⇒ CHẶN** — nếu không có chốt này, chỉ cần 1 lần đọc được là bot đã tự sang LIVE với key lỗi ~75% (rất nguy hiểm: không đặt được SL).
- `state_sync.last_live_error()` + ghi mã lỗi vào `logs/state_sync.log`.
- `check_live_key.py`: đọc 5 lần (`x/y lần thành công`) + **bảng theo từng IP** (`ip_diag`) + **IP mà Binance TỪ CHỐI** (lấy từ message `-2015`, chính xác hơn ipify vì máy đổi đường ra giữa 2 lần gọi) + cảnh báo IP đã đổi; `--retry N`, `--json` (kèm `by_ip`/`rejected`); exit 2 nếu key không ổn định.
- README **§16.3** ghi lại toàn bộ sự cố + cách sửa. Tests: **612 OK** (thêm `tests/test_check_live_key.py` 7 test).

---

## 15. (09/10) Chế độ "theo dõi & học" — watcher + bản tin

Yêu cầu: **KHÔNG restart khi đang mở vị thế**; chỉ restart khi **hết vị thế**; trong lúc đó **theo dõi + học + cập nhật tin tức** để vào lệnh.

- **`restart_when_flat.py`** (đang chạy nền, PID trong `logs/restart_when_flat.log`): 30s/lần đọc vị thế THẬT; khi **0 vị thế** ⇒ kill supervisor + chạy lại `run_forever.py` (áp code mới). Đọc sàn lỗi ⇒ không restart (fail-safe). Xem README §19.1.
- **`market_brief.py`**: bản tin 5 phần — tin tức/sentiment (RSS, không cần key) · bối cảnh từng cặp (giá/ATR/regime/funding/OI) · vị thế & rủi ro · **vì sao chưa vào lệnh** (vòng quét cuối) · **bot học được gì** (`logs/learner.json`). Xem README §19.2.
- Trạng thái 09/10 20:45 (LIVE): equity **22.88 USDT** (từ 22.11 lúc sang LIVE), 5 vị thế (~39 USDT notional), tất cả cặp `COMPRESSION` (AVAX `BREAKDOWN`), learner n=189 (`sent +0.517`, `retest +0.421`, `htf −0.571`, `macd −0.398`).

---

## 16. (11/10) CHẠY SONG SONG TESTNET + LIVE (2 instance, hội đồng quyết định)

Yêu cầu: vừa TESTNET để học vừa LIVE để thực tế nhanh hơn; **hội đồng AI** chọn phương án phù hợp nhất.

- **2 instance, `logs/` RIÊNG** (journal/learner/risk_state/heartbeat dùng chung ⇒ ghi đè lẫn nhau, hỏng số liệu):
  - Repo chính `autonomous-trading-bot/` = **TESTNET** (demo key, 7 cặp, risk 1.0%, `MAX_POSITIONS=4`, `MIN_PF=1.2`)
  - `../atb-live/` = **LIVE** (key thật, 5 cặp, risk **0.5%**, `MAX_POSITIONS=2`, `MIN_PF=1.05`/`MIN_TRADES=30`, git local riêng — không đụng GitHub)
  - Ghi lại cấu hình: `python tools/setup_parallel_env.py`; **mốc tách** `atb-live/logs/.split_ts`
- **`compare_modes.py`**: bảng so sánh 2 chế độ (chỉ tính lệnh **sau mốc tách**) + **quy tắc tất định** + **hội đồng AI tư vấn** (5 phương án); `--apply` ghi vào `.env` LIVE trong **trần cứng** (risk 0.25–1.0%, max_positions 1–3).
- **`MIN_PF`/`MIN_TRADES` nay cấu hình được qua `.env`** (mặc định 1.2/50) ⇒ mỗi instance ngưỡng riêng.
- Trạng thái 11/10 00:50: TESTNET equity **4290** (demo) · LIVE **21.59** với 4 vị thế (ADA/DOGE/SOL của bot + `1000RATS` mở tay). 666 tests OK.

---

## 14. (09/10) ĐÃ SANG LIVE + 5 lỗi LIVE-only đã sửa (xem README §18)

**Trạng thái hiện tại**: bot chạy **LIVE** từ 16:35:47 (`.env`: `BINANCE_TESTNET=false`, key LIVE, risk 0.5% · `MAX_POSITIONS=2` · SOL/XRP+ADA/DOGE/AVAX). Sau ~3.5h: equity **22.11 → 22.6 USDT**, các lệnh đóng đều `r` dương (soft-SL chốt lãi: AVAX `r=+0.82`, SOL `r=+0.48`).

**5 lỗi LIVE-only đã sửa (đều có test)**:
1. **Con chạy config cũ**: `run_forever.child_env()` đọc lại `.env` mỗi lần spawn (trước: `Popen` kế thừa env lúc supervisor start ⇒ `.env` LIVE nhưng bot vẫn demo, heartbeat `equity=4348`).
2. **Kill-switch trip oan khi đổi chế độ**: `risk.KillSwitch.mode` — DEMO↔LIVE ⇒ mốc lại DD (`note_equity(mode=...)`); đã gặp `daily loss 99.49%` do mốc demo 4355 vs equity LIVE 22.
3. **HEDGE mode**: `exchange.hedge_mode()` tự dò; gửi `positionSide`, KHÔNG gửi `reduceOnly` (hedge trả `-1106`). Trước đó mọi lệnh `-4061`.
4. **"Vị thế ma"**: `position_sync.adopt()` dọn cả `bot.portfolio` (chỉ xoá khi sàn xác nhận `qty=0`; lỗi đọc ⇒ giữ).
5. **Test phụ thuộc `.env`**: `test_bot`, `test_live_guard` tự set config ⇒ chạy đúng ở cả demo và LIVE.

⚠️ **`-4045` — CHẨN ĐOÁN CŨ ĐÃ SAI (sửa 12/10)**: kết luận "giới hạn phía Binance, không phải lỗi bot" là **SAI**. Gốc thật: từ 2025-12-09 Binance chuyển lệnh điều kiện sang **Algo Order API** (`/fapi/v1/algoOrder`); ccxt `fetch_open_orders()` (và `cancel_all_orders`) **chỉ** thấy lệnh thường ⇒ bot tưởng vị thế chưa được bảo vệ ⇒ `_rearm_missing()` đặt lại mỗi 60s ⇒ **tích tụ 100 lệnh (TESTNET) / 200 (LIVE)** trùng lặp + lệnh mồ côi của cặp đã đóng (19 cặp TESTNET / 14 cặp LIVE) ⇒ **chạm trần stop-order của tài khoản** ⇒ mọi SL/TP mới bị `-4045`. Đã vá: `exchange.algo_orders()` (đọc algo), `fetch_protection()` (đọc cả 2 nguồn), `cancel_symbol_orders()` (huỷ cả algo), `turbo_demo.protection_drift()` (phát hiện SL/TP lệch giá) + công cụ `tools/orders_audit.py` (kiểm kê/`--dedupe`/`--cancel-orphans`). Đã gom: TESTNET 100→20, LIVE 200→4 (mỗi vị thế đúng 1 SL + 1 TP). Chi tiết: `README §18.1`.







