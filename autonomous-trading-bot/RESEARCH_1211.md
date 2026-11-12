# Nghiên cứu 80 repo/ link (12/11/2026) — cái gì THỰC SỰ áp dụng được cho repo này

Mục đích: trả lời "hội đồng đọc các repo này xem dự án áp dụng được gì" bằng **quyết định cụ thể gắn
vào file/hàm đang có**, không phải danh sách khen.

**Phương pháp & giới hạn (nói trước cho minh bạch)**

- Đọc kỹ (README + cấu trúc thư mục) **47 repo**. Các link còn lại rơi vào **3 mẫu lặp** đã đọc đại diện
  đầy đủ: (a) *second-brain* Obsidian/markdown (12 repo — cùng một kiến trúc), (b) *skill-pack*
  (SKILL.md + marketplace, 8 repo), (c) *agent desktop UI / agent-OS* (10 repo), cộng vài link không
  phải repo cụ thể (`topics/agile-development`, `orgs/ucberkeley`). Không có kết luận nào cho repo chưa
  đọc mà lại giả vờ đã đọc.
- Mọi con số "đo được" dưới đây là **số của repo này** (journal, `council_eval`, `probe_cline`), không
  phải số của repo được đọc.
- Thang quyết định: **ADOPT** (làm ngay, rẻ, có test) · **ADAPT** (lấy ý, viết lại theo code mình) ·
  **LATER** (đúng nhưng chưa cần) · **SKIP** (không hợp, kèm lý do).

---

## 1. Bảng quyết định (12 việc đáng làm nhất, xếp theo tỉ lệ giá-trị/ công)

| # | Nguồn | Ý áp dụng vào repo này | Mức | Nơi sửa | Vì sao đáng |
|---|---|---|---|---|---|
| 1 | `Archive228/foreman` | 3 chỉ số "crew đang nói dối" còn **thiếu** trong `selfops`: **roster drift** (model khai trong `.env` ≠ model thật sự bỏ phiếu), **dormant model** (0 phiếu trong N giờ), **silent routine** (việc định kỳ không chạy) | ADOPT | `tools/selfops.py`, `tools/council_gaps.py` | Đúng lớp lỗi đã tái diễn 4 lần: "hội đồng im lặng" (B-051/B-052) mà không ai báo |
| 2 | `anthropics/skills` + `claude-plugins-official` | Đóng gói 4 runbook đã có thành `skills/<name>/SKILL.md` (frontmatter `name`+`description`): `close-dust`, `council-silent`, `reconcile-first`, `drift-report` | ADOPT | thư mục mới `skills/` | Quy ước "gặp X thì chạy Y" hiện nằm rải trong `OPERATIONS.md` 300 dòng; skill = cùng nội dung nhưng agent nào cũng nạp được |
| 3 | `ranaroussi/quantstats` | `tools/perf_report.py`: 8 chỉ số (CAGR/sharpe/sortino/calmar/maxDD/ulcer/PF/expectancy) từ **equity theo ngày** + phân rã theo `setup/regime` (tái dùng bucket của `lessons.py`) | ADAPT | `tools/perf_report.py` + test | Repo đã có `pandas` (qua ccxt) nhưng chỉ có PF(R) thô; thiếu chỉ số risk-adjusted để so sánh thật |
| 4 | `freqtrade` (protections) | **Cooldown theo cặp sau 1 lệnh thua** (như `CooldownPeriod`/`StoplossGuard`), khác gate theo bucket hiện có | ADAPT | `entries_gate.py`, `config.py` (`PAIR_COOLDOWN_MIN`) | `risk.py` chỉ trip theo *tổng* lỗi; một cặp "nóng" vẫn vào lại ngay lần sau |
| 5 | `ccxt` (error taxonomy) | Ánh xạ **mã lỗi sàn → lớp lỗi** (`InsufficientFunds`, `InvalidOrder`, `RateLimit`, `Network`) thay cho chuỗi `if code == -2022 …` rải rác | ADAPT | `exchange.py`, `trade_mgmt.py` | Đã gặp 6 mã (−2022/−4164/−4120/−2021/−4045/quota); mỗi mã mới lại sửa một chỗ |
| 6 | `gist karpathy/llm-wiki` + `akitaonrails/ai-memory` | `tools/lessons_wiki.py`: sinh `LESSONS.md` **có trích dẫn** (`decision_id`) + **checker từ chối số không khớp nguồn** (tái dùng pattern `golden_set`) | ADAPT | `tools/lessons_wiki.py` | `LESSONS.md` hiện viết tay ⇒ nguy cơ "số tự nghĩ ra"; karpathy nêu đúng điểm này |
| 7 | `google/elephant-goldfish-model` (EGM) | "Goldfish reviewer" = reviewer có **context mới**; repo đã có (debate vòng 2 + golden). Bổ sung: **drift report thành skill** chuẩn hoá | ADOPT (đóng gói) | `skills/drift-report/SKILL.md` → `tools/drift_docs.py` | EGM coi đây là skill chính thức; ta có tool nhưng thiếu vỏ để agent khác dùng |
| 8 | `ruvnet/ruflo` | **Byzantine quorum** (loại nút `value_r ≤ 0` khỏi kết quả nhưng vẫn ghi journal) repo đã làm; bổ sung **"witness/manifest"**: hash danh sách test chốt vào `golden/baseline.json` để phát hiện test bị xoá lặng lẽ | ADAPT | `tools/bug_catalog.py --manifest`, `golden/baseline.json` | Chống "xoá test cho xanh" — đúng ý `ruflo verify` |
| 9 | `cloudflare/security-audit-skill` | Checklist audit 6 pha; repo **có tiền thật**: key trong `.env`, đường LIVE, `LIVE_CONFIRM` | ADOPT (1 lần) | `SECURITY_AUDIT.md` | Một lần chạy rẻ hơn một lần mất key (đã từng phải thu hồi key Blockworks) |
| 10 | `walkinglabs/learn-harness-engineering` | Khung 5 subsystem (instructions/tools/environment/state/feedback) để soi chỗ trống: repo thiếu *feedback cho chất lượng prompt*, không phải cho code | ADAPT | `AGENTS.md` mục "harness" | Tránh thêm tính năng khi lỗ hổng thật nằm ở vòng phản hồi |
| 11 | `bmoscon/cryptofeed` | **Gap detection** trên nến: đếm số nến thiếu trong cửa sổ tín hiệu (song song `freshness.data_age`) | ADAPT | `freshness.py` | `data_age` bắt "dữ liệu cũ", không bắt "dữ liệu thủng lỗ" |
| 12 | `HAEGONG/grok-bot-profiles` | Mỗi agent một dòng **"approval boundary"** (việc gì agent KHÔNG được tự quyết) trong `AGENTS.md` | ADOPT | `AGENTS.md` | Repo đã ghi "agent không sửa risk.py"; chuẩn hoá thành bảng để agent mới không đoán |


