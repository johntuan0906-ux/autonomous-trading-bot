# CONTEXT.md — Ngữ cảnh hiện tại của dự án (đọc file này ĐẦU TIÊN)

> **Mục đích**: một chỗ duy nhất ghi *trạng thái + kiến thức đã kiểm chứng* của dự án, để khi mở lại VS Code / mở phiên chat mới (người hoặc AI) là **nhớ lại ngay**, không phải suy đoán lại.
> **Cập nhật lần cuối**: 08/10/2026 ~23:40 (sau commit `ee25859`).
> **Quy tắc vàng**: mọi con số ở đây **có ngày** và **kèm lệnh tự kiểm chứng**. Số liệu hiệu suất thay đổi mỗi ngày → chạy lại lệnh ở §3 trước khi kết luận.

---

## 0. Khôi phục ngữ cảnh trong 60 giây (dành cho phiên AI mới)

Đọc theo thứ tự: **CONTEXT.md (file này) → AGENTS.md → README.md mục 13–14**. Sau đó chạy:

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

## 2. Trạng thái hiện tại (08/10/2026 ~23:40)

| Hạng mục | Giá trị | Ghi chú |
|---|---|---|
| Chế độ | `BINANCE_TESTNET=true`, `DRY_RUN=false` | lệnh thật trên **tài khoản demo** |
| Bot | supervisor PID `58068` + `turbo_demo` (tiến trình con) | tự restart khi crash; lock `logs/.supervisor.lock` |
| Ví demo | **4631.8 USDT** | uPnL −12.82 tại thời điểm ghi |
| Vị thế đang mở | **7**: DOGE, BTC, LINK, AVAX, ADA, XRP, SOL (toàn SHORT) | SL/TP trên sàn **bị chặn `-4045`** → monitor mềm bảo vệ |
| Hội đồng AI | **15 model** (12 Cline + 2 Qwen CLI + 1 Local Ollama) | Copilot bị chặn tới 01/11; **Muse đã tắt hoàn toàn** |
| Quyền veto của AI | **CHƯA cấp** (`granted=False` cho cả SETUP và COUNCIL) | hội đồng chỉ ghi `[shadow]`; `BLOCKED_VETO=0` |
| Tham số rủi ro | risk 1%/lệnh, trần tổng 2%, `LEVERAGE=8`, `MAX_POSITIONS=4` | `BALANCE_USDT=1000` = trần size (`size_base = min(trần, equity thật)`) |
| Kill-switch | bình thường (đã `python risk.py --reset` ngày 08/10) | |

## 3. Hiệu suất hiện tại (đọc từ `logs/journal.jsonl`, ngày 08/10)

```
CONG HOAN THANH TESTNET -> LIVE | n_toan_bo=291/300 | PF(R)=1.548 | PF($)=1.421
  7 ngay    217  67.7%  PF(R)=1.865  PF($)=1.759  E(R)=+0.1398  PnL=+248.50$
  14 ngay   268  66.0%  PF(R)=1.497  PF($)=1.355  E(R)=+0.0969  PnL=+178.24$
  30 ngay   291  66.7%  PF(R)=1.548  PF($)=1.421  E(R)=+0.1082  PnL=+233.34$
VERDICT: CHUA HOAN THANH  ->  [CHAN] n lenh dong toan bo = 291 < 300 (chi con 9 lenh!)
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

---

## 8. Việc đang mở / tiếp theo

- [ ] **Chờ đủ n=300** (hiện 291) → chạy `python live_ready.py`; chỉ khi `HOAN THANH` mới bàn chuyện sang LIVE (§4).
- [ ] Theo dõi lỗi `api errors` (nguồn của 2 lần flatten tối 08/10) trước khi nghĩ tới LIVE.
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


