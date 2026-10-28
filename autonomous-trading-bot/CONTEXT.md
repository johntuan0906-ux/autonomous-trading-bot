# CONTEXT.md — Ngữ cảnh hiện tại của dự án (đọc file này ĐẦU TIÊN)

> **Mục đích**: một chỗ duy nhất ghi *trạng thái + kiến thức đã kiểm chứng* của dự án, để khi mở lại VS Code / mở phiên chat mới (người hoặc AI) là **nhớ lại ngay**, không phải suy đoán lại.
> **Cập nhật lần cuối**: 20/10/2026 (B-023 `-2022` + B-024 bụi chết + `tools/watch_regress.py` theo dõi liên tục; tắt thông báo "terminal process terminated").
> **Quy tắc vàng**: mọi con số ở đây **có ngày** và **kèm lệnh tự kiểm chứng**. Số liệu hiệu suất thay đổi mỗi ngày → chạy lại lệnh ở §3 trước khi kết luận.

---

## 0. Khôi phục ngữ cảnh trong 60 giây (dành cho phiên AI mới)

**Đang chạy 2 instance SONG SONG** (từ 11/10): repo chính = **TESTNET** (demo, học), `../atb-live/` = **LIVE** (tiền thật ~19.7 USDT). Mỗi instance có `logs/`, `.env`, kill-switch RIÊNG; code dùng chung (sync bằng robocopy `*.py tools tests`). Cả hai quét **458 cặp** (nạp 522 → lọc sàn → ban BTC vĩnh viễn; danh sách trong `.env` `SYMBOLS` do `tools/apply_symbols.py` giữ, luôn trừ `logs/banned_pairs.json` của từng instance).

**Cấu trúc thư mục — tránh mở TRÙNG (19/10)**: **repo root = `c:\Users\User\.vscode\Projects`** (chỉ có **MỘT** `.git` ở đây, branch `test-ai-agents`, remote `autonomous-trading-bot.git`); **code bot nằm trong `autonomous-trading-bot/`** (TESTNET chạy ở đây), **LIVE ở `atb-live/`** (bị `.gitignore`). Vì vậy **ĐỪNG** mở `autonomous-trading-bot/` như một root workspace riêng — VS Code sẽ hiện **2 lần cùng một cây** (đúng như đã gặp), index/watch trùng ⇒ search chậm + kết quả trùng, agent đọc trùng (`CONTEXT.md` vs `autonomous-trading-bot/CONTEXT.md`). Mở đúng bằng **`atb.code-workspace`** (1 root) hoặc chính thư mục `Projects`; `.vscode/settings.json` đã loại `logs/`, `backups/`, `__pycache__`, `vendor`, `models` khỏi watcher/search/Pylance. Kiểm chứng nhanh: `git -C <thư-mục> rev-parse --show-toplevel` (phải ra `...\Projects`).

**Kiểm tra sau khi bỏ root trùng (19/10 14:42)** — hội đồng **5-0 ALLOW** (mimo-v2.6-pro, qwen3.7-plus, qwen3.7-max, qwen3.8-max, minimax-m3; phiếu lưu trong journal `status=COUNCIL`): TESTNET round **1739→1741**, LIVE **344→346** (equity 39.39, 8 vị thế), watcher `restart_when_flat` PID 112116 sống, 3 phút gần nhất **0 lỗi**; suite **1005 test OK** (54s); `harness_audit` LIVE **100/100**, TESTNET 88/100 (FAIL duy nhất = kill-switch trip, đúng phán quyết); `bug_catalog` 21 lớp/36 test OK; `capabilities` 26 tool OK. ⇒ Bỏ root trùng **chỉ ảnh hưởng hiển thị VS Code**, không tác động runtime. Lưu ý: khi root đổi, VS Code có thể hỏi *"Do you trust the authors of this folder?"* → chọn **Yes** (chọn No thì `tasks.json` không chạy được).

**TESTNET RESUME bằng PARITY LIVE (19/10 14:59 — hội đồng 3-1 ALLOW)**: TESTNET kẹt từ 15/10 (`tripped:true`, daily loss 2.03%) vì tham số demo cũ (risk **1.0%** / **4** slot / trần **2.0%**) khiến chỉ **2 lệnh thua liên tiếp** là chạm trần 2%/ngày ⇒ trip gần như tất yếu (3.6 ngày `monitor_only_end`, không học được gì = lớp lỗi B-003). Đã áp **parity LIVE**: `RISK_PER_TRADE_PCT=0.25`, `MAX_POSITIONS=1`, `MAX_TOTAL_RISK_PCT=1.0` (giữ `MARGIN_TYPE=ISOLATED`, `LEVERAGE=8`), `tools/restart_bot.py --target testnet --reset` → kill-switch sạch, TESTNET **100/100**. Muốn về tham số demo cũ: sửa 3 dòng đó trong `.env` (có ghi chú `Muon ve lai:` ngay trên mỗi dòng).

**Cổng máy "hội đồng IM LẶNG" (19/10)**: `harness_audit` có thêm dòng **`council-models`** — đếm **số MODEL khác nhau thực sự trả phiếu** trong 48h (`council_models()` đọc `logs/journal.jsonl`, dòng `status=COUNCIL`; ngưỡng `MIN_COUNCIL_MODELS=3`). Trước đây harness chỉ đọc `AGENT_VETO_SOURCE` nên vẫn 100/100 trong khi **0 model trả phiếu** (402 hết credit / provider 500 / tier `lite`) ⇒ mọi kết luận về veto vô nghĩa. Nay <3 model ⇒ **WARN** + gợi ý `agents.py --council-health`. Đây cũng là **điều kiện máy** cho câu hỏi "có nạp credit dự phòng không" (LIVE, 19/10): *theo dõi, chưa nạp*; chỉ nạp khi WARN này lặp 2 ngày liền.

**Đã gặp (19/10 14:53, LIVE)**: `close NEAR failed: {"code":-2022,"msg":"ReduceOnly Order is rejected."}` — vị thế đã đóng (SL khớp) trước khi bot kịp gửi lệnh đóng ⇒ `-2022`; `reconcile` phát hiện **stale** (`stale=['XRP','NEAR'] da-don-lenh=['XRP']`) và tự dọn trong vòng sau (round 351+ sạch, không cần can thiệp). Chưa xử lý `-2022` tường minh (khác `-4164`/`-4045` đã vá) — **TÁI DIỄN LẦN 2** (ONDO/USDT 16:21 19/10, cùng kiểu: SL khớp trước khi bot kịp gửi lệnh đóng ⇒ sàn trả `ReduceOnly Order is rejected`, `reconcile` tự dọn ở vòng sau) ⇒ **P1 kế tiếp: xử lý `-2022` tường minh** (đọc lại vị thế thật; nếu sàn xác nhận qty=0 thì coi như đã đóng + ghi CLOSE, tránh 2 dòng WARNING và 1 vòng trễ mỗi lần).

**THEO DÕI LIÊN TỤC TÁI PHÁT + TIẾN TRÌNH (20/10) — `tools/watch_regress.py`.** Sau khi vá một lớp lỗi, câu hỏi thật là *"nó có tái xuất hiện không"* — và câu trả lời phải do **máy** trả lời. Cách làm: mỗi lớp lỗi đã vá = 1 **SIGNATURE** (mẫu văn bản trong log lỗi) + **MỐC THỜI GIAN ĐÃ VÁ** (`logs/regress_watch.json`, đặt bằng `--mark-fixed B-023`); chỉ đếm dòng log có timestamp **≥ mốc** ⇒ *"0 lần kể từ khi vá"* là **bằng chứng kiểm chứng được**, và tự động thành SAI ngay khi nó tái xuất hiện. Đồng thời kiểm **tiến trình theo pid THẬT** (`tasklist`, không chỉ đọc file): supervisor còn chạy? tiến trình con còn chạy (nhịp tim "mới" mà pid không tồn tại = số CŨ)? nhịp tim, kill-switch, số vị thế, cổng tạm dừng. Khi phát hiện: ghi vết `logs/regress_watch.log` + **đẩy câu hỏi vào `ops_queue`** (priority high, mỗi instance/lớp chỉ 1 lần). Chạy: `python tools/watch_regress.py` (1 lần) · `--check` (exit 1 nếu có vấn đề) · `--watch --interval 300` (nền trong VS Code) · `--install-task` (**Task Scheduler mỗi 10 phút, không cần VS Code mở**). 24 test (`tests/test_watch_regress.py`).