---

## 2. Nhóm A — Harness & verification (ruflo, learn-harness-engineering, EGM, foreman,
`oh-my-claudecode`, `security-audit-skill`)

**Điều đáng học nhất không phải tính năng, mà là cách chúng định nghĩa "bằng chứng".**

- `foreman` mở đầu bằng 12 "cách một crew có thể nói dối bạn", mỗi tính năng đóng đúng một cách.
  Ba cách repo này **chưa đóng**:
  1. *Roster drift*: `.env` khai 5 model, thực tế 1 model bỏ phiếu (đã xảy ra: B-051, B-052).
     Cách đóng: `selfops` so `_council_models(cfg)` với tập model **thật sự có phiếu** trong 24h.
  2. *Dormant model*: có trong roster nhưng 0 phiếu N giờ (không phải "treo", mà là "im").
  3. *Silent routine*: việc định kỳ đáng lẽ chạy mà `logs/autonomy.jsonl` không có dấu vết.
- `learn-harness-engineering` (24,4k★): 5 subsystem. Đối chiếu repo: instructions = `AGENTS.md` +
  `CONTEXT.md` ✅; tools = `tools/*.py` ✅; environment = `.env` 2 instance ✅; state =
  `managed_state`/`journal` ✅; feedback = `golden_set` + `drift_docs` ✅ **nhưng chỉ cho code**, chưa
  cho *chất lượng câu hỏi gửi council* (prompt). Đó là chỗ trống thật. Repo họ còn có skill
  `harness-creator` và `tools/audit-harness.sh` — chạy một lần để đối chiếu khách quan.
