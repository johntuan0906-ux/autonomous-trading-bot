# RESEARCH_1115 — Thị trường, quyết định LIVE, và 28 nguồn (đọc 15/11/2026)

**Nhiệm vụ (do người vận hành ban hành):** *"Xem xét thị trường để vào LIVE tăng lãi từ nay đến cuối
năm."* Báo cáo này trả lời bằng **số đo từ chính sổ của bot**, không bằng cảm tính; mỗi đề xuất ghi rõ
*áp dụng được gì / không áp dụng được gì* và **điều kiện đổi trạng thái**.

## 0. Kết luận trước (đọc 30 giây)

| Câu hỏi | Trả lời |
|---|---|
| Có nên bật LIVE **hôm nay**? | **KHÔNG.** Cổng đo được: PF($) **tính riêng lệnh bot** = 1,052 (< 1,1) trên 1.070 lệnh; 14 ngày 0,750; 30 ngày 0,481. |
| Vì sao trước đây tưởng đã đạt? | Số **gộp** có PF(R)=1,829 trông đẹp, nhưng 2.425/3.511 lệnh CLOSE là **lệnh tay** (−1.135,29 USDT) ⇒ số gộp **không đo bot**. |
| Có cơ hội nào thật? | Có: **lệnh bot đang dương** (+127,80 USDT/1.070 lệnh, PF($)=1,052) và **LIVE bot-only PF($)=1,172** trên 622 lệnh. Tức bot *gần* hoà-và-lãi, chưa đủ biên. |
| Đường đến 31/12 | 3 mốc tuần (§5): sửa số đo (xong 1 phần) → 14 ngày forward nhỏ → mở LIVE khi PF($) bot ≥1,1 **và** vốn ≥ 150–200 USDT. |

## 1. Thị trường & hiện trạng (số đo 15/11)

**1.1 Sổ của bot đã bị lệnh tay làm nhiễu (đo trực tiếp từ journal)**

| Instance | CLOSE | Lệnh BOT | PnL bot | Lệnh TAY | PnL tay | PF($) gộp | PF($) bot |
|---|---|---|---|---|---|---|---|
| TESTNET | 3.511 | 1.086 | **+44,72** | 2.425 | **−1.135,29** | 0,66–0,80 | **1,017** |
| LIVE | 702 | 622 | **+138,16** | 80 | −9,38 | 0,86–1,17 | **1,172** |

**1.2 Cổng vào LIVE (`python live_ready.py`, sau khi sửa 15/11)**

```
CONG HOAN THANH TESTNET -> LIVE | n_toan_bo=3054/300 | PF(R)=1.829 | PF($)=0.803
  RIENG LENH BOT               | n_bot=1070 | PF(R)=1.039 | PF($)=1.052 | PnL=+127.80
VERDICT: CHUA HOAN THANH
  [CHAN] PF($) 14 ngay [lenh BOT] = 0.750 < 1.1
  [CHAN] PF($) 30 ngay [lenh BOT] = 0.481 < 1.1
  [CHAN] PF(R) 14/30 ngay [lenh BOT] < 1.2
  [WARN] dang TESTNET; LIVE_CONFIRM=false
```

**1.3 Hiệu năng theo thời gian** (`python tools\perf_report.py`)

| Cửa sổ | n | PF | WR | MaxDD | Nhận xét |
|---|---|---|---|---|---|
| TESTNET 30 ngày | 2.567 | **0,66** | 47,0% | **131%** (ảo, do gộp lệnh tay) | không dùng được |
| TESTNET 7 ngày (bot) | 31 | **1,27** | — | — | mẫu nhỏ |
| LIVE 14 ngày | 114 | **1,86** | 52,6% | 0,18% | dương nhưng n=114 |
| LIVE 30 ngày (bot) | 67 | **1,57** | — | — | dương, mẫu nhỏ |

**1.4 Ràng buộc tiền học được từ số** (không phải ý kiến)
- Kỳ vọng hiện tại ≈ **0,037 USDT/lệnh** (LIVE 14 ngày) trong khi phí 2 chiều trên notional tối thiểu
  (≈15 USDT) là **≈0,015 USDT** ⇒ **~40% edge bị phí ăn**. Muốn có lãi *có ý nghĩa* phải tăng vốn/lệnh
  hoặc giảm số lệnh; **vốn 38 USDT là quá nhỏ** cho 4 vị thế × 1% risk.