**RÀ SOÁT LẠI THAY ĐỔI ĐÃ ÁP SAU VÀI NGÀY (26/10) — `tools/review_due.py`.** Yêu cầu người vận hành: *"theo dõi tiếp, vài ngày sau xác nhận lại"*. Câu trả lời **không thể là trí nhớ người** ⇒ ngày rà soát nằm **trong SỔ** (`harness_ledger.jsonl`, trường `review_at`; hẹn bằng `--add --review-days N` hoặc `--schedule <ID> --days N`), và `harness_ledger --check` **báo CAN XEM** khi một thay đổi đã áp mà **quá hạn chưa xác nhận** (không để "vả rồi để đó"). Tool chạy hằng ngày (task **`ATB-ReviewDue`** 09:00): so **cửa sổ MỚI** (từ lúc áp) với **cửa sổ NỀN** (14 ngày trước đó) trên **journal THẬT** → `n`, `avgR`, `PF`, `WR`; rồi **chỉ HỎI** người vận hành (câu hỏi vào `ops_queue` **đúng instance**, kèm lựa chọn "về 14/69" = đường lùi) — **không tự đổi tham số**. Ba kỷ luật bắt buộc: (1) `n < 30` ⇒ **KHÔNG kết luận**, tự **hoãn +7 ngày** và ghi vết; (2) **tính R THẬT từ giá** (`r = (exit-entry)/|entry-sl|`, ghép OPEN→CLOSE) vì trường `r` trong journal **là rác** — xem **B-031** (có bản ghi `r=793` và `r=+196` cho lệnh LỖ); loại bản ghi ngoài dải `[-1.6, 5.0]` và **đếm `n_dropped`** để minh bạch; (3) **kiểm chứng cửa sổ** bằng `rr` trung vị của lệnh MỚI tính từ giá (hình học mới 12/6 ⇒ `rr=2.0`) — nếu cửa sổ "mới" vẫn ra `rr≈4.9` thì **mốc áp sai** ⇒ bằng chứng không dùng được. Đo 26/10: cửa sổ mới **n=0** (lệnh cuối 24/10) ⇒ hẹn lại 29/10 06:55; nền: n=540, avgR=+0.045, PF=1.15, WR=51%; `rr_lenh_moi=2.00` ✅ đúng hình học mới. 28 test (`tests/test_review_due.py`) + 8 test sổ. Chạy tay: `python tools/review_due.py --force H-20261026-007` · `--list` · `--check`.

**B-024 — VỊ THẾ BỤI "KHÔNG THỂ ĐÓNG" (20/10, phát hiện khi theo dõi).** TESTNET có vị thế BANK **1 hợp đồng = 0.026 USDT** trong khi sàn yêu cầu tối thiểu **5 USDT** ⇒ **không lệnh MARKET/LIMIT nào đóng được**; bot cũ cứ giữ lại nên **mỗi ~4 phút** lại "đóng thất bại" ⇒ ghi 1 dòng **CLOSE GIẢ** vào journal (làm sai WR/PF) + arm lại SL/TP (tốn hạn ngạch stop-order) — **log ồn mà vô dụng, mãi mãi**. Nay `bot._dust_give_up()`: sau `DUST_MAX_FAILS=3` lần thất bại ⇒ ghi symbol vào `logs/dust_skip.json` + bỏ khỏi sổ sách + báo **1 lần**; `position_sync.adopt` bỏ qua symbol trong file đó (không kéo lại mỗi vòng/restart). Muốn theo dõi lại: xoá symbol khỏi file. 3 test mới.

**LỆNH TAY BICOUSDT + MẪU TP/SL ĐÃ ÁP DỤNG CHO CẢ 2 INSTANCE (21/10).** Lệnh mẫu trên LIVE: **LONG 706 @ 0.01703**, **SL 0.0154 (−9.57%)**, chốt **30% ở +27.4%** và **50% ở +47.4%**, giữ **20% chạy**, SL **cố định** (`closePosition=true`); notional ≈12 USDT, lỗ tối đa 1.15 USDT = **2.9% equity**. Quy đổi: SL = **5.5×ATR(1h) = 14×ATR(15m)**; TP1 = **4.95R**; TP2 = **2.86R**. Đối chiếu bằng dữ liệu: (a) mô phỏng trên **3.231 lệnh** của chính bot ⇒ cách này cho **−14% tổng R** (các bậc gần hơn còn tệ hơn: 4R/2R −48%, 3R/1.5R −53%) vì bot đánh khung **15m** và MFE p90 trên LIVE chỉ **1.25R**; (b) trên LIVE **$40 vốn**, SL 9.57% + risk 0.25% ($0.10) ⇒ notional **$1.04 < 5 USDT** ⇒ **không vào được lệnh** (muốn vào phải risk ≥1.2%/lệnh). **Hội đồng: 1 ALLOW / 3 VETO ⇒ VETO** (phiếu lưu trong journal `status=COUNCIL`). Đã làm (không đổi hành vi giao dịch): `ADOPT_SKIP_SYMBOLS=BICO` ở **cả 2 instance** (bot **không bao giờ** quản lý/dời SL/chốt lệnh tay), mẫu cấu hình để sẵn trong `.env` (khối "MẪU TP/SL CỦA NGƯỜI DÙNG", đang comment — bật bằng cách bỏ `#` 6 dòng rồi restart), bài học ghi trong `LESSONS.md` (khối `<!-- HUMAN -->`, đã kiểm chứng **sống sót** qua `learn_review`), và câu hỏi vận hành **#1 (LIVE, high)**: có nâng `RISK_PER_TRADE_PCT` lên ≥1.2% để dùng được SL rộng không. **ĐÃ ÁP DỤNG 21/10** (người vận hành yêu cầu làm đồng thời 2 lựa chọn): `RISK_PER_TRADE_PCT=1.2`, `MAX_TOTAL_RISK_PCT=1.6`, `SL_ATR_MULT=14`, `TP_ATR_MULT=69`, `PARTIAL_AT_R=2.86`, `PARTIAL_PCT=0.3`, `BE_AT_R=0`, `TRAIL_ATR_MULT=0`, `SIZE_TO_MIN_NOTIONAL=true` (nâng qty lên minNotional thay vì SKIP_NOTIONAL — đo: 23/40 cặp vào được ở risk 1.2%, có cờ này 40/40). **Hệ quả**: 2 lệnh thua ⇒ trip kill-switch 2%/ngày; muốn chạy liên tục phải nâng `MAX_DAILY_LOSS_PCT` (chưa làm).