- `EGM`: reviewer phải là **context mới**, và "drift report" là skill chính thức. Repo có debate vòng 2
  (`multi_model_council`) và `drift_docs.py`; thiếu vỏ skill + thiếu *luật* "reviewer không được là
  author" cho tài liệu (CONTEXT do agent viết, agent khác kiểm bằng `drift_docs` — nay là quy ước,
  nên thành luật trong `AGENTS.md`).
- `cloudflare/security-audit-skill` (71k★): "agent kiểm không phải agent tìm", "severity cần impact".
  Áp dụng: mọi phát hiện bảo mật trong repo phải có `file:line` + đường khai thác, không "có thể".
- `oh-my-claudecode` (40,8k★): hooks/guards để agent không lách luật. Repo không dùng Claude Code hooks,
  tương đương đã có: `bug_catalog --check` + `golden_set --check` trong chuỗi trước commit. Đủ.

## 3. Nhóm B — Skills/plugin packaging (anthropics/skills, claude-plugins-official,
knowledge-work-plugins, openclaw/clawhub, obsidian-skills, addyosmani/agent-skills,
mattpocock/skills, cloudflare/security-audit-skill)

Định dạng chung: một thư mục = một `SKILL.md`, frontmatter **chỉ 2 field bắt buộc** (`name`,
`description`) + phần hướng dẫn; có thể kèm `scripts/`, `references/`. Marketplace chỉ là JSON trỏ tới
thư mục. Ba repo skills lớn (anthropics 194k★, addyosmani 116k★, obsidianmd 52k★) đều **không** cần
runtime — chỉ markdown. `clawhub` thêm phần đáng chú ý: frontmatter khai `requires.env`, `requires.bins`
và **phân tích bảo mật đối chiếu khai báo với hành vi thật**.

**Áp dụng**: tạo `skills/` với 4 skill (mỗi cái ≤ 60 dòng, chỉ gọi tool đã có, kèm `requires.bins`):

- `skills/close-dust/SKILL.md` — "vị thế < 5 USDT không đóng được": thứ tự thử + mã lỗi đã đo.
- `skills/council-silent/SKILL.md` — "hội đồng im lặng": chạy `probe_cline.py --copilot` TRƯỚC khi sửa
  code; đọc 4 mã `MODEL_GATED / PAYMENT / AUTH / MODEL_FORMAT`.
- `skills/reconcile-first/SKILL.md` — "kết luận về tiền": bắt buộc `reconcile.py` + `positions.py`.
- `skills/drift-report/SKILL.md` — "tài liệu ↔ code": `drift_docs.py --check`, không nới ngưỡng.

Lợi ích thật: 3 lỗi này đã tái diễn ≥ 4 lần; SKILL.md là bản duy nhất agent nào (Claude/Codex/Copilot)
cũng nạp được, không phụ thuộc một `OPERATIONS.md` dài.

## 4. Nhóm C — Trading/data (freqtrade, vectorbt, quantstats, cryptofeed, ccxt, hypergrok-trading-desk,
multiBot, grok-factory, botroster)

- **freqtrade** (56,8k★): giá trị thật nằm ở **`protections`** (StoplossGuard, CooldownPeriod,
  MaxDrawdown, LowProfitPairs) — mỗi cái là một luật *thời gian*, khác gate theo thống kê của repo.
  Đề xuất #4: `PAIR_COOLDOWN_MIN` (mặc định 60′) sau khi một cặp đóng bằng SL. Hyperopt/backtesting của
  họ không cần vì repo có `backtest.py` + journal thật.
- **quantstats** (7,9k★): 3 module `stats/plots/reports`; cảnh báo của chính họ: metric **theo kỳ**
  (ngày) khác metric **theo lệnh** — báo cáo phải nói rõ đang báo cái nào. Đề xuất #3.
- **vectorbt** (9,8k★): mạnh khi quét hàng nghìn tham số (Numba + Rust). Repo có ~1.500 lệnh thật và đã
  có `learner/sweep`; thêm numba/rust = **SKIP** cho tới khi cần quét >10⁴ tổ hợp.