- Với equity 150–200 USDT: risk 0,6% = 0,9–1,2 USDT ⇒ notional 60–80 USDT ⇒ phí ≈0,06–0,08 (≈8% edge).

**1.5 Thị trường — những gì bot thực sự nhìn thấy** (không có nguồn ngoài, nên chỉ nêu cái đo được)
- `market_regime` trong journal 14 ngày: phần lớn `?`/`NONE` (thiếu context từ OPEN) ⇒ **chỉ số theo
  regime chưa đáng tin** (đã có `perf_report` cảnh báo).
- Tín hiệu vĩ mô đang dùng: ATR%, funding, OI change, thanh lý, sentiment. **Ngưỡng cần theo dõi để
  không vào LIVE đúng lúc thị trường xấu**: `ATR% ≥ 2%` (đang chặn `SKIP_VOL`), funding âm mạnh
  (< −0,03%/8h) khi LONG, BTC regime DOWN + alpha LONG (đã có `mtf`/`btc_regime`).
- **Việc phải làm trước khi LIVE**: chốt 1 bảng "điều kiện thị trường được phép LIVE" (BTC 1D không
  DOWNTREND, ATR% trung vị < 3%, funding |x| < 0,05%) — hiện **chưa có** và sẽ thêm vào cổng (§4, mục 3).


## 2. 28 nguồn: đọc sâu cái gì, áp dụng được gì

Bảng chỉ ghi **việc làm được** hoặc lý do **không** làm. "Đọc sâu" = đã đọc README/kiến trúc, rút ra
được cơ chế cụ thể; "lướt" = chỉ đủ để kết luận không liên quan.

| # | Nguồn | Đọc | Áp dụng cho repo này | Mức |
|---|---|---|---|---|
| 1 | `tauricresearch/tradingagents` | sâu | (a) **chấm điểm bằng alpha so với benchmark** thay vì chỉ R; (b) **kỷ luật thời điểm**: quyết định chỉ được tính từ **nến đã đóng**; (c) "memory log" (đã có `lessons`); (d) sweep có `run_id` để chạy tiếp | ADOPT (a)(b) |
| 2 | `HKUDS/Vibe-Trading` | sâu | (a) hook **`_on_plan_rejected`** — mọi lệnh bị sàn từ chối phải có mã + lý do (đã làm ở B-056); (b) **hiệu chuẩn dung sai USD-M** khi so qty (đã có `quantize_qty`); (c) "no-progress stop" cho vòng lặp agent | ADAPT |
| 3 | `HKUDS/AI-Trader` | sâu | Mô hình **skill + platform** (agent đọc `SKILL.md` để tham gia). Repo đã có `skills/`; **không** áp dụng copy-trading/leaderboard (không kiểm chứng được lợi thế) | ADOPT một phần |
| 4 | `yongjunmun/Systematic-Trading-System` (trong topic options) | sâu | (a) **Deflated Sharpe** chống overfit khi thử nhiều setup; (b) **R-ladder dùng CHUNG bit-for-bit** giữa backtest và live; (c) sizing theo volatility | ADOPT (a) |
| 5 | `LLMQuant/awesome-trading-agents` | sâu | Bản đồ 3 tầng (Agents · MCP · Skills) + tiêu chí "chọn cái có artifact công khai, không chọn cái chỉ có bài viết" | dùng làm tiêu chí |
| 6 | `kevmyung/swing-trading-agent` | sâu | Kiến trúc **3 nhịp** (EOD signal → sáng đặt lệnh → trong ngày quản lý) + `playbook/` tách khỏi `agents/`. Repo đã có nhịp vòng 5 phút; **không** bê AWS/React | ADAPT (playbook) |
| 7 | `topics/agentic-security` (90 repo) | sâu | Trước khi cho agent tiêu tiền thật: **chặn prompt-injection ở tool-call**, **sandbox quyền**, **audit log tool**. Ta đã có `SECURITY_AUDIT.md` + F-01..F-06; thiếu: **kiểm tra tool-call do LLM sinh** (hiện LLM không sinh lệnh) | giữ nguyên + ghi |
| 8 | `Piebald-AI/claude-code-system-prompts` | lướt-sâu | Kỹ thuật prompt: "verify before claim", "state uncertainty", "prefer tools over guesses". **Đây là lỗ hổng harness đã ghi (AGENTS.md §Harness)**: ta không đo chất lượng prompt | ADAPT (đo, không copy) |
| 9 | `topics/options-trading-bot` (31 repo) | sâu | Chủ yếu options (IV/Greeks/hedge). Repo futures-perp **không dùng**; chỉ mượn 2 ý: **vol-target sizing**, **walk-forward** | phần lớn NO |
| 10 | `alishahryar1/free-claude-code`, `Egonex-AI/Understand-Anything`, `milind-soni/OpenMausBot`, `yibie/awesome-rea`, `Generated-Computers/Locals`, `dstrml/wu`, `OpenSparX/MasterAgent`, `C4rohan/Lampline`, `SoMarkAI/OXR`, `xerj-org/xerj`, `yetone/magpie`, `mksglu/context-mode`, `storytold/craft-anything`, `wici-ai/inferssd`, `herdrdev/herdr`, `divagr18/qwenputer`, `nomic-ai/gpt4all`, `JustVugg/colibri`, `tradingagents-ai.github.io`, `tradingagents.cc` | lướt | Đây là **hạ tầng agent/lập trình/UI/local-inference**, không phải edge giao dịch. Đã thử hướng local LLM (B-051/B-052) ⇒ `local/llama3.2-3b` value_r **−1,303** nên **không** đưa vào hội đồng | NO (có bằng chứng) |

