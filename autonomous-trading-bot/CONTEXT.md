# CONTEXT.md — Ngữ cảnh hiện tại của dự án (đọc file này ĐẦU TIÊN)

> **Mục đích**: một chỗ duy nhất ghi *trạng thái + kiến thức đã kiểm chứng* của dự án, để khi mở lại VS Code / mở phiên chat mới (người hoặc AI) là **nhớ lại ngay**, không phải suy đoán lại.
> **Cập nhật lần cuối**: 08/10/2026 ~23:40 (sau commit `ee25859`).
> **Quy tắc vàng**: mọi con số ở đây **có ngày** và **kèm lệnh tự kiểm chứng**. Số liệu hiệu suất thay đổi mỗi ngày → chạy lại lệnh ở §3 trước khi kết luận.

---

## 0. Khôi phục ngữ cảnh trong 60 giây (dành cho phiên AI mới)

Đọc theo thứ tự: **CONTEXT.md (file này) → `STATE.md` (số liệu tự động) → AGENTS.md → README.md mục 13–15**. Sau đó chạy:

```bash
python live_ready.py                 # còn thiếu cổng nào để sang LIVE
python monitor_report.py --days 7    # hiệu suất thật từ journal
python status.py                     # bot có sống? ví? vị thế? learner?
python agents.py --authority         # hội đồng AI đã có quyền chặn lệnh chưa
git log --oneline -10                # vừa thay đổi gì
```

Hiện đang chạy **testnet (tiền demo)** — KHÔNG phải tiền thật. Bot do supervisor tự chạy lại (§6).

---

## 1. Dự án là gì (1 đoạn)

Bot giao dịch **USDT-M Futures (Binance)** tự động trên Windows: vòng lặp `turbo_demo.py` quét 7 cặp → tính điểm tín hiệu (kỹ thuật + phái sinh + tin tức + learner) → đi qua các cổng an toàn **tất định** (risk, strategy block, learner score, urgent) → mở lệnh kèm SL/TP → `bot._monitor()` bảo vệ mỗi vòng. Ngoài ra có **hội đồng AI (LLM)** để *cố vấn* (chưa có quyền chặn lệnh) và **learner** học online trọng số từ kết quả thật.

## 2. Trạng thái hiện tại (09/10/2026 ~00:10 — số tự động xem `STATE.md`)

| Hạng mục | Giá trị | Ghi chú |
|---|---|---|
| Chế độ | `BINANCE_TESTNET=true`, `DRY_RUN=false` | lệnh thật trên **tài khoản demo** |
| Bot | supervisor PID `82912` + `turbo_demo` (tiến trình con) | tự restart khi crash; lock `logs/.supervisor.lock` |
| Ví demo | ~4630 USDT | số mới nhất do `state_sync.py` ghi vào `STATE.md` |
| Vị thế đang mở | **7**: DOGE, BTC, LINK, AVAX, ADA, XRP, SOL (toàn SHORT) | SL/TP trên sàn **bị chặn `-4045`** → monitor mềm bảo vệ |
| Hội đồng AI | **15 model** (12 Cline + 2 Qwen CLI + 1 Local Ollama) | Copilot bị chặn tới 01/11; **Muse đã tắt hoàn toàn** |
| Quyền veto của AI | **CHƯA cấp** (`granted=False` cho cả SETUP và COUNCIL) | hội đồng chỉ ghi `[shadow]`; `BLOCKED_VETO=0` |
| Tham số rủi ro | risk 1%/lệnh, trần tổng 2%, `LEVERAGE=8`, `MAX_POSITIONS=4` | `BALANCE_USDT=1000` = trần size (`size_base = min(trần, equity thật)`) |
| Kill-switch | bình thường (đã `python risk.py --reset` ngày 08/10) | |
| **Cổng LIVE** | ✅ **`live_ready.py` = HOAN THANH** (n=301 · PF(R) 1.616 · PF($) 1.492) | chi tiết §3/§4 |
| **Tự động hoá** | `STATE_SYNC_SEC=1800` · `AUTO_LIVE_ARMED=true` · `AUTO_LIVE_MIN_EQUITY=10` | `state_sync.py` mỗi 30 phút: ghi `STATE.md` + push GitHub + kiểm tra cổng; khi sang LIVE thì **áp mức rủi ro theo ví thật** (§11.1) |

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

---

## 8. Việc đang mở / tiếp theo

- [x] **Đủ n≥300** (n=301) → `live_ready.py` = `HOAN THANH` (09/10 00:07).
- [ ] **Chờ điều kiện tiền thật để tự sang LIVE**: `state_sync.py --auto-live` đã chạy mỗi 30 phút nhưng **KHÔNG đổi** vì chưa đọc được ví THẬT (API key hiện là key demo). Cần: **API key live + số dư ≥ `AUTO_LIVE_MIN_EQUITY` (100 USDT)** → khi đó tự đổi, không hỏi lại (§11).
- [ ] Theo dõi lỗi `api errors` (đã gây 2 lần `flatten + dung` tối 08/10) trước khi tin tưởng LIVE.
- [ ] (tuỳ chọn) Bật veto thật cho hội đồng khi có đủ bằng chứng **cả 2 nhóm** (`python agents.py --authority` phải `granted=True`), rồi `AGENT_VETO_SOURCE=COUNCIL`.
- [ ] (tuỳ chọn) Muse: nạp credit → tạo API key → `muse auth set` → điền lại `AGENT_COUNCIL_MUSE_CLI`.
- [ ] (tuỳ chọn) I/O offload: ghi journal async, cache OHLCV, Telegram ở thread riêng.

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