- **cryptofeed** (3,0k★): chuẩn hoá dữ liệu + checksum + gap. Repo chỉ cần phần **gap** (#11); không đổi
  sang websocket handler của họ (bot chạy REST theo vòng).
- **ccxt** (44,9k★): phân cấp lỗi `BaseError → NetworkError/ExchangeError → {InvalidOrder,
  InsufficientFunds, RateLimitExceeded…}`. Đề xuất #5: dùng chính class của ccxt (đã là dependency) thay
  vì so mã chuỗi; mã Binance vẫn giữ trong log để `reconcile` đọc. ccxt cũng có **MCP server** (opt-in,
  audit journal, notional cap) — mô hình đáng chép cho "agent được phép làm gì".
- **hypergrok-trading-desk** (501★): "research trước, execution cần ticket được duyệt" + 7 role/17 skill
  — repo đã tương đương (`LIVE_CONFIRM`, `AGENTS.md`). Điểm đáng chép: họ **công bố hash** của
  profile/skill (provenance) → trùng ý #8.
- **multiBot / grok-factory / botroster**: orchestration "1 điều phối + N worker CLI" — council hiện là
  *bỏ phiếu song song*, không phải *phân việc tuần tự*; chỉ hữu ích nếu sau này có "shift" dài (LATER).

## 5. Nhóm D — Local model & memory (colibri, airllm, bitnet, kimi-k3-in-c, ODS, MetaClaw, ai-memory,
karpathy gist, PageIndex, second-brain ×12)

- **Local inference (colibri / airllm / bitnet / kimi-k3-in-c)**: kỹ thuật thật (MoE hot/warm/cold, nạp
  từng lớp, ternary CPU kernels, 2,78T tham số trong 8,24 GB RAM) nhưng **không giải bài toán của repo**:
  repo cần 1 phiếu JSON đáng tin, không cần model lớn. Bằng chứng nội bộ: `local/llama3.2-3b-local` có
  `value_r = −1,303` (64 phiếu) ⇒ đã bị `AGENT_COUNCIL_IGNORE` loại. **SKIP**, ghi lại để lần sau không
  ai đề xuất lại.
- **MetaClaw** (3,5k★): 5 loại memory (`episodic / semantic / preference / project_state /
  working_summary`) + consolidation định kỳ. Repo đã có `journal`=episodic, `LESSONS.md`=semantic,
  `.env`=preference, `STATE.md`=project_state. Thiếu `working_summary` (bản tóm tắt cuộn) — **LATER**,
  khi `CONTEXT.md` vượt ~1.000 dòng (nay ~615).
- **karpathy llm-wiki** (gist 5k★) + biến thể có checker: "wiki biên soạn một lần, có trích dẫn, checker
  từ chối số không có trong nguồn" → đề xuất #6. Đây là ý **đắt giá nhất trong nhóm này**: repo đã 3 lần
  phải sửa "số trong tài liệu lệch code" (`drift_docs` sinh ra từ đó).
- **PageIndex** (40,4k★): RAG không vector, index theo cây tài liệu, tiết kiệm 97% token trên tài liệu
  dài. Hay, nhưng `LESSONS.md` + `CONTEXT.md` của repo chỉ vài trăm KB; `grep` nhanh hơn và ít rủi ro.
  **LATER** (mốc: khi tài liệu > ~2 MB hoặc có PDF báo cáo).

## 6. Nhóm E — Agent UI / runtime / profile (Orkas, AionUi, botroster, oxicode, cherry-studio,
PhoneZero, agent-org-chart, grok-bot-profiles, baalda, HugAgentOS, omnigent, multiBot)

- Đây là **sản phẩm desktop/CLI cho người dùng**, không phải thư viện để nhúng. Repo chạy headless 2
  instance trên 1 máy ⇒ thêm UI là tăng bề mặt lỗi. **SKIP** toàn nhóm, trừ 2 ý khái niệm:
  - `grok-bot-profiles`: tách **spec / implement / verify** + "approval boundary" rõ ràng → #12.
  - `omnigent` (11,4k★): "policy stack 3 tầng (server/agent/session), tầng chặt hơn được kiểm trước" —
    repo có tương đương: `config` (env) → `risk` → `entries_gate`; chỉ nên *ghi lại thứ tự*, không xây
    policy engine.
- `PhoneZero` (điện thoại tự động), `n8n self-hosted-ai-starter-kit` (docker compose low-code): không
  liên quan tới bot giao dịch.
- `agent-org-chart`: catalog "org chart" cho agent — ý hay nhưng repo chỉ 5 vai (critic/arbiter/review/
  macro/reflect) đã đủ; thêm vai là thêm chi phí mỗi lệnh.

## 7. Nhóm F — Cái KHÔNG nên làm (và vì sao) — để lần sau khỏi bàn lại