**Điều hội đồng KHẲNG ĐỊNH sau khi đọc 28 nguồn:** không có repo nào trong danh sách tạo ra **edge
giao dịch** miễn phí. Cái đáng lấy là **kỷ luật đo lường** (benchmark, no-lookahead, deflated sharpe,
tách số bot/tay) — đúng những chỗ repo này còn yếu.

## 3. 12 việc đáng làm nhất (xếp theo giá-trị/công, cho mục tiêu "vào LIVE")

| # | Việc | Nơi sửa | Trạng thái |
|---|---|---|---|
| 1 | **Cổng LIVE chỉ tính lệnh BOT** (bỏ 2.425 lệnh tay khỏi PF) | `live_ready.py` (`bot_pairs`, `bot_stats`) | ✅ **xong 15/11** + 4 test |
| 2 | **Bỏ nến đang hình thành** khi tính tín hiệu (chống "nhìn trước") | `exchange.fetch_ohlcv` / `turbo_demo` | ⏳ kế tiếp |
| 3 | **Điều kiện thị trường được phép LIVE** (BTC 1D không DOWN, ATR% trung vị < 3%, funding |x|<0,05%) | `live_guard.py` | ⏳ |
| 4 | **Alpha so với BTC buy&hold** cho mỗi lệnh (không chỉ R) | `tools/perf_report.py --benchmark` | ⏳ |
| 5 | **Deflated Sharpe** với `n_trials` = số setup đã thử (8) | `tools/perf_report.py` | ⏳ |
| 6 | **Bảng "điều kiện vào/ra" tách khỏi code** (`playbook/`) cho agent đọc | `skills/` + `AGENTS.md` | ⏳ |
| 7 | Tăng vốn LIVE lên **150–200 USDT** trước khi bật (phí ăn 40% edge ở 38 USDT) | quyết định của người | ⏳ |
| 8 | **Forward-test 14 ngày** ở 0,4% risk, 3 cặp, ghi riêng sổ bot | vận hành | ⏳ |
| 9 | Ghi **mã lý do** cho mọi lệnh bị từ chối (đã có `ORDER_REJECT` + 13 nhóm) | `exchange.classify_error` | ✅ xong (B-056) |
| 10 | **Số riêng bot** trong `perf_report` (không chỉ cổng) | `tools/perf_report.py --bot-only` | ⏳ |
| 11 | Đo **chất lượng prompt** trước/sau mỗi lần sửa (`council_eval --hours 720`) | `tools/council_eval.py` | luật đã ghi |
| 12 | **Không** thêm model/hạ tầng mới trước khi PF($) bot ≥ 1,1 | — | luật |

## 4. "ĐỪNG LÀM" (kèm bằng chứng nội bộ)

| Đề xuất hấp dẫn | Vì sao KHÔNG |
|---|---|
| Bật LIVE ngay vì "PF(R) 1,83 > 1,2" | PF(R) gộp; **PF($) bot 1,052** và 14/30 ngày **0,75 / 0,48** |
| Copy-trading / leaderboard (AI-Trader) | Không kiểm chứng được lợi thế của người dẫn; thêm rủi ro đối tác |
| Đổi sang options/IV/Greeks (topic options) | Sàn đang dùng là USD-M futures; phải mở tài khoản khác + edge chưa đo |
| Chạy LLM local thay hội đồng (gpt4all/colibri/qwenputer) | Đã đo: `local/llama3.2-3b` value_r **−1,303**, 3/3 lần không bỏ phiếu |
| Thêm agent/UI mới (OXR, craft-anything, MasterAgent) | Không tạo edge; UI thêm tầng có thể chết mà bot không biết |