**LỖI NGHIÊM TRỌNG TÌM RA + VÁ (20/10) — B-023: `-2022 ReduceOnly Order is rejected` = SÀN TỪ CHỐI `reduceOnly` cho lệnh MARKET (KHÔNG phải "vị thế đã đóng").** Chuỗi sự thật đo được: **157 lần `-2022`/ngày**, 13 lần `monitor ... failed` ⇒ **kill-switch TESTNET TRIP OAN** lúc 09:06 ("7 consecutive API errors"), rồi `_flatten` đóng 16 vị thế mà **không đóng được vị thế nào** ⇒ sổ sách SẠCH trong khi sàn vẫn giữ đủ 16 vị thế (vị thế mồ côi — chỉ còn bảo vệ đã arm trước đó). Đo TRỰC TIẾP trên API demo: (1) `reduceOnly=True` MARKET bị từ chối **vô điều kiện** — qty=1 trên vị thế 31 hợp đồng VẪN `-2022`; (2) `closePosition=true` cũng không dùng được cho MARKET: `-4136 Target strategy invalid for orderType MARKET`; (3) **chỉ lệnh MARKET KHÔNG `reduceOnly`, qty ĐÚNG BẰNG vị thế thật** mới FILLED (31→0). Đã vá: `exchange.close_position` gặp `-2022` ⇒ đọc lại vị thế **của ĐÚNG PHÍA** (`position_qty(..., direction=...)` — HEDGE có 2 dòng LONG/SHORT cùng symbol; đọc nhầm phía = vị thế mồ côi) ⇒ qty=0 thì `already_closed` (coi như ĐÃ ĐÓNG), còn vị thế thì `_close_exact()` đóng lại bằng `qty = min(qty_sàn, qty_yêu_cầu)` (**không `reduceOnly`**) rồi **đọc lại** để báo `left_over`/`flipped` (lật chiều khi SL khớp đúng lúc gửi); không đọc được ⇒ **ném lỗi như cũ** (không đoán). Memo `_ro_market_rejected` để không tốn 1 request chắc chắn thất bại mỗi lần đóng. `bot._record_exit()` dùng CHUNG cho `EXIT_SL/EXIT_TP` và nhánh `PARTIAL` gặp `-2022` (trước đây nhánh PARTIAL rơi vào `except` ⇒ `register_error()` ⇒ **trip kill-switch oan**); `_dust_close`/`position_sync.adopt` cũng đọc qty theo đúng phía. `-2022` thêm vào `ops.COUNT_PATTERNS`: còn xuất hiện trong log lỗi = **cả đường dự phòng cũng thất bại** ⇒ cần người xem. Xử lý vận hành kèm theo: TESTNET `risk.py --reset` + restart (16 vị thế mồ côi được `adopt` lại và arm bảo vệ); 1 vị thế AVAX (30 hợp đồng) đóng thủ công trong lúc đo để chứng minh đường "không reduceOnly" chạy đúng.

**LỖI AN TOÀN TÌM RA + VÁ (19/10 15:35) — B-022: `MAX_POSITIONS` là "chốt giả" trên LIVE.** `turbo_demo.py` — script mà `run_forever.py` chạy cho **cả hai** instance — **bỏ qua `MAX_POSITIONS` vô điều kiện** (docstring ghi "chỉ dùng trên demo" nhưng không có cổng nào chặn LIVE). Đo thật lúc 15:03: **TESTNET 14 vị thế**, **LIVE 8 vị thế** dù `.env` đặt `MAX_POSITIONS=1`; thứ thật sự chặn chỉ là `MAX_TOTAL_RISK_PCT=1.0` (risk thực mỗi vị thế ~0.075–0.15% do quantize qty) + kill-switch. Đã vá: `turbo_demo.max_positions_block()` chặn sớm trên LIVE (`SKIP_MAX_POS`), mặc định `TURBO_BYPASS_MAX_POSITIONS` = **chỉ DEMO mới bỏ qua** (`config._default_turbo_bypass`), fail-safe khi thiếu thuộc tính. 11 test mới (`tests/test_turbo_gate.py`) + lớp lỗi **B-022** trong `bug_catalog` (22 lớp / 41 test chốt). **Hiệu lực**: TESTNET (demo) không đổi; **LIVE áp dụng từ lần restart kế tiếp** — watcher `restart_when_flat` (PID 112116) restart khi hết vị thế kèm pause 24h, nên **không cần** restart tay giữa 8 vị thế đang mở. Muốn turbo trên LIVE (không khuyến nghị): `TURBO_BYPASS_MAX_POSITIONS=true`.

**Tự động hoá + artifact (19/10, sau khi hội đồng đọc 7 repo — xem `REPO_IDEAS.md` §16)**: (1) `tools/terminal_hygiene.py` dọn shell rác của VS Code (Cline tạo **1 terminal mỗi lần chạy lệnh**; đo được **112 shell = 1138 MB RAM**) — 3 lớp an toàn (chỉ shell của `Code.exe`, chỉ shell **rảnh**, bỏ qua cây tiến trình đang chạy), **tự động chạy ở cuối mỗi lần `council_vote.py`** (`--no-clean` để tắt, `--watch` cho nền, task *"Cline: theo dõi dọn terminal"*); (2) `tools/ops_artifact.py` — mỗi quyết định vận hành sinh `logs/ops/<ts>-<slug>.md` (bối cảnh → **bảng phiếu hội đồng lấy từ journal theo đúng câu hỏi** → quyết định → hành động → kết quả → truy vết), **tự sinh khi `ops_queue.answer`** (`--from-queue <id>`, `--list`, `--council-question`). Hội đồng đọc 7 repo (AutoGPT, LangChain, Dify, MetaGPT, AutoGen, CrewAI, LangGraph): **1-4 VETO** việc làm `council_replay` ngay (tốn credit mỗi lần chạy) ⇒ chọn artifact (0 chi phí LLM). Lưu ý: **AutoGen đã ARCHIVED**; Dify/AutoGPT platform cần server+DB ⇒ chỉ mượn **cơ chế**, không mượn hạ tầng.
**Terminal "Cline" tích tụ trong VS Code (19/10) — chi tiết**: extension **Cline** (`saoudrizwan.claude-dev`) tạo **1 terminal mới cho mỗi lần chạy lệnh** và **không tự đóng** ⇒ đo được **112 shell PowerShell sống = 1138 MB RAM** (nguyên nhân lag, không phải do repo/thư mục). Cline **không có setting** terminal nào (đã kiểm `package.json`), nên cách xử lý: (a) xoá định kỳ bằng `Ctrl+Shift+P → Terminal: Kill All Terminals`; (b) hạn chế số lần chạy lệnh (gộp nhiều lệnh vào 1 lần); (c) `terminal.integrated.enablePersistentSessions=false` (đã đặt ở cả user + workspace settings) để **reload cửa sổ là xoá hết** terminal cũ. Kiểm tra nhanh: `(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'powershell' -and $_.ParentProcessId -in (Get-Process Code).Id }).Count`.

Đọc theo thứ tự: **CONTEXT.md (file này) → `OPERATIONS.md` (vận hành hằng ngày: 3 lệnh, shell, restart an toàn) → `STATE.md` → AGENTS.md → README.md mục 13–15 → `REPO_IDEAS.md` (9 repo tham khảo + việc áp dụng)**. Sau đó chạy:

```bash
python live_ready.py                 # còn thiếu cổng nào để sang LIVE
python monitor_report.py --days 7    # hiệu suất thật từ journal
python status.py                     # bot có sống? ví? vị thế? learner?
python agents.py --authority         # hội đồng AI đã có quyền chặn lệnh chưa
python tools/ops_queue.py resume     # ĐANG CHỜ người vận hành trả lời gì? (mỗi instance)
python tools/bug_catalog.py --check  # lớp lỗi cũ còn test chốt không (mất test = mất chốt)
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
| **Hội đồng: id gateway (13/10)** | **ĐÃ SỬA**: `clinepass`/`ClineProvider` gửi **nguyên văn** tên `cline-pass/glm-5.3` lên gateway, mà gateway đã đổi id sang `<vendor>/<tên>` ⇒ `HTTP 500 {"error":"empty response content"}` ⇒ 12/14 model chết. Thêm `model_aliases.to_gateway()` (map 15 alias → id thật, lấy từ chính `GET /api/v1/models`) + **gửi `max_tokens=300`** (không gửi thì model trả rỗng) | **Đã kiểm chứng qua code bot**: `cline-pass/mimo-v2.6-pro` → `{"action":"ALLOW","confidence":0.7,...}` (phiếu thật). `kimi-k3`/`glm-5.3` còn 500 tại gateway → đã cho vào `CLINE_SKIP_MODELS` |
| **Tên provider (13/10)** | Journal ghi `copilot_cli` nhưng `.env`/hàm chặn dùng `copilot` ⇒ việc "bỏ review khi provider bị chặn" **không có tác dụng** (đã bỏ hậu tố `_cli` khi kiểm tra) | sửa trong `_provider_blocked()` — ảnh hưởng mọi chỗ gọi |
| **Danh sách chung lẫn provider (13/10)** | `AGENT_COUNCIL_MODELS` có thể chứa `cline-pass/*`; khi Cline bị chặn theo ngày thì model cline **vẫn được dùng** ⇒ gọi gateway vô ích + sai báo cáo "provider còn lại làm 100%". Tên hỏng `qwen/cline-pass/x` trước đây **che mất** lỗi này | `_council_models()` lọc theo tiền tố ở bước cuối (nhánh fallback "cả 2 chặn" vẫn trả danh sách để không crash) |
| **CLI in phiếu bị crash (13/10)** | `agents.py --council-multi-test` ném `UnicodeEncodeError` (console Windows cp1252) khi in trả lời model có dấu/emoji ⇒ mất toàn bộ bằng chứng phiếu | `main()` gọi `reconfigure(encoding="utf-8", errors="replace")` (theo quy ước có sẵn ở `memory_agent.py`) |
| **Hội đồng: danh sách model (14/10)** | `AGENT_COUNCIL_CLINE=all` (14 model) gọi cả model gateway đã chết/treo ⇒ hội đồng chậm (>10 phút), phần lớn phiếu trắng. Đã **dò song song qua chính `ClineProvider`**: 5 model trả JSON thật trong 8–20s | `.env` cả 2 instance: `AGENT_COUNCIL_CLINE=mimo-v2.6-pro,qwen3.7-plus,qwen3.7-max,qwen3.8-max,deepseek-v4-pro`. Quay lại toàn bộ: đặt `all`. Dò lại: `python tools/probe_cline.py` |
| **Cổng prompt (14/10)** | Payload hội đồng có thể chứa dữ liệu **ngoài lai** (`pattern`/`regime`/lý do đóng lệnh, sau này là tiêu đề tin) mà không có cổng nào khử chỉ thị ⇒ model có thể *nghe theo dữ liệu* thay vì phân tích số liệu | `prompt_guard.sanitize_payload()` gắn tại `build_prompt()` (điểm chặn duy nhất): bỏ mẫu chỉ thị (`ignore previous`, `system:`, `<|...|>`, `bỏ qua mọi hướng dẫn`), URL, ký tự điều khiển; cắt 120 ký tự/trường; trả `findings` để ghi log (không im lặng). 10 test |
| **Phiếu hội đồng bị nuốt (14/10)** | `multi_model_council` trả `votes` dạng **dict**, nhưng `AgentLayer.log_decision()` gọi `dec.to_dict()` ⇒ `AttributeError` bị `except Exception: return {}` **nuốt im lặng** ⇒ **mọi phiếu VETO/ALLOW của hội đồng KHÔNG vào journal** (chỉ model trở ngại được ghi). Hệ quả: `--council-health` luôn báo "0 VETO/0 ALLOW" dù hội đồng có ra VETO thật, và bằng chứng cấp quyền veto **không bao giờ tăng** | `log_decision()` nhận cả `Decision` lẫn `dict`; `turbo_demo` đọc `cache_hit` theo cả 2 dạng; nhãn provider theo đúng tiền tố (`_provider_label`) |
| **Ngưỡng lessons 13/10** | Quét ngưỡng (`learn_review --sweep`): **−0.05** tiết kiệm 82.33 (TESTNET) / 62.46 (LIVE) mà **bỏ lỡ 0** ⇒ siết từ −0.20/−0.15 về **−0.05** cả 2 instance | xem lại mỗi tuần: `python tools/learn_review.py --target live --sweep` |
| **Ràng buộc JSON cho model local (15/10)** | `raw_text` của model local là **ví dụ JSON lặp lại** (nó "dạy" định dạng chứ không phân tích lệnh) ⇒ phiếu rỗng thông tin, đo được `value_r = −1.303` (VETO chặn lệnh thắng +0.246R, ALLOW cho lệnh thua −1.057R) | `OpenAICompatProvider(json_mode=True)` thử **giảm dần độ chặt** `json_schema → json_object → off` (tự hạ cấp khi 400/404/422, lỗi khác ném ngay; ghi `json_mode_used`). Đã kiểm chứng: llamafile **nhận `json_schema`** và trả JSON sạch. Chẩn đoán: `python tools/probe_local_json.py` |
| **Đọc journal tăng dần (15/10)** | `learn_review` đọc lại **toàn bộ** journal mỗi lần (2.27 MB và lớn dần) — chi phí tăng tuyến tính theo lịch sử | `lessons.update_state()`/`build_from_state()` + cache `logs/lessons_cache.json` (offset + `resets`, xoay file an toàn); `--full` khi cần đọc toàn bộ. Đo trên journal thật: 0.11s → **0.00s**, 34 tổ hợp/834 lệnh/91 loại bỏ **khớp tuyệt đối** |
| **Tầng agent đơn chết vì provider bị park (15/10)** | `.env` ghim `AGENT_PROVIDER=copilot_cli` + Copilot hết quota tháng (`AGENT_COUNCIL_COPILOT_UNTIL=2026-11-01`) mà `build_provider()` **không hỗ trợ Cline** ⇒ review sau khi đóng lệnh **chết 100%** (LIVE 7/7, TESTNET 82/82 trong 48h) ⇒ không rút được bài học nào từ lệnh LIVE | `build_provider` nhận `cline/clinepass/cline_pass` (cố ý không đặt trong `_PROVIDERS` để tránh default model sai gateway); `.env` 2 instance → `AGENT_PROVIDER=cline`, `AGENT_MODEL=mimo-v2.6-pro`. Chẩn đoán: `python tools/diag_review.py` |
| **`restart_when_flat` nhắm SAI instance (15/10)** | `ROOT = Path(__file__).parent` **cố định** ⇒ chạy `restart_when_flat.py` từ `atb-live` vẫn đọc `.env` và kill supervisor của **TESTNET**: LIVE không bao giờ được áp cấu hình mới, và nguy hơn là kill nhầm instance đang có vị thế mở | thêm `--target {testnet,live}` + `chdir` vào instance **trước** khi đọc `Settings()`; truyền `root` xuống `restart_bot()`/`env_symbols()`/`open_positions()` (log ghi theo instance) |
| **`council_vote` trả 0 phiếu (15/10)** | Không truyền `models` ⇒ hội đồng tự chọn tier theo độ khó (payload vận hành ~0.15 → tier `lite`, `AGENT_COUNCIL_SINGLE_BELOW` bật chế độ SINGLE) ⇒ chỉ hỏi **1 model**, mà model lite đầu danh sách lại nằm trong `CLINE_SKIP_MODELS` ⇒ bị bỏ qua **im lặng** ⇒ `votes: {}` dù log báo "8 model" (tool in ra "0 phiếu/NO_OPINION" = báo sai) | tool lấy **danh sách đầy đủ** và truyền `models=` (bypass tier); thêm `--raw` để soi phản hồi gốc. Sau khi sửa: 5 model bỏ phiếu thật (2 ALLOW / 3 VETO). Còn nợ: model bị bỏ qua phải được ghi vào `abstained` kèm lý do thay vì mất dấu |
| **`AGENT_COUNCIL_QWEN` chứa model Cline (15/10)** | `.env` 2 instance đặt `AGENT_COUNCIL_QWEN=cline-pass/qwen3.8-max,cline-pass/qwen3.7-plus` ⇒ sinh tên hỏng `qwen/cline-pass/qwen3.8-max` ⇒ **cùng một model bỏ 2 phiếu ngược nhau** (ALLOW 0.62 + VETO 0.62) làm lệch kết quả bỏ phiếu | đặt `AGENT_COUNCIL_QWEN=` rỗng (2 model đó đã có trong `AGENT_COUNCIL_CLINE`); chỉ điền khi có CLI `qwen` thật |
| **Phiếu hậu kiểm làm nhiễu bảng điểm model (15/10)** | `council_eval` tính **cả phiếu của agent review** — phiếu này bỏ **sau khi lệnh đã đóng** nên đã biết kết quả ⇒ thiên lệch nhìn trước (đo được: dòng `claude-sonnet-5.5` +0.044 chính là model review, không phải phiếu hội đồng) | `council_evals.is_pre_trade()` loại `status=CLOSED/REVIEW` và vai `review/review_agent` khỏi `pair_cases()`; test chốt trong `tests/test_council_evals.py` |
| **Công cụ chạy "cho instance khác" đọc sai `.env` (15/10)** | `load_dotenv()` tìm `.env` theo **thư mục của `config.py`** (không theo cwd) ⇒ tool chạy từ repo chính nhưng nhắm `../atb-live` vẫn dùng `BINANCE_TESTNET=true` + key demo ⇒ `-2015 Invalid API-key`, và snapshot LIVE ghi `testnet=true` khiến `live_guard` **bỏ qua mọi chốt chặn** (nó tưởng đang ở testnet) | `config.py` nhận `ATB_ENV_FILE` (đặt **trước** khi import ⇒ đọc `.env` của instance đích, `override=True`); chẩn đoán: `python tools/instance_env.py` (đối chiếu `.env` file ↔ OS env ↔ `Settings()`, cảnh báo biến bị OS ghi đè) |
| **Quyết định vận hành có bằng chứng (15/10)** | Kill-switch TESTNET trip (6 lệnh thua liên tiếp) — trước đây chỉ 1 người quyết và không lưu vết | `tools/council_vote.py` triệu tập hội đồng và ghi phiếu vào journal (`status=COUNCIL`). Lần 1 (chưa nêu bằng chứng lessons): **2 ALLOW/3 VETO → VETO**. Sau khi bổ sung "4 tổ hợp lỗ đã bị `lessons.py` chặn": **3 ALLOW/1 VETO → ALLOW** ⇒ reset kill-switch + restart TESTNET (cùng lúc nạp `.env` mới) |
| **Danh sách SKIP không có tác dụng (15/10)** | `.env` ghi danh sách hội đồng **không tiền tố** (`mimo-v2.6-pro`) còn `CLINE_SKIP_MODELS` ghi **có tiền tố** (`cline-pass/mimo-v2.6-flash`) ⇒ phép so sánh cũ `m not in skip` **luôn sai** ⇒ model đã chết vẫn được gọi mỗi vòng (tốn thời gian + rác journal). Phát hiện khi viết test cho hàm liệt kê model bị bỏ qua | `agents._apply_skip()` so khớp **cả 2 dạng tên**, áp cho cả 5 provider (cline/muse/muse_cli/qwen/local) |
| **Model bị SKIP biến mất im lặng (15/10)** | Model bị loại ngay khi đọc cấu hình ⇒ không vào `decisions` ⇒ không vào `abstained` ⇒ `--council-health` không thấy, không ai biết vì sao thiếu phiếu (đúng lớp lỗi đã làm hội đồng "im lặng" 48h) | `multi_model_council` trả thêm `skipped` (model → tên biến SKIP) và gộp vào `abstained` **sau khi xong các vòng** (không để chúng bị hỏi lại ở vòng ngân sách/debate); `turbo_demo` ghi đúng lý do (`bo qua: CLINE_SKIP_MODELS`) vào journal |
| **`state_sync` cho instance khác (15/10)** | Chạy từ repo chính mà nhắm LIVE ⇒ `Settings()` vẫn dùng `.env` testnet ⇒ snapshot/STATE.md của LIVE ghi `testnet=true`, `risk_pct=1.0`, `max_positions=4` (số của TESTNET) và `live_guard` **bỏ qua mọi chốt chặn** | `state_sync.py --target {testnet,live}`: nạp `.env` của instance đích bằng `config.load_instance_env()` + ghi vào `STATE.md`/`logs/state_snapshot.json` của instance đó. Đã kiểm chứng: snapshot LIVE = `testnet=false, live_confirm=true, risk_pct=0.5, max_positions=2`; STATE.md = "**LIVE (TIỀN THẬT)**" |
| **Vị thế do người/bot khác mở trên LIVE (15/10)** | Người vận hành yêu cầu "tạm bỏ qua lệnh có sẵn trên LIVE". Đo thực tế (`tools/orders_audit.py --target live`): 1 vị thế `BTW/USDT:USDT` + 1 `STOP_MARKET` bảo vệ, `managed_state.trades={}` ⇒ bot không quản lý. **Rủi ro tiềm ẩn:** nếu cặp đó **nằm trong danh sách cặp của bot** thì `ADOPT_POSITIONS=true` sẽ **nhận nuôi** và bot tự đặt SL/TP · chốt lời · đóng — trái ý người vận hành | thêm `ADOPT_SKIP_SYMBOLS` (nhận cả `BTW` lẫn `BTW/USDT:USDT`): vị thế bị **bỏ qua hoàn toàn** (không vào `portfolio`/`managed`, không đặt lệnh nào, không tính vào slot), log `ADOPT: BO QUA n vị thế theo ADOPT_SKIP_SYMBOLS`. `.env` LIVE: `ADOPT_SKIP_SYMBOLS=BTW` (tạm thời, bỏ khi hết vị thế); TESTNET: rỗng |
| **Hội đồng im lặng TRÊN ĐƯỜNG VÀO LỆNH (16/10)** | **LỖI THẬT ĐÃ SỬA**: tier `lite` chỉ lấy model lite/core, mà **mọi model Cline làm được phiếu đều bị xếp `hard`** (tên chứa `pro`/`max`/`plus`) ⇒ tier lite chỉ còn model **local** — mà local nằm trong `AGENT_COUNCIL_IGNORE` ⇒ `_tally` lọc đi ⇒ **0 phiếu**. Log LIVE (round 248): `do kho 0.00 -> tier 'lite' (1 model)` + `hoi dong 1 model: 0A / 0V (hoa 0: -)` ⇒ hội đồng "sống" nhưng **không có phiếu nào** cho phần lớn lệnh | `_council_models_by_tier()` loại model bị IGNORE **trước** khi chọn tier + mở rộng dần khi còn <2 model (lite → lite+core → toàn bộ); `.env` 2 instance đặt `AGENT_COUNCIL_SINGLE_BELOW=0` (tắt chế độ 1 model). 2 test chốt |
| **Margin CROSS lẫn giữa vị thế người dùng và bot (16/10)** | Phiếu VETO của `qwen3.7-plus` (hội đồng LIVE): tài khoản chỉ ~41 USDT mà có vị thế **CROSS** do người dùng mở (`BTW`) ⇒ **chiều margin chung** với 4 vị thế của bot, phép tính rủi ro của bot không biết nó tồn tại. Đo thật (`tools/margin_audit.py --target live`): **5/5 vị thế CROSS**, ví 41.66 · dùng 5.45 · còn 36.19 | Người vận hành chọn (a): `MARGIN_TYPE=ISOLATED` — bot đặt margin type cho cặp **ngay trước khi vào lệnh** (`exchange.set_margin_mode`, fail-open, `-4046` = đã đúng). **Binance KHÔNG cho đổi margin type khi cặp còn vị thế/lệnh chờ** ⇒ 5 vị thế đang mở vẫn CROSS tới khi đóng; mọi lệnh MỚI vào ISOLATED |
| **Adopt định kỳ 13/10** | `ADOPT_EVERY_ROUNDS=10`: cứ 10 vòng đọc lại vị thế thật, dọn entry "ma" + huỷ lệnh mồ côi | trước đây chỉ adopt lúc khởi động ⇒ LIVE giữ `BNB` trong `managed` khi sàn đã đóng |
| Kill-switch trip là THẬT | 08 lệnh thua liên tiếp 12/10 (AAVE r=-1.15, FLOKI -1.35, MOG -1.42, PEPE -1.37…) đúng thiết kế | sau reset, nếu thị trường tiếp tục xấu sẽ trip lại — đó là đúng ý |
| **Cline `402 Payment Required` rồi TỰ HỒI (18/10)** | Hội đồng LIVE im lặng: gateway trả `402` cho mọi model ⇒ đã thêm chốt chặn provider 12h (`AGENT_PROVIDER_BILLING_PAUSE_SEC`) + báo người vận hành. Vài giờ sau dò lại `python tools/probe_cline.py`: **7/8 model OK trong 25s** (`deepseek-v4-pro` = 500) ⇒ **KHÔNG phải hết credit vĩnh viễn, chỉ là tạm thời** | `.env` 2 instance: `AGENT_COUNCIL_CLINE=mimo-v2.6-pro,qwen3.7-plus,qwen3.7-max,qwen3.8-max,minimax-m3` (bỏ `deepseek-v4-pro` 500; thêm `minimax-m3`). Kiểm chứng bằng phiếu hội đồng thật: **5/5 model bỏ phiếu** (165s). **Bài học: gặp 402 ⇒ luôn `probe_cline.py` lại trước khi kết luận "hết tiền"** |
| **Probe "OK" ≠ bỏ được phiếu (18/10)** | `muse-spark-1.3-contributor` probe trả JSON hợp lệ nhưng **3/3 lần đều vào `abstained`** (2 lượt bỏ phiếu vận hành + 1 lượt chẩn đoán riêng `--json --raw`): `votes={}, abstained=["muse-spark…"]` ⇒ hội đồng "6 model" thực chất 5. Nhãn `[ngan sach]` trong `why` **không phải hết tiền** mà là `escalated` (nâng bậc vì thiếu phiếu) — nhãn dễ gây hiểu sai | Gỡ khỏi danh sách hội đồng (giữ `minimax-m3` — model này bỏ phiếu được khi hỏi riêng, 26s). Nguyên tắc: **danh sách liệt kê = số model thật sự bỏ phiếu**; `council_vote` đã in `KHONG TRA VE PHIEU` để không mất dấu |
| **Đổi `.env` KHÔNG tự có hiệu lực (18/10)** | `.env` chỉ đọc **lúc import** ⇒ bot đang chạy vẫn dùng cấu hình cũ (log còn `> 2.00% (MAX_TOTAL_RISK_PCT)` trong khi `.env` đã ghi 1.0%) — lớp lỗi "chạy config cũ" quay lại | Người vận hành chốt: siết `MAX_TOTAL_RISK_PCT` 2.0 → **1.0** (LIVE) để daily-loss 2%/ngày không bị chạm chỉ sau 2–3 lệnh thua. Áp bằng **watcher nền** `pythonw restart_when_flat.py --target live --max-hours 48` (chờ hết 8 vị thế rồi restart, KHÔNG cắt ngang lệnh đang mở; log `atb-live/logs/restart_when_flat.log`) |
| **Hội đồng VETO 5–0 việc gỡ kill-switch LIVE (18/10)** | Triệu tập hội đồng đúng quy trình ("quyết định có bằng chứng"): `0 ALLOW / 5 VETO` — lý do: daily loss 2.38% vừa trip, 6/7 lệnh lỗ, chưa qua 24h nguội, chế độ thị trường khớp kém. Thực tế LIVE **đã được gỡ khoá trước đó** (đang giữ 8 vị thế SHORT, tổng risk 1.96%, `orders_audit`: 16/16 lệnh bảo vệ, gọn) | Giữ nguyên phán quyết làm chuẩn phòng ngừa: **phản hồi bằng siết tham số** (`RISK_PER_TRADE_PCT=0.25`, `MAX_POSITIONS=1`, `MAX_TOTAL_RISK_PCT=1.0`) thay vì gỡ khoá thêm lần nữa. Muốn gỡ mạnh hơn ⇒ cần phiếu hội đồng mới có bằng chứng mới |
| **Kill-switch không tự xoá ⇒ instance kẹt pause (18/10)** | TESTNET trip "daily loss 2.03%" **15/10** rồi **kẹt 3.6 ngày** (round 1690 `monitor_only_end`, lượt gọi LLM cuối cùng `15/10`) — vì `risk.note_equity()` cố ý **không bao giờ tự xoá `tripped`** (chống restart làm mất kill-switch). Không ai báo ⇒ demo "sống" nhưng **không học được gì** | Phát hiện bằng đối chiếu `logs/risk_state.json` (`day` cũ + `tripped:true`) ↔ `logs/agent_state.json` (`last_ts`) ↔ heartbeat. Quy trình đúng: **triệu tập hội đồng** (`tools/council_vote.py`) rồi `python risk.py --reset` + restart |
| **TRUY VẾT 1 lệnh — mắt xích thiếu lớn nhất (19/10)** | Không có chỗ nào trả lời "**vì sao bot mở lệnh này**": journal có, bảng điểm model có, lessons có, nhưng rời rạc. Đo thật: lệnh `SOL` 11/10 05:43 thuộc tổ hợp `B_BREAKOUT_RETEST \| BOS_UP \| COMPRESSION \| LONG` **đang bị chặn** (n=23, avgR=-0.083) mà không ai thấy | `tools/trace_trade.py --pair SOL` → chuỗi 1) vào lệnh (feature + size/risk) 2) phiếu hội đồng quanh lúc vào 3) tầng SETUP/review 4) đóng lệnh (r/pnl/MFE/thời gian) 5) **tổ hợp + mã bằng chứng `EV-xxxxxx` + đang bị chặn?**. `--key "<tổ hợp>"` in bằng chứng (n/avgR/mốc thời gian + lệnh tệ nhất & tốt nhất) — **truy nguoc từ journal, không tin file tổng hợp** |
| **Kho tri thức phải có MÃ BẰNG CHỨNG (19/10)** | `LESSONS.md` chặn lệnh thật nhưng không ai kiểm chứng được kết luận (và tổ hợp GIẢ `? \| ? \| ? \| ?` từng lọt vào "NÊN ƯU TIÊN") | `lessons.evidence_code(key)` → mã **ổn định** `EV-xxxxxx`; `lessons.evidence(journal, key)` đọc lại **journal** để đếm n/avgR/PnL + mốc thời gian + mẫu lệnh tệ nhất/tốt nhất; `LESSONS.md` thêm **cột Mã** + dòng hướng dẫn truy ngược |
| **"Đang chờ người vận hành cái gì?" không được ghi ở đâu (19/10)** | TESTNET kẹt 3.6 ngày; cổng pause BTW phải viết watcher riêng — vì không có chỗ ghi *"đang chờ trả lời gì, chờ bao lâu"* | `tools/ops_queue.py` (2 file/instance: `logs/ops_questions.json` đang chờ, `logs/ops_queue.json` lịch sử đã trả lời): `add/list/answer/resume`; `--check` exit 1 khi có câu hỏi quá 24h. **Đã ghi 2 câu LIVE + 1 TESTNET**; thêm vào nghi thức đầu phiên ở §0 |
| **"Lớp lỗi cũ còn chốt chặn không?" (19/10)** | Repo ~980 test nhưng **không có bản đồ lớp lỗi ↔ test** ⇒ sửa rồi xoá/đổi tên test = mất chốt chặn mà không ai biết | `tools/bug_catalog.py`: **21 lớp lỗi** (B-001…B-021) kèm triệu chứng/cách chặn/file; `--check` đọc `tests/` và **báo test bị thiếu** (36 test chốt). Luật "mỗi lớp lỗi phải có test" nay **kiểm tra được bằng máy** |
| **TEST ghi đè STATE của instance THẬT (19/10)** | Chạy suite xong, `logs/heartbeat.json` của TESTNET thành `{"pid": 28000, "round": 2, "phase": "monitor_only"}` — **pid 28000 không tồn tại**. Nguyên nhân: `turbo_demo.heartbeat()` luôn ghi vào hằng số `_HEARTBEAT` (state thật) nên `tests/test_p0_safety.py::TestMonitorOnly` (chạy nhánh monitor-only) ghi đè nhịp tim thật bằng pid của tiến trình test | Hệ quả nếu bỏ qua: `ops.py`/`deadman`/`harness_audit`/`STATE.md` đọc số liệu MA, watchdog có thể tưởng bot còn sống (hoặc ngược lại). Sửa 3 lớp: `heartbeat(path=…)` · `ATB_HEARTBEAT_PATH` · **chạy dưới test runner ⇒ tự động ghi file tạm**; test chốt: `TestHeartbeatKhongGhiStateThat` + `TestMonitorOnly` set env trong `setUp` |

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
| **Trần lỗ NGÀY (22/10)** | **6.0%** (hội đồng 2 ALLOW / 1 VETO): 11/15 ngày lỗ >2%, 9/15 >3.6% ⇒ trần 2% bị chạm gần như mỗi ngày ⇒ trip + reset tay liên tục. Phanh chính nay là `MAX_CONSECUTIVE_LOSSES=5` + `MAX_TOTAL_RISK_PCT=1.6` + cổng tạm dừng có hạn |
| **Tự gỡ kill-switch** | Cơ chế `KILL_AUTO_RESET_HOURS` đã có (7 test) nhưng **hội đồng 0–2 VETO** ⇒ để **TẮT (0)**, vẫn reset tay; chống trì trệ bằng cảnh báo tự động khi trip (`watch_regress` → `ops_queue`) |
| **ĐÃ ĐỔI hình học SL/TP: 14/69 → 6/12 (26/10 13:50)** | Hội đồng **đổi quyết định khi có bằng chứng mạnh hơn**: 10:14 = **4 VETO** (n=31) → 13:45 = **4 ALLOW chọn B** (backtest rộng 10 cặp × 60 ngày, có slippage: 14/69 PF **0.57** n=162 · 6/12 PF **0.81** n=305 · 4/8 PF 0.963 n=558). Đã áp `.env` cả 2 instance: `SL_ATR_MULT=6`, `TP_ATR_MULT=12`, `PARTIAL_AT_R=1.0` (backup `.env.bak-hinhhoc1346`) + restart (TESTNET 35868, LIVE 115512). **Về lại:** `SL_ATR_MULT=14`, `TP_ATR_MULT=69`, `PARTIAL_AT_R=2.86` + restart. Sổ: `H-20261026-007` (adopted) |
| **Đo lệch khai báo vs thực tế + lệch đầu vào (28/10)** | `tools/drift_probe.py` (task **`ATB-DriftProbe`** 08:30): so `.env` (ý định) với journal (**giá trị bot ĐANG CHẠY**) ⇒ bắt "sửa .env nhưng CHƯA restart"/hình học không được áp/SL không còn theo ATR; + **PSI** từng đặc trưng so nền 30 ngày (ngưỡng 0.1/0.25) ⇒ **báo vào `ops_queue`**. Kỷ luật: **`n < 10` ⇒ KHÔNG kết luận**; câu hỏi phải kèm số đo được. Hội đồng **4 ALLOW / 0 VETO** (`REPO_IDEAS` §23) |
| **B-031 → CHẶN CHIẾN LƯỢC → BOT ĐỨNG YÊN (28/10, `drift_probe` phát hiện)** | `.env` có `STRATEGY_BLOCK=A_TREND_PULLBACK` + `STRATEGY_GATE=true` (đặt theo **đề xuất của agent** dựa trên *digest từ journal*: `sum_r=-2.465`, `avg_r=-0.066` — chính là trường `r` **RÁC** của B-031) ⇒ ~6000 dòng log cuối: **18.048 `BLOCKED_STRAT`** + 19.357 `SKIP_RISK` + 22.606 `BLOCKED_LEARN` nhưng chỉ **2 `OPENED`** ⇒ **không có lệnh mới từ 26/10 21:50** ⇒ hình học 6/12 **không thể xác nhận**. Đã đẩy **câu hỏi #2 (high)**: gỡ block hay đo lại bằng R thật trước? |
| **Rà soát lại thay đổi đã áp (26/10)** | `tools/review_due.py` (task **`ATB-ReviewDue`** 09:00 mỗi ngày): hẹn ngày bằng `harness_ledger --add --review-days N` / `--schedule <ID> --days N`; tới hạn thì tự đo lại bằng journal THẬT, **`n < 30` ⇒ tự hoãn +7 ngày (không kết luận)**, đủ mẫu thì **hỏi** người vận hành (vào `ops_queue`). `harness_ledger --check` báo CAN XEM khi **quá hạn chưa xác nhận**. Chạy tay: `--force <ID>` · `--list` · `--check` |
| **B-031: `r` trong journal là RÁC (ảnh hưởng CỔNG SANG LIVE)** | Mọi thống kê đọc `r` từ journal đều vô nghĩa (đo 26/10: `r=793`, `r=+196` cho lệnh LỖ). **`STATE.md` báo PF(R)=5.345 trong khi PF(R) THẬT chỉ 1.013** (937 lệnh ghép được, R tính từ giá; avgR=+0.004, WR=53% ⇒ bot **hoà vốn**) — và `live_ready.py`/`live_guard.py` dùng chính `pf_r` này làm cổng (PF(R)≥1.2) ⇒ **cổng sang LIVE đang chấm bằng số rác**. Đã đẩy câu hỏi **#1 (high)** vào `ops_queue`. Tạm dùng `tools/review_due.pair_trades()` (R từ giá, ghép OPEN→CLOSE) cho mọi đo lường |
| **B-030: báo động giả "OPENED" (26/10)** | `ops.py` đếm `"OPENED"` (status của lệnh mở **THÀNH CÔNG**) vào "lỗi 7 phút" ⇒ báo `CAN XEM` sai mỗi lần vào lệnh ⇒ người vận hành quen báo động ⇒ **bỏ sót báo động thật**. Đã bỏ khỏi `COUNT_PATTERNS`, tách `ops.count_errors()` để test; lỗi thật (`ORDER_FAILED`/`ERROR`/`REJECTED`) vẫn đếm. Sau khi sửa: `ops.py` → **KET LUAN: OK** cả 2 instance |
| **Stress-test đường tiền — kiểm chứng trần 6% bằng số (26/10)** | `tools/stress_harness.py` (bootstrap từ phân phối R thật, 3000 đường × 200 lệnh, seed cố định). **LIVE** (n=649, E(R)=0.085): P(kết thúc âm)=13%, drawdown p90=13.7R (~16.4% equity), **P(chạm trần NGÀY)=16% với trần 2% → 0.3% với trần 6%** ⇒ quyết định nâng trần của hội đồng 22/10 **đúng và đo được**. **Sức chịu chi phí**: +0.05R/lệnh ⇒ P(âm) 13%→35%; +0.10R ⇒ **62%**; +0.20R ⇒ 93% ⇒ edge LIVE **rất mỏng**, kiểm soát chi phí là ràng buộc chính. TESTNET (n=3342): P(âm)=0%, DD p90=10.3R, trip 9.1%→1.2% |
| **Chất lượng proxy biến động (ATR) — đo thật (26/10)** | `tools/atr_quality_probe.py`: trên journal thật (TESTNET n=955, LIVE n=599) **biên độ THUẬN trung vị chỉ 0.20–0.33R** (p90 1.13–1.36R) trong khi **chi phí = 0.10–0.16R** (~40–50% biên độ thuận trung vị). Lấy ATR thật từ sàn (mẫu 30): ATR(14,15m) trung vị **0.580%** vs biên độ thuận thật **0.23%** ⇒ **mfe/ATR = 0.37**, Spearman = **0.23** (ATR phóng đại ~3× và tương quan yếu) |
| **Hình học SL/TP 14/69 — hội đồng VETO đổi (26/10)** | Đề xuất đổi sang 6×ATR/12×ATR (backtest 30 ngày 4 cặp lớn, **có slippage**: 14/69 ⇒ n=31, WR 16.1%, PF **0.20**; 6/12 ⇒ PF 0.65; 4/8 ⇒ PF 0.82). Hội đồng **0 ALLOW / 4 VETO** (n=31 quá nhỏ; mẫu 14/69 do người vận hành chọn) ⇒ **GIỮ NGUYÊN**; ghi `H-20261026-005` kèm điều kiện mở lại (≥100 lệnh/arm, nhiều symbol, hoặc người vận hành yêu cầu) |
| **Mô phỏng có SLIPPAGE (26/10)** | `trade_mgmt.SLIPPAGE_PCT` (0.02%/chiều, `SLIPPAGE_PCT` trong `.env`) + `COST_ROUNDTRIP_PCT`; `backtest.py` truyền `slippage_pct` ⇒ mọi so sánh tham số nay gồm **phí + trượt giá**. **Không đổi số thật** (mặc định 0.0 — giá khớp thật đã bao gồm trượt giá) |
| **Cầu nối Telegram 2 chiều (26/10)** | `tools/telegram_bridge.py` + task `ATB-Telegram` (1 phút/lần, `--once`): đẩy câu hỏi đang chờ ra Telegram (**nhắc lại sau 6h** nếu còn treo) và nhận lệnh `/status /health /list /ask /answer`; lệnh **GHI** (`/dedupe /reset <t> confirm /restart <t>`) nay đã **BẬT** (`TELEGRAM_ALLOW_WRITE=true`), chỉ nghe chat_id trong `.env`, argv cố định (không `shell=True`), ghi vết `logs/telegram_bridge.log` |
| **Kronos (foundation model K-line) — hội đồng VETO (26/10)** | 0 ALLOW / 4 VETO: máy Windows CPU-only đang chia tài nguyên cho llamafile, chưa có bằng chứng vượt ATR hiện tại ⇒ **không thêm torch/weight**. Ghi sổ `H-20261026-002` kèm **điều kiện mở lại**: có GPU/máy riêng, hoặc có giả thuyết đo được (biến động Kronos vs ATR(15m) ở bước đặt SL) — khi đó chỉ **probe offline**. 3 thứ lấy được ngay không cần torch: (a) đo chất lượng proxy ATR bằng MAE/MFE thật, (b) backtest phải mô phỏng phí/slippage, (c) sinh dữ liệu tổng hợp từ 3.335 lệnh để stress-test harness |
| **Hàng đợi vận hành ghi theo cwd (B-029, 26/10)** | `ops_queue` dùng đường dẫn tương đối ⇒ task Scheduler (cwd = `C:\Windows\System32`, **có** `System32\logs` nhưng **không ghi được**) làm cảnh báo mất im lặng (đo thật 24/10: log có dòng `VAN DE naked @ LIVE` nhưng hàng đợi trống). Nay nhận diện instance bằng **dấu hiệu bot** (`logs/` + `turbo_demo.py`/`config.py`), không thì dùng repo; lỗi ghi báo ra stderr + ghi vết vào `regress_watch.log`; câu hỏi của LIVE đi đúng `atb-live/logs/ops_questions.json` |
| **Vấn đề tiến trình phải vào HÀNG ĐỢI, không chỉ in ra (B-028, 22/10)** | `watch_regress.notify()` đẩy cả `problems` (kill-switch TRIPPED, supervisor/con chết, nhịp tim cũ, **vị thế TRẦN**, **cặp lệnh bảo vệ TRÙNG**) vào `ops_queue` theo **loại** vấn đề ⇒ báo lại mỗi 1h khi còn lỗi (không spam, không tắt). Task `ATB-WatchRegress` (10 phút/lần) nay chạy `--check --orders`: tự kiểm kê bảo vệ trên sàn + ghi `logs/orders_snapshot.json` cho `ops.py` đọc |
| **Bụi ≠ TRẦN** | `orders_audit.load_dust()` tách vị thế **bụi** đã ghi `dust_skip.json` (qty < minNotional ⇒ sàn không cho đặt SL/TP) khỏi vị thế **TRẦN** thật; kết luận có dòng riêng cho TRẦN (trước đây báo động giả cho bụi rồi vẫn kết luận "gọn" ⇒ che mất TRẦN) |
| **Luật phá thế hoà của hội đồng** | `council_vote.resolve_verdict`: quorum ≥2 → đa số → tổng confidence → **giữ nguyên hiện trạng**. Không bao giờ trả `NO_OPINION` cho quyết định vận hành (người vận hành yêu cầu "đừng để chia rẽ ⇒ trì trệ") |
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
| `atomic.py` | **ghi file trạng thái NGUYÊN TỬ** (tmp → `fsync` → `os.replace`, retry khi Windows khóa file) — mọi file state phải đi qua đây (B-025) |
| `tools/council_daemon.py` | **hội đồng chạy nền 24/7** (task `ATB-Council` 15 phút): tự lập chương trình nghị sự từ journal/câu hỏi tồn/tái phát/cấu hình rủi ro, dedup TTL, trần chi phí, **mặc định dry-run**; chỉ đề xuất, không chạm đường tiền |
| `tools/harness_ledger.py` | **sổ thay đổi harness** (prompt/model/gate/risk/lesson) — mỗi thay đổi phải có bằng chứng + kết quả probe + quyết định adopt/reject (`--check`) |
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








## 15/10 — 4 viec van hanh (lam tron goi)

1. **Supervisor tu chay llamafile** (`run_forever.ensure_llamafile`, goi moi lan restart):
   do duoc hoi dong chi con `local/llama3.2-3b-local` bo phieu (10 VETO/3h) => server local
   chet = hoi dong CAM ma khong ai bao. Quyet dinh la ham THUAN TUY (`plan_autostart`),
   probe `GET /v1/models` (3s), tat bang `LLAMAFILE_AUTOSTART=false`. Dau vet:
   `logs/turbo_err.log` dong `[llamafile] <hanh dong>`.
2. **Dead-man switch** `tools/deadman.py` (+ `--install-task`, mac dinh 15 phut): doc CUNG
   nguon voi `tools/ops.py`. Coi la CHET khi: nhip tim cu / khong co supervisor /
   kill-switch dang ngung / co loi (bo qua `SKIP_DATA` vi do la hanh vi dung). Co URL
   Healthchecks thi ping `<url>` (OK) hoac `<url>/fail` (loi); khong co URL thi ghi
   `logs/deadman.json` + `logs/deadman.log`. Bao tri co chu dinh: `--mute` hoac file
   `logs/deadman_mute`. Chay that 15/10: bat ngay TESTNET kill-switch tripped.
3. **`/evolve` + `/prune` cho lessons** (`lessons.py`): `evolve()` rut **KY NANG co ten**
   (`tranh:` / `uu_tien:`, xep theo |avgR| x n) — ten lay tu KHOA to hop vi bucket chi
   chua so lieu (loi that: doc truong `strategy/...` tu bucket => luon ra `"?"`).
   `prune_stale()` truc xuat to hop khong con lenh trong N ngay (ly do luu vao
   `logs/lessons_archive.jsonl`, khong xoa). Vi `turbo_demo.lessons_gate()` tinh lai gate
   TU `buckets`, day la cach duy nhat go duoc vong chan cu. CLI:
   `python tools/learn_review.py --prune --stale-days 30 --evolve`.
4. **Backup dinh ky**: `python tools/backup.py --install-task` (03:30 hang ngay, go bang
   `--uninstall-task`) => `backups/atb-<instance>-<ts>.zip` (da kiem chung doc lai; `.gitignore` chan `backups/`).

Watch: TESTNET kill-switch trip lai (6 loi lien tiep, muc 12) — reset demo-only; LIVE co
1 `LIVE INTERLOCK` trong cua so (xem tiep).