| Đề xuất hấp dẫn | Vì sao không (bằng chứng nội bộ) |
|---|---|
| Thêm model vào council để "đa dạng" | Đo 12/11: `minimax-m3` prec **0,500** (ném đồng xu), `muse-spark-1.3` 3/3 **không ra phiếu**, `local 3B` value_r **−1,303** |
| Chuyển sang vectorbt để backtest "chuẩn" | Cần numba/rust; repo có 1.500 lệnh thật + `learner.sweep`; lợi ích chỉ khi >10⁴ tổ hợp |
| Thêm vector DB / RAG (PageIndex, ai-memory server) | `LESSONS.md` vài trăm dòng; `grep` nhanh hơn, không thêm dependency |
| Chạy LLM local (colibri/airllm/bitnet) | Cần ≥16–32 GB RAM/VRAM, độ trễ cao; phiếu JSON của model nhỏ đã đo là **phản tác dụng** |
| Dùng agent desktop (Orkas/AionUi/botroster) để "quản" bot | Đã có `tools/ops.py`, `restart_bot.py`, `selfops.py`; UI thêm tầng có thể chết mà bot không biết |
| Nâng gói Copilot rồi sửa `.env` thủ công | Đã thiết lập sẵn (B-052): chạy `probe_cline.py --copilot --candidates`, hội đồng tự mở rộng |

## 8. Roadmap 3 bước (mỗi bước có tiêu chí nghiệm thu)

**Bước 1 — "đóng 3 cách crew nói dối" (nửa ngày).** `selfops` thêm `roster_drift`, `dormant_model`,
`silent_routine`; mỗi cái 1 test chốt; nếu phát hiện lớp lỗi mới thì thêm vào `bug_catalog`.
*Nghiệm thu*: chạy trên dữ liệu thật 12/11 phải báo đúng "roster 5 model, thực tế 1 model có phiếu".

**Bước 2 — runbook thành skill + audit bảo mật (1 ngày).** `skills/{close-dust,council-silent,
reconcile-first,drift-report}/SKILL.md`; `SECURITY_AUDIT.md` theo checklist Cloudflare (6 pha, có
`file:line`). *Nghiệm thu*: 4 thư mục skill hợp spec (`name`+`description`), audit có ≥1 phát hiện thật
hoặc kết luận "không có" kèm bằng chứng.

**Bước 3 — đo lường tử tế (1–2 ngày).** `tools/perf_report.py` (8 chỉ số, tách theo setup/regime),
`PAIR_COOLDOWN_MIN` trong `entries_gate`, ánh xạ lỗi ccxt. *Nghiệm thu*: báo cáo chạy trên journal thật;
cooldown có test "cặp vừa SL không vào lại trong 60′"; mọi mã lỗi sàn đi qua 1 hàm phân loại duy nhất.

## 9. Nguồn (đọc 12/11/2026)

ruflo · anthropics/skills · claude-plugins-official · knowledge-work-plugins · financial-services ·
agent-org-chart (×2) · omnigent · MetaClaw · learn-harness-engineering · freqtrade · vectorbt ·
quantstats · cryptofeed · ccxt · hypergrok-trading-desk · multiBot · grokbot-x · colibri · airllm ·
bitnet · kimi-k3-in-c · google/elephant-goldfish-model · PageIndex · ODS · karpathy gist · grok-factory ·
grok-bot-second-brain · foreman · PhoneZero · botroster · grok-bot-profiles · reverse-engineering-bot ·
baalda · Orkas · aionui · clawhub · oxicode · oh-my-claudecode · HugAgentOS · offload-mcp-server ·
agent-second-brain · ai-memory · COG-second-brain · obsidian-second-brain · obsidian-skills ·
addyosmani/agent-skills · cloudflare/security-audit-skill · n8n self-hosted-ai-starter-kit.

Biến thể cùng mẫu (không đọc riêng, đã suy từ đại diện): `claude-second-brain`, `open-second-brain`,
`wiki-master`, `obsidian-mind`, `obsidian-claude-pkm`, `obsidian-agent-vault-template`,
`karpathy-llm-wiki`, `second-brain-os`, `ai-second-brain`, `llm-wiki`, `gbrain`, `mattpocock/skills`,
`cherry-studio`, `724-office`, `voyager`, `dsh-superagent-prototype`, `awesome-copilot`,
`claude-quickstarts`, `prompt-eng-interactive-tutorial`, `offload` (bản khác), `topics/*`.