## 5. Quyết định LIVE + đường đến 31/12 (3 mốc, có điều kiện đo được)

**Quyết định hôm nay: GIỮ LIVE Ở CHẾ ĐỘ NHỎ/QUAN SÁT, KHÔNG tăng vốn, KHÔNG hạ chuẩn cổng.**
Lý do: 2.425 lệnh tay đang làm số gộp sai; số thật của bot là PF($) 1,052 (14 ngày 0,750; 30 ngày 0,481).
Bật LIVE lúc này = đánh cược vào một con số **đã biết là sai nguồn**.

| Mốc | Thời gian | Việc | Điều kiện ĐẠT (đo được) |
|---|---|---|---|
| **M1 — Số đo sạch** | 15–22/11 | (a) cổng chỉ tính lệnh bot ✅; (b) bỏ nến đang hình thành; (c) `perf_report --bot-only`; (d) dọn 1 lần lệnh tay khỏi sổ TESTNET bằng `reconcile.py` (chỉ ghi bù, không xoá) | `live_ready` in được `n_bot` + PF($) bot; 14 ngày **PF($) bot ≥ 1,10**, PF(R) bot ≥ 1,20 |
| **M2 — Forward 14 ngày** | 22/11–06/12 | chạy TESTNET 0,4% risk, 3 cặp thanh khoản nhất (BTC/ETH/SOL), **không** lệnh tay; ghi sổ riêng để so | PF($) bot ≥ 1,10 · MaxDD ≤ 5% · WR 45–60% · không có ngày mất > 2% |
| **M3 — Mở LIVE nhỏ** | 06–20/12 | bật `BINANCE_TESTNET=false`, `LIVE_CONFIRM=true`, vốn **≥ 150 USDT**, 2 vị thế, risk **0,4%**, leverage 5 | 7 ngày đầu: không ngày nào lỗ > 1,5%; PF($) ≥ 1,0; SL/TP đủ 2/2 mỗi vị thế |
| **M4 — Tăng dần** | 20–31/12 | chỉ tăng khi M3 đạt: +1 vị thế, risk 0,6% | PF($) duy trì ≥ 1,1 và MaxDD ≤ 5% |

**Các cổng code đã có để M3 không thể "quên"**: `live_guard.py` (n≥50, PF≥1,2, risk≤2%, lev≤10,
`LIVE_CONFIRM=true`, kill-switch sạch) + `live_ready.py` (PF($) bot ≥1,1, n≥300, 2 hướng đủ mẫu).

**Điều hội đồng KHÔNG hứa**: không hứa "tăng lãi đến cuối năm". Số hiện tại cho thấy bot **gần hoà**;
mọi cam kết lợi nhuận sẽ là bịa. Việc hội đồng bảo đảm là: **không vào LIVE bằng số sai**, và mỗi tuần
có báo cáo PF($) bot để bạn quyết.

## 6. Nguồn (đọc 15/11/2026)

Đọc sâu: TradingAgents (arXiv 2412.20138) · Vibe-Trading · AI-Trader · Systematic-Trading-System ·
awesome-trading-agents · swing-trading-agent · topics/agentic-security · topics/options-trading-bot ·
claude-code-system-prompts.
Lướt (kết luận: không liên quan edge): free-claude-code · Understand-Anything · OpenMausBot · awesome-rea ·
Locals · wu · MasterAgent · Lampline · OXR · xerj · magpie · context-mode · craft-anything · inferssd ·
herdr · qwenputer · gpt4all · colibri · tradingagents-ai.github.io · tradingagents.cc.
Trong repo: `RESEARCH_1211.md` (80 link đợt 12/11), `REPO_IDEAS.md` §29, `SECURITY_AUDIT.md`.

| Tăng đòn bẩy để "tăng lãi" | `live_guard` chặn lev>8 khi PF<1,5 — đúng; đòn bẩy không sửa được PF($) |
| Sửa prompt hội đồng rồi tin là tốt hơn | Chưa có số đo prompt (AGENTS.md §Harness); phải chạy `council_eval` trước/sau |
