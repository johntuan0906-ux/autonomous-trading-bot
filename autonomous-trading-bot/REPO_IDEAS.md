# REPO_IDEAS.md — 9 repo tham khảo: áp dụng được gì cho dự án này

> Đọc 12/10/2026 theo yêu cầu. Mỗi mục: repo là gì → **áp dụng cụ thể** (P1 = làm
> ngay/đã làm, P2 = làm khi rảnh, P3 = chỉ để tham khảo, KHÔNG cài).
> Nguyên tắc: chỉ thêm phụ thuộc khi thật sự giảm rủi ro/ thời gian vận hành.

| Repo | Áp dụng | Ưu tiên |
|---|---|---|
| mattpocock/skills | Bộ "skill" nhỏ cho agent (triage, diagnosing-bugs, tdd, retro, handoff, wizard) | **P1** |
| cocoindex-io/cocoindex-code | Index AST repo để agent tìm code nhanh/thẻ context | **P1** |
| dzhng/jevgrep | Tìm code bằng câu hỏi ngữ nghĩa (~30% rẻ hơn cho agent) | P2 |
| rohitg00/ai-engineering-from-scratch | Eval framework + safety harness + metrics cho hội đồng AI | **P1** |
| donnemartin/system-design-primer | Cache-aside/TTL, circuit breaker, bulkhead, rate limit | **P1** |
| revfactory/harness | Mẫu kiến trúc nhóm agent + A/B có/không skill | P2 |
| camel-ai/camel | Multi-agent framework (memory, toolkits, RAG) | P3 |
| collabs-inc/collab-public | IDE canvas cho agent (thay khi shell VS Code quá tệ) | P3 |
| morluto/rea | Reverse-engineering (MCP + skills) | P3 |

---

## 1. mattpocock/skills — "skill" cho agent (P1)

**Là gì**: các skill `.md` nhỏ, soạn theo kinh nghiệm kỹ thuật, dùng cho bất kỳ
model: `triage`, `diagnosing-bugs`, `tdd`, `code-review`, `retro`, `handoff`,
`domain-modeling`, `codebase-design`, `research`, `wizard`.

**Áp dụng cụ thể cho dự án này** (thêm vào `AGENTS.md` / `.clinerules`):

- **`diagnosing-bugs`** → đúng vấn đề của chúng ta: "dựng vòng phản hồi đỏ được
  trên bug này" trước khi sửa. Bản địa hoá: mọi bug hạ tầng phải có **1 lệnh tái
  hiện** (vd `python tools/ops.py --minutes 6` chỉ ra FETCH_TIMEOUT) — đã làm.
- **`retro`** → cuối mỗi phiên, đề xuất cải thiện *môi trường* (tooling, kiểm tra
  tự động, chuẩn code) — chính là việc bạn đang yêu cầu; kết quả là `OPERATIONS.md`.
- **`tdd`** → vòng đỏ-xanh-refactor cho module mới; ta đã có `unittest` + 690 test.
- **`handoff`** → nén ngữ cảnh thành tài liệu để agent khác tiếp tục: `CONTEXT.md`
  + `STATE.md` là bản địa hoá của skill này (giữ đúng vai trò đó).
- **`wizard`** → script dẫn người dùng qua bước chỉ-con-người-làm (tạo API key
  Binance, whitelist IP) thay cho văn xuôi README §16. Đề xuất: `tools/wizard_live.py`.

## 2. cocoindex-io/cocoindex-code — index AST (P1)

**Là gì**: CLI `ccc` nhúng, index code theo AST (tree-sitter) + MCP server, giúp
agent tìm đúng file/thẻ context thay vì grep mù.

**Áp dụng cụ thể**:

- Repo này **240 file, có file 2.800–2.900 dòng** (`turbo_demo.py`, `agents.py`) và
  vendor JS lớn → grep thường xuyên bị nhiễu (đã gặp: tìm "test" ra `d3.v7.min.js`).
  Index AST + `exclude_patterns` sẽ cắt nhiễu này.
- Việc làm ngay (không cần cài): **loại `vendor/`, `d3*.min.js`, `logs/`, `data/`
  khỏi mọi tìm kiếm** (thêm `.clineignore`/mô tả trong `AGENTS.md`).
- Việc làm khi rảnh: cài `ccc`, `ccc init` trong repo, dùng `ccc search` khi cần
  hiểu luồng (vd "chỗ nào set SYMBOLS").


## 3. rohitg00/ai-engineering-from-scratch — eval + an toàn + metrics (P1)

**Là gì**: giáo trình 20 giai đoạn, có sẵn code cho: **eval framework** (task spec,
metric cổ điển, code-exec metric, leaderboard), **RAG nâng cao** (hybrid BM25 +
dense, cross-encoder rerank, RAG eval), **safety harness** (jailbreak taxonomy,
prompt-injection detector, refusal eval, constitutional rules engine),
**monitoring** (Prometheus metrics), **agent harness**.

**Áp dụng cụ thể** (repo cho giá trị cao nhất với dự án):

- **Eval cho hội đồng AI**: ta đã ghi `[shadow]` mỗi quyết định (VETO/ALLOW). Thêm
  phép đo: VETO có đúng không (so với kết quả lệnh), precision/recall, bảng xếp
  hạng theo model → có bằng chứng mới dám cấp quyền chặn lệnh thật
  (`AGENT_VETO_SOURCE=COUNCIL`). Hiện `BLOCKED_VETO=0` vì thiếu phép đo này.
- **Safety gate cho tin tức**: bot đưa headline RSS vào prompt LLM → **rủi ro prompt
  injection thật** (tiêu đề tin có thể chứa chỉ thị). Áp: khử chỉ thị trong headline
  trước khi vào prompt + bộ luật "constitutional rules" cho agent.
- **Metrics**: xuất số liệu của `tools/ops.py` ra `logs/metrics.prom` (kiểu
  Prometheus textfile) để có **chuỗi thời gian** (tỉ lệ lỗi, số vòng, PF theo giờ).

## 4. donnemartin/system-design-primer — mẫu chịu tải (P1)

**Là gì**: primer kinh điển về cache, rate limiting, hàng đợi, availability, monitoring.

**Áp dụng cụ thể**:

- **Cache-aside + TTL** (đã làm hôm nay: `exchange.fetch_ohlcv` cache tăng dần,
  `_cached_ctx` cho OI/liq TTL 600s + jitter) → đúng pattern trong primer.
- **Circuit breaker**: endpoint lỗi liên tục thì "mở mạch" một lúc thay vì retry
  liên tục — ta có cooldown 120s cho fetch; nên áp tương tự cho
  `derivatives.fetch_oi_funding` / `fetch_liquidations` (hiện nuốt lỗi, trả 0).
- **Bulkhead**: tách pool theo nguồn (klines / OI / tin tức) để 1 nguồn chậm không
  nghẽn cả vòng quét. Hiện mọi thứ đi qua cùng 1 cụm 8 luồng.
- **Back-of-the-envelope**: ghi ngân sách weight Binance (2400/phút) + số
  request/vòng vào tài liệu — chính là phần "Đo trước khi sửa" ở `OPERATIONS.md` §3.

## 5. dzhng/jevgrep — tìm code bằng ngữ nghĩa (P2)

**Là gì**: CLI cho coding agent: hỏi "code nào làm việc này" → trả file/ngữ cảnh;
đo trên 10 task SWE-bench: cùng độ chính xác, **giảm ~30% chi phí agent**.

**Áp dụng**: dùng khi điều tra chéo nhiều file (vd "chỗ nào ghi journal", "ai set
MAX_POSITIONS"). **Lưu ý bảo mật**: nó gửi nội dung file lên provider → phải chắc
`.env`, `logs/`, key không nằm trong vùng tìm kiếm.

## 6. revfactory/harness — kiến trúc nhóm agent (P2)

**Là gì**: "nhà máy kiến trúc đội agent": 6 mẫu (Pipeline, Fan-out/Fan-in, Expert
Pool, Producer-Reviewer, Supervisor, Hierarchical) + sinh skill + **verification
(trigger eval, A/B có/không skill)** + vòng tiến hoá.

**Áp dụng**: ta đã dùng đúng 2 mẫu — **Supervisor** (`run_forever.py`) và
**Producer-Reviewer** (hội đồng critic/review). Nên: (a) vẽ rõ kiến trúc này vào
`README`; (b) biến "shadow" của hội đồng thành **A/B có/không hội đồng** chính thức;
(c) theo quy tắc của họ "dạng luồng điều khiển quyết định chế độ chạy" → hội đồng
của ta là fan-out một lần ⇒ **không** cần workflow phức tạp.

## 7. camel-ai/camel — framework multi-agent (P3)

**Là gì**: framework multi-agent lớn (role-playing society, memory, toolkits, RAG,
evaluation, MCP).

**Áp dụng (chỉ tham khảo)**: mượn ý tưởng **TaskCreationAgent / TaskPrioritizationAgent**
cho khâu triage; mượn **long-term memory + RAG** để nâng `learner.py` (logistic 20
feature) lên "truy hồi các setup tương tự trong journal". Không cài: quá nặng.

## 8. collabs-inc/collab-public — IDE canvas cho agent (P3)

**Là gì**: app Electron: canvas vô hạn chứa nhiều terminal + note + file, chạy nhiều
agent song song (PowerShell/WSL2 trên Windows).

**Áp dụng**: **phương án dự phòng cho đúng vấn đề shell chập chờn** — nếu terminal
VS Code tiếp tục lỗi, đây là nơi tách hẳn terminal của agent khỏi VS Code. Chưa cài
(ưu tiên tasks.json + `tools/ops.py`).

## 9. morluto/rea — reverse-engineering (P3)

**Là gì**: bộ công cụ + MCP server để reverse-engineer (app, binary) bằng agent.

**Áp dụng**: gần như không cho logic trading. Điểm đáng mượn: **cách đóng gói công cụ
qua MCP + "skill-only installation"** — nếu sau này muốn cho agent ngoài gọi trực
tiếp `tools/ops.py` / `tools/restart_bot.py` thì đó là mẫu. **Không** dùng để phân
tích binary của sàn (vi phạm điều khoản sử dụng).

---

## 10. `dealignai/DeepSeek-V4.1-Flash-UNCENSORED-FP8` — **KHÔNG áp dụng** (12/10)

**Dữ liệu đọc được từ trang model** (không tải trọng số):

| Mục | Giá trị | Ý nghĩa với dự án |
|---|---|---|
| Tổng tham số | **763,2 B** (I8 557B + FP8_E4M3 204B) | MoE cực lớn; **phải giữ toàn bộ trọng số trong VRAM** |
| Kích thước file | **~510 GB** (sharded) | Tải về đã tốn ~0,5 TB đĩa + băng thông |
| VRAM cần (ước) | **~916 GB** ở 8-bit (công cụ tính) | Máy hiện tại: 1 GPU nhỏ (~8 GB) ⇒ **bất khả thi** |
| Tag | `uncensored`, `abliterated`, **`crack`**, multimodal, fp8 | Đã **bỏ lớp từ chối** của model gốc |
| `model-index` | **null** (không có eval) | Không có bằng chứng chất lượng nào để so |
| License | khai `mit` trong khi base là DeepSeek | Nghi vấn **license laundering** |
| Gated | không | Bất kỳ ai cũng tải được (không kiểm soát nguồn) |
| Bản sao | hàng chục repo/Space clone cùng tên | Nguồn gốc trọng số **không kiểm chứng được** |

**Vì sao không dùng cho dự án này**:

1. **Không chạy được**: 763B tham số cần ~916 GB VRAM — dự án chạy trên 1 máy Windows
   với hội đồng cloud + 1 model local 3B.
2. **Ngược nguyên tắc an toàn của hội đồng**: hội đồng đọc **dữ liệu ngoài** (tin tức
   RSS, headline) rồi đưa vào prompt. Một model không có lớp từ chối + nguồn gốc
   không kiểm chứng = tăng rủi ro **prompt-injection** và không có gì bù lại.
3. **Không có bằng chứng chất lượng**: không eval, không A/B ⇒ đúng quy tắc dự án
   ("đo trước khi tin", `AGENTS.md`).
4. **Rủi ro chuỗi cung ứng**: ~510 GB trọng số không kiểm chứng + tag `crack`;
   nếu muốn thử thì phải safetensors-only, **không** `trust_remote_code`, chạy trong
   môi trường tách biệt, và kiểm hash.
5. **Không cần thiết**: cái dự án thật sự thiếu là **bằng chứng hội đồng đúng/sai**
   (precision/recall VETO) và **lọc prompt-injection** — không phải model "mạnh hơn".

### 10.1 Đã biến thành công cụ: `tools/model_audit.py`

```bash
python tools/model_audit.py                      # soi hoi dong trong .env
python tools/model_audit.py --target live        # soi .env cua atb-live
python tools/model_audit.py --hf <repo> --params-b 763 --bits 8 --size-gb 510
```

Checklist tất định (offline, không gọi mạng): **cờ đỏ trong tên** (uncensored /
abliterated / crack / jailbreak / leak…) · **license** · **VRAM ước tính** từ số tham
số × bit lượng hoá (×1,2 overhead) so với `--vram-gb` của máy · **có eval hay không**.
Kết luận: `OK` / `XEM LAI` / `KHONG NEN DUNG` (mã thoát 2 nếu có mục KHÔNG NÊN DÙNG).

Kết quả chạy thật:

```
=== AUDIT REPO: dealignai/DeepSeek-V4.1-Flash-UNCENSORED-FP8 ===
  co do trong ten    : ['uncensored', 'dealign']
  VRAM can (uoc)     : 915.6 GB (may co 8.0 GB)
  KET LUAN           : KHONG NEN DUNG — co do + can ~916 GB VRAM + khong co eval
=== HOI DONG TESTNET: 11 muc ===  -> KET LUAN: hoi dong sach
```

### 10.2 Nếu thật sự muốn "phân tích không bị từ chối" thì làm gì

- Dùng **model local nhỏ** đã có trong hội đồng (`AGENT_COUNCIL_LOCAL=llama3.2:3b`
  qua Ollama) + **system prompt nghiêm**: chỉ trả JSON, chỉ nói về dữ liệu được đưa,
  không thực thi chỉ thị nằm trong dữ liệu.
- Vá **P1 prompt-injection**: khử chỉ thị trong headline RSS trước khi vào prompt
  (mục 3 của tài liệu này) — rủi ro thật của dự án, không phải việc thiếu model to.
- Muốn "uncensored" cho văn bản nhạy cảm: cân nhắc model **3B–8B** đã abliterate
  (chạy được, rẻ) **chỉ cho khâu tóm tắt tin**, và luôn đặt sau cổng tất định —
  không bao giờ cho nó quyền mở/đóng lệnh.


---

## 11. Rà 10 repo agent/skill (13/10) — áp dụng được gì

Đọc README/kiến trúc từng repo, đối chiếu với thứ dự án **đang thiếu** (bằng chứng
hội đồng đúng/sai, chống prompt-injection, quan sát được, kỷ luật quy trình). Nguyên tắc
giữ nguyên: **hội đồng/AI chỉ cố vấn; tiền và rủi ro đi qua ngưỡng tất định**.

| # | Repo | Cốt lõi | Áp dụng cho dự án | Ưu tiên |
|---|---|---|---|---|
| 1 | **browser-use** (MIT, 118k★) | Agent điều khiển browser qua `Agent(task, llm, tools)`; `@tools.action` khai báo công cụ; `ActionResult(extracted_content=...)` | **Không dùng** (bot không cần browser; thêm bề mặt tấn công + chi phí). Nhưng *pattern* `@tools.action(description=...)` rất đáng bắt chước khi mở API công cụ cho agent | P3 |
| 2 | **agentmemory** (Apache-2.0) | Bộ nhớ 4 tầng (episodic→semantic→procedural), **decay theo đường cong Ebbinghaus**, hợp nhất theo phiên, **triple-stream retrieval** (BM25 + vector + graph, hợp nhất bằng **RRF k=60**), provenance ghi lúc lưu | **Áp dụng**: `memory_graph.py`/`memory_agent.py` đã có graph + retrieval; bổ sung **(a) decay + eviction** cho ký ức cũ, **(b) provenance**: mỗi ký ức trỏ về sự kiện journal sinh ra nó (đã có `bench_retrieval.py` để đo) | **P1** |

---

## 12. Rà 3 repo lớn (14/10) — AI engineering, self-hosted, agent harness

Đọc README + cấu trúc thư mục của từng repo, đối chiếu với thứ dự án **đang thiếu**.
Nguyên tắc bất biến: **AI/hội đồng chỉ cố vấn; tiền và rủi ro đi qua ngưỡng tất định**.

### 12.1 `rohitg00/ai-engineering-from-scratch` (MIT, 69k★, 20 phase / 87 bài)

| Phần | Cốt lõi | Áp dụng cho dự án | Ưu tiên |
|---|---|---|---|
| **G. Eval framework** (bài 70–75) | Task Spec Format, classical metrics, code-exec metric, **perplexity & calibration**, leaderboard, end-to-end eval runner | **ĐÃ LÀM (14/10)**: `council_evals.model_leaderboard()` + `tools/council_eval.py` — xếp hạng TỪNG model theo kết quả thật (`value_r = avgR(ALLOW) − avgR(VETO)`, `veto_precision`, **Brier calibration**). Bằng chứng đầu: `claude-sonnet-5.5` veto_precision **0.292** (71% lệnh nó chặn là lệnh thắng) — khớp với gap A/B −0.077 đã đo | **XONG** |
| **I. Safety harness** (82–87) | Prompt-injection detector, refusal eval, content classifier, **Constitutional Rules Engine (Python + YAML)**, end-to-end safety gate | **ĐÃ LÀM (14/10)**: `prompt_guard.py` + gắn vào `build_prompt()` — cổng tất định khử chỉ thị trong dữ liệu ngoài lai (mẫu `ignore previous`, `system:`, `<|...|>`, URL, ký tự điều khiển) + cắt độ dài; trả `findings` để ghi log. Còn lại (P2): bộ luật YAML cho các ngưỡng hội đồng | **P1 (phần chính xong)** |
| **F. Advanced RAG** (64–69) | Chunking, hybrid BM25 + dense, cross-encoder rerank, HyDE/multi-query, **RAG eval: precision/recall/MRR/nDCG/faithfulness** | `lessons.py` + `memory_graph.py` đang truy xuất thô: thêm **MRR/nDCG** để biết lesson nào thực sự hữu ích (hiện chỉ đếm số lần chặn) | P2 |
| **D. Auto research** (50–57) | Hypothesis generator → experiment runner → **result evaluator** → **critic loop** → iteration scheduler | `learner.py` đã gần mô hình này; bổ sung **iteration scheduler** (1 thí nghiệm/tuần, có bảng kết quả) + critic loop cho đề xuất tự động | P2 |
| B/C/E/H (transformer, DPO, VLM, distributed) | Train model từ đầu | **Không áp dụng** — dự án không train model | — |

### 12.2 `awesome-selfhosted/awesome-selfhosted` (326k★) — công cụ tự host

| Nhu cầu | Công cụ (nhóm trong danh sách) | Trạng thái dự án | Ưu tiên |
|---|---|---|---|
| **Dead-man switch** (bot chết hẳn) | **Healthchecks**, Uptime Kuma | Đã có watchdog nội bộ + heartbeat, **chưa có cảnh báo khi tiến trình chết hẳn** | **P1** |
| **Backup** | Restic / Borg | `logs/journal.jsonl` + `.env` (khoá thật) **chưa có backup tự động** | **P1** |
| Metrics | Prometheus + `node_exporter` | Đã có `tools/ops.py --prom` → `logs/metrics.prom` (thiếu nơi scrape) | P2 |
| Dashboard | Grafana | — | P2 |
| Log tập trung | Loki + Promtail / Grafana Alloy | Log đang là file rời trong `logs/` | P2 |
| Alerting | Alertmanager → Telegram | Đã có Telegram trực tiếp từ bot | P2 |
| Scheduler | Cronicle / systemd timer / Task Scheduler | Cần cho việc #24 (tự chạy llamafile khi boot) | P2 |
| Secrets | Infisical / Vault | `.env` đang **plaintext** (khoá API live) | P2 |
| Local LLM | llama.cpp / llamafile, Open WebUI | Đang dùng llamafile; Open WebUI chỉ để **xem log hội đồng** | P3 |

### 12.3 `affaan-m/ECC` (MIT, 279k★) — agent harness performance

Cốt lõi: `skills/` + **instincts** (`/instinct-status`, `/instinct-import|export`, `/evolve` gom
instinct thành skill, `/prune` xoá instinct hết hạn), `hooks/` (PreToolUse/PostToolUse/Stop),
`rules/` (coding-style, testing TDD 80% coverage, performance, security), `commands/`
(plan, code-review, **quality-gate**, **learn / learn-eval**, checkpoint, test-coverage),
memory-persistence hooks, strategic-compact.

| Ý tưởng | Áp dụng cho dự án | Ưu tiên |
|---|---|---|
| **`/evolve`** — gom instinct thành skill | `lessons.py` chính là "instinct": thêm `tools/evolve_lessons.py` gom lesson cùng chủ đề thành **skill có tên** + đề xuất đổi ngưỡng (vẫn qua cổng tất định `AGENT_AUTO_APPLY`) | **P1** |
| **`/prune`** — xoá instinct hết hạn | Lesson cũ không tái hiện (>60 ngày) ⇒ archive, tránh `SKIP_LESSON` chặn oan (đang bắn 11–13 lần/vòng) | **P1** |
| **`/quality-gate`** — cổng xác minh trước khi merge | `tools/git-sync.cmd` gọi trước: `unittest discover` + `harness_audit.py --both`; điểm tụt ⇒ chặn push | P2 |
| **`/checkpoint`** — lưu trạng thái xác minh | Ghi (số test, điểm harness, số vị thế) vào `STATE.md` để so sánh giữa các phiên | P2 |
| **strategic-compact** — nén ngữ cảnh theo ngân sách | Hội đồng đã có `agent_max_prompt_tokens`; thêm cắt theo tier khi prompt phình | P3 |
| **hooks Pre/PostToolUse** | Đặt lệnh đã có guard tất định; **không cần thêm** (thêm hook = thêm bề mặt lỗi) | — |

**Việc nên làm ngay từ §12**: (a) `tools/council_eval.py` (eval model hội đồng, P1),
(b) chống prompt-injection từ headline RSS (P1), (c) Healthchecks dead-man switch (P1),
(d) backup journal + `.env` bằng Restic (P1), (e) `/evolve` + `/prune` cho `lessons.py` (P1).

| 3 | **scientific-agent-skills** (MIT) | 177 skill theo **chuẩn Agent Skills**: `skills/<ten>/SKILL.md` + frontmatter (`name`, `description`, `when_to_use`), thư mục `references/`, `scripts/` | **Áp dụng**: viết `SKILLS.md` của dự án (fix-bug-loop, retro, handoff, wizard, audit-lệnh-chờ) **theo đúng frontmatter chuẩn** để mọi agent đọc được | **P1** |
| 4 | **diagram-design** (MIT) | 44 kiểu sơ đồ, HTML+SVG tự chứa, "1 accent, không đổ bóng, mọi toạ độ chia hết cho 4"; có **fidelity receipt**; nói rõ *khi nào KHÔNG nên vẽ* | **Áp dụng nhẹ**: 1 sơ đồ luồng `turbo_demo → bot → exchange → sàn` cho README. Quy tắc "Git hay đổi thì dùng Mermaid" ⇒ README dùng Mermaid, sơ đồ đẹp để riêng | P3 |
| 5 | **anthropic-cybersecurity-skills** (Apache-2.0) | 818 skill, **map vào 6 framework** (MITRE ATT&CK, NIST CSF 2.0, ATLAS, D3FEND, AI RMF, F3) | **Áp dụng**: `SECURITY.md` của dự án nên **map biện pháp vào khung** (vd NIST CSF: Identify=whitelist IP/không quyền rút tiền; Protect=key tách 2 instance; Detect=`ops.py`/kill-switch; Respond=flatten; Recover=ADOPT). Giúp không bỏ sót lớp | P2 |
| 6 | **OpenViking** (AGPL-3.0 ⚠️) | "Context database": memory + RAG + skill hợp nhất; **thư mục là ngữ cảnh truy hồi** (TrieHI, truy vấn theo nhánh), VikingRAG chỉ mở rộng truy hồi khi **thiếu bằng chứng** | **Chỉ lấy ý tưởng** (AGPL ⇒ KHÔNG nhúng code): (a) truy hồi theo *nhánh thư mục* cho `CONTEXT.md`/`STATE.md`; (b) **truy hồi tăng dần khi thiếu bằng chứng** = đúng cách `bench_retrieval.py` nên đo | P2 |
| 7 | **awesome-harness-engineering** | Tuyển tập về **harness**: eval skill, guardrail, observability, **tool annotations as risk vocabulary** (`readOnlyHint/destructiveHint/idempotentHint/openWorldHint`), **"lethal trifecta"** = dữ liệu riêng + nội dung không tin cậy + kênh ra ngoài | **Áp dụng trực tiếp**: (a) dán nhãn công cụ của bot theo 4 hint trên (vd `orders_audit.py`=readOnly, `--dedupe`=destructive, `stop_tp_orders`=idempotent); (b) **lethal trifecta đúng với dự án**: hội đồng đọc tin RSS (nội dung không tin cậy) + thấy ví thật (dữ liệu riêng) + có thể gửi Telegram (kênh ra ngoài) ⇒ **giữ veto ở shadow**, lọc injection trước khi vào prompt | **P1** |
| 8 | **GitNexus** (zero-server) | Chỉ mục code: tree-sitter AST + graph DB + BM25/FTS; nhiều biến `GITNEXUS_*` để chỉnh độ sâu truy vết luồng | **Chưa dùng** (nặng, cần Node + DB; repo này nhỏ ~40 file Python). Giữ ý tưởng: **truy vết luồng** khi sửa file lõi (`exchange.py` → `bot.py` → `turbo_demo.py`) — đã có `ccc` trong P3 | P3 |
| 9 | **mattpocock/skills** (MIT, 288k★) | Bộ skill kỷ luật: `diagnosing-bugs` (**dựng vòng phản hồi đỏ trước → tối giản → giả thuyết → đo → sửa → test hồi quy**), `retro`, `handoff`, `code-review` (2 trục: chuẩn + đặc tả), `pr` (**one-way vs two-way door + blast radius**), `writing-for-agents` | **Áp dụng ngay**: (a) `diagnosing-bugs` = **đúng cách tôi tìm ra lỗi 200 lệnh hôm nay** (đo `openAlgoOrders` → thấy 200 → suy ra vòng re-arm) — đưa vào `SKILLS.md`; (b) `pr`: mọi thay đổi tiền/rủi ro phải ghi **một chiều hay hai chiều + bán kính ảnh hưởng**; (c) `writing-for-agents` cho `AGENTS.md` | **P1** |
| 10 | **Understand-Anything** (MIT) | **Tách tất định vs ngữ nghĩa**: tree-sitter trích cấu trúc (cùng input → cùng output) + LLM chỉ để *dán nhãn* (tóm tắt, tầng kiến trúc, tour); pipeline 5 agent có **`graph-reviewer` kiểm tra tính toàn vẹn tham chiếu**; cập nhật tăng dần theo fingerprint | **Áp dụng**: (a) giữ đúng nguyên tắc "cấu trúc tất định, LLM chỉ dán nhãn" — chính là thiết kế hiện tại, nên **viết ra thành quy tắc**; (b) thêm **bước kiểm tra toàn vẹn** kiểu `graph-reviewer` vào `state_sync.py`/`memory_graph.py` (mọi ký ức phải trỏ tới sự kiện journal tồn tại) | P2 |

**Kết luận rà soát**: 3 việc P1 đáng làm ngay, đều **nhỏ và không đụng vào logic tiền**:
`SKILLS.md` (chuẩn Agent Skills) · nhãn rủi ro cho công cụ + **lọc prompt-injection cho headline**
(lethal trifecta) · decay/provenance cho bộ nhớ. Phần còn lại là P2/P3, ghi lại để không quên.

**Không áp dụng**: browser-use (không cần browser), GitNexus (nặng so với quy mô repo),
OpenViking (AGPL ⇒ chỉ lấy ý tưởng, không nhúng).

---

## 13. Rà 5 repo harness/memory (13/10, đợt 2)

| # | Repo | Cốt lõi | Áp dụng cho dự án | Ưu tiên |
|---|---|---|---|---|
| 1 | **ruvnet/ruflo** (MIT, TS, 74k★) | "Agent harness": **27 hooks**, swarm (Raft/Byzantine/Gossip), HNSW vector memory, SONA self-learning, **`ruflo verify`** (chứng minh bằng mật mã rằng byte đã cài khớp witness đã ký), AIDefence, **MetaHarness** = "chấm điểm setup agent, quét cấu hình tool để tìm lỗ hổng, phát hiện thay đổi giữa các lần chạy" | **Áp dụng (P1)**: ý tưởng **MetaHarness** → viết `tools/harness_audit.py`: 1 lệnh **chấm điểm setup** theo tiêu chí tất định (số test, kill-switch, **độ phủ bảo vệ = 2 × số vị thế**, whitelist ↔ `.env`, journal OPEN/CLOSE cân, veto còn shadow, `.clineignore`). **Không** mang cả framework TS vào (nặng, thừa cho 1 bot Python) | **P1** |
| 2 | **mozilla-ai/llamafile** (Apache-2.0, 26k★) | 1 file thực thi = llama.cpp + Cosmopolitan, chạy **không cần cài**; phục vụ **API tương thích OpenAI**; **Windows: chỉ file < 4 GB**; kèm `whisperfile` | **Áp dụng (P1)**: thay phụ thuộc **Ollama** cho model local của hội đồng (`llama3.2:3b`) bằng 1 `.llamafile` + trọng số GGUF — cùng endpoint `/v1` nên **không phải đổi code**, nhưng bỏ được daemon/dịch vụ nền (đang là điểm chết khi máy khởi động lại). Chọn bản quantized để file < 4 GB | **P1** |
| 3 | **vxcontrol/pentagi** (MIT, Go+React+Docker, 27k★) | Agent tự trị chạy tác vụ dài: nhiều agent chuyên trách, **flow/chain** có trao artifact, sandbox Docker, **stack quan sát** (compose riêng cho Langfuse/Prometheus/Grafana), API GraphQL | **Áp dụng một phần (P2)**: (a) **quan sát** — xác nhận việc `logs/metrics.prom` (đếm OPEN/CLOSE/lỗi/kill-switch) là hướng đúng, nên làm; (b) **flow có artifact** = mô hình hội đồng 2 vòng hiện tại (đã có). **Không** nhúng: cần Docker + Go + React, quá nặng | P2 |
| 4 | **tigerless-labs/autoharness** (MIT, Python, 11k★) | Lớp **skill tự học**: rút skill từ phiên thật, **hợp nhất skill cùng tình huống thay vì xếp chồng bản gần giống**, cập nhật khi dùng, **tỉa skill hết dùng** (lưu trữ, không xoá), đếm **use / view / patch** riêng (adherence ≠ lượt xem), **không bao giờ đụng vào skill do người viết** (có dấu ledger), giới hạn số lượng + trục xuất, **không daemon, không benchmark** | **Áp dụng (P1)** — đúng 4 điều dự án đang thiếu: (a) **hợp nhất thay vì xếp chồng** cho `learner.json` (đang **251 cập nhật**, chưa có kiểm tra trùng) và cho bộ nhớ; (b) **đếm use vs view** cho hội đồng (ta đã ghi `event=AGENT` — cần tách "được dùng" và "chỉ đọc"); (c) **trần + trục xuất vào kho lưu trữ** cho ký ức; (d) **không tự sửa mục do người viết** (áp cho `CONTEXT.md`/`STATE.md`) | **P1** |
| 5 | **Egonex-AI/Understand-Anything** (MIT, 86k★) | tree-sitter **tất định** + LLM **chỉ dán nhãn**; pipeline 5 agent có **`graph-reviewer` kiểm tra toàn vẹn tham chiếu**; cập nhật tăng dần theo fingerprint | **Đã ghi ở §11 mục 10** — giữ nguyên: (a) viết thành quy tắc "cấu trúc tất định, LLM chỉ dán nhãn"; (b) thêm bước **kiểm tra toàn vẹn** kiểu `graph-reviewer` (mọi ký ức phải trỏ tới sự kiện journal tồn tại) | P2 |

**Không áp dụng**: ruflo (framework TS + swarm — thừa cho 1 bot Python 40 file),
pentagi (Docker/Go/React). **Chỉ lấy ý tưởng**: cả hai.

**Việc rút ra cho lần tới (đã xếp vào danh sách tổng hợp):** `tools/harness_audit.py`
(ruflo/MetaHarness) · llamafile thay Ollama · kỷ luật hợp nhất/tỉa của autoharness cho
`learner` + bộ nhớ · `metrics.prom` (pentagi).


1. **P1** `SKILLS.md` theo chuẩn Agent Skills (fix-bug-loop, retro, handoff, wizard, audit-lệnh-chờ).
2. **P1** `.clineignore` loại `vendor/`, `d3*.min.js`, `logs/`, `data/` — **đã làm 12/10**.
3. **P1** Eval hội đồng (precision/recall VETO) + lọc prompt-injection cho headline.
4. **P1** Circuit breaker cho `derivatives.py`; bulkhead tách pool theo nguồn.
5. **P2** `logs/metrics.prom` (Prometheus textfile) từ `tools/ops.py`.
6. **P2** A/B "có/không hội đồng" chính thức trước khi cấp quyền veto.
7. **P3** Cân nhắc `ccc` (index AST) và Collaborator nếu shell vẫn tệ.
8. **P1** `python tools/model_audit.py` trước khi thêm/bớt model hội đồng — **đã có 12/10**.
9. **P0** Lệnh điều kiện ở Algo Order API: đọc/huỷ qua `exchange.algo_orders()` + kiểm kê bằng `tools/orders_audit.py` — **đã vá 13/10** (200 → 4 lệnh LIVE).
10. **P1** Nhãn rủi ro cho công cụ (`readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint`) — §11 mục 7.
11. **P1** Bộ nhớ: thêm decay/eviction + provenance (mỗi ký ức trỏ về sự kiện journal) — §11 mục 2.
12. **P2** `SECURITY.md` map biện pháp vào khung NIST CSF — §11 mục 5.
13. **P2** `graph-reviewer` cho `state_sync.py`/`memory_graph.py` (toàn vẹn tham chiếu) — §11 mục 10.
14. **P2** LIVE: chặn sớm khi notional < minNotional $5 (hiện `CFX` trả `-4164` mỗi vòng, tốn log/vòng quét).
15. **P2** Gọi `position_sync.adopt()` **định kỳ trong vòng lặp** (vd mỗi 10 vòng): hiện chỉ chạy lúc khởi động nên entry "ma" (symbol đã đóng trên sàn nhưng còn trong `managed`/`portfolio`) sống tới lần restart sau; quan sát 13/10: LIVE còn `BNB` trong `managed=4` trong khi sàn chỉ có 3 vị thế. Không nguy hiểm (đã có `fetch_protection` nên KHÔNG re-arm trùng), nhưng nên dọn định kỳ.
16. **P2** Quét mồ côi định kỳ: `python tools/orders_audit.py --target live --cancel-orphans` (mỗi lần đóng vị thế có thể để lại 1 chân TP nếu SL trên sàn khớp trước khi bot kịp `_close`).
17. ~~**P1** `tools/harness_audit.py`~~ — **đã làm 13/10** (chấm điểm setup, 16 test).
18. ~~**P1** Thay Ollama bằng llamafile~~ — **đã làm 13/10**: `tools/llamafile_setup.py` (check/download/start/probe/env); cần chạy `--download` để có file thật.
19. ~~**P1** Kỷ luật autoharness cho learner + bộ nhớ~~ — **đã làm 13/10**: `lessons.py` (hợp nhất theo tổ hợp, đếm `hits` = use ≠ view, trần + trục xuất vào `logs/lessons_archive.jsonl`, không sửa phần `<!-- HUMAN -->`).
20. ~~**P1** `logs/metrics.prom`~~ — **đã làm 13/10**: `python tools/ops.py --prom` (4 test).
21. ~~**P1** Bật veto thật cho hội đồng~~ — **13/10: đo dứt điểm ⇒ KHÔNG nên bật** (SETUP gap +0.012 = vô dụng; COUNCIL gap −0.077 = ngược dấu). Thay vào đó đã **sửa sức khoẻ hội đồng**: bỏ model treo, bỏ review khi provider chết, nâng hạn mức gọi. Việc còn lại: theo dõi `--council-health` cho tới khi có VETO/ALLOW thật rồi đo lại.
22. ~~**P2** Nâng/hạ `LESSONS_MAX_AVG_R`~~ — **đã quyết bằng `--sweep`**: −0.05 (tiết kiệm 82.33/62.46, bỏ lỡ 0) cho cả 2 instance.
23. ~~**P2** Bỏ hẳn Ollama~~ — **đã làm 13/10**: llamafile thin + GGUF 3B Q4 đang chạy ở `127.0.0.1:8080`, cả 2 instance dùng nó; đổi qua lại bằng `tools/switch_local_model.py`.
24. **P1** Chạy llamafile **tự động khi khởi động** (hiện phải `--start` tay): thêm vào `run_forever.py` (nếu endpoint chết thì start) hoặc Task Scheduler — để sau reboot hội đồng vẫn có phiếu local.
25. ~~**P1 (mới, 13/10)** Map lại alias hội đồng → id gateway ClinePass~~ — **ĐÃ LÀM**: `model_aliases.py` (map 15 alias → id thật) + `ClineProvider` gửi id gateway + `max_tokens=300`; kiểm chứng qua code bot thấy phiếu thật; `kimi-k3`/`glm-5.3` (gateway 500) đã vào `CLINE_SKIP_MODELS`.
26. **P2** Hội đồng chạy **rất chậm** (14 model × 2 vòng > 10 phút khi test tay): cân nhắc giảm còn 5–6 model hoặc hạ `COUNCIL_ROUNDS=1` cho các vòng bình thường.


---

## 14. (16/10) Đọc 2 repo người vận hành gửi — áp dụng được gì

### 14.1 `HKUDS/CLI-Anything` (Apache-2.0, 53.2k★) — "Making ALL Software Agent-Native"

**Cốt lõi:** mỗi ứng dụng được đóng gói thành **một CLI đầy đủ chức năng** + thư mục
`agent-harness/` **có test riêng** (GIMP 107 test, Blender 208, Inkscape 202…), kèm
`cli-hub-matrix` (ma trận năng lực), `cli-hub-meta-skill` (skill dạy agent *cách* chọn
đúng CLI), và nhiều "cửa" cài đặt cho từng agent (`claude-plugin`, `cursor-plugin`,
`codex-skill`, `.claude-plugin`, `.cursor-plugin`). Triết lý: **không có "đường tắt" riêng

---

## 16. (19/10) Đọc 7 repo người vận hành gửi — áp dụng được gì

**Bối cảnh**: người vận hành gửi 7 repo (**AutoGPT, LangChain, Dify, MetaGPT, AutoGen, CrewAI,
LangGraph**). Hội đồng đọc + bỏ phiếu: **1 ALLOW / 4 VETO** việc làm `council_replay` ngay
(4 model VETO vì **tốn credit mỗi lần chạy**) ⇒ chọn việc **rẻ hơn** là artifact mỗi quyết định
vận hành (đã làm: `tools/ops_artifact.py` + hook trong `ops_queue.answer`). Nguyên tắc: **mượn
CƠ CHẾ, không mượn HẠ TẦNG** — dự án chạy 1 máy, 2 instance, ưu tiên `file + CLI`.

### 16.1 Bảng cơ chế → dự án (đã có gì / còn thiếu gì)

| Repo | Cơ chế đáng học | Ở dự án này | Việc cần làm |
|---|---|---|---|
| **LangGraph** | graph state + **durable execution** (checkpoint → resume) | `journal` + `managed_state.json` + `reconcile` + `entries_gate` (pause có hạn) = bản thủ công, đủ dùng | P3 (chỉ làm nếu cần "chạy lại từ checkpoint" 1 vòng quét) |
| | **interrupt / human-in-the-loop** (dừng chờ người) | `tools/ops_queue.py` (`ops_questions.json` + `ops_queue.json`, resume qua phiên) + `entries_gate` | **P2**: đẩy câu hỏi ra Telegram để không phải mở máy |
| | **time travel / replay** | chưa có | P2 nhưng **hội đồng VETO làm ngay** (tốn credit) — xem `council_replay` ở §16.3 |
| **LangChain** | runnable + **structured output** + retry/fallback | `agents.parse_decision` + `missing_models` + `shadow` | đã đủ |
| | **lọc "slop"** ở đầu ra LLM | chưa tất định hoá | **P2**: lý do không có số/mã bằng chứng ⇒ gắn nhãn `slop` để `council_eval` đo |
| | callbacks/tracing | mọi quyết định ghi `journal` + `tools/trace_trade.py` | đã đủ |
| **AutoGen** ⚠️**ARCHIVED** | **termination conditions** (max turns / budget) | `AGENT_DAILY_CALLS(_HARD)` + `BUDGET` + trần 2 vòng debate | đã đủ — **không dùng repo** (Microsoft archive, chuyển sang Agent Framework) |
| | group chat manager chọn người nói | hội đồng bỏ phiếu song song + `arbiter` + tie-break 1-3 | đã đủ |
| **CrewAI** | task có **expected_output** + **guardrails** | guard **tất định** (kill-switch, `can_add_risk`, `entries_gate`) — mạnh hơn guardrail mềm của LLM | đã đủ |
| | hierarchical process (manager giao việc) | `arbiter` + escalate/debate | đã đủ |
| | memory (short/long/entity) | `lessons.py` + `LESSONS.md` (có provenance `EV-xxxxxx`) | đã đủ |
| **MetaGPT** | **artifact chuẩn hoá mỗi bước** | **ĐÃ LÀM 19/10**: `tools/ops_artifact.py` → `logs/ops/<ts>-<slug>.md` (bối cảnh → phiếu hội đồng → quyết định → hành động → kết quả) | ✅ xong |
| | **executable feedback** (chạy test, nuôi lỗi ngược lại) | `bug_catalog` (22 lớp lỗi ↔ 41 test chốt) + `lessons` từ journal | **P2**: sinh lesson từ **LỖI vận hành** (`-2022`, `ORDER_FAILED`, `SKIP_MAX_POS`…) chứ không chỉ từ lệnh đóng |
| | token/cost accounting | journal có `cost_usd`, `tokens_in/out`; `AGENT_DAILY_BUDGET_USD` | P3: báo cáo chi phí/ngày |
| **AutoGPT** | **"actions that need attention"** | `tools/ops_queue.py` + `tools/ops.py` (`--check` quá 24h) | đã đủ |
| | **benchmark harness** (agbenchmark) | `tools/harness_audit.py` (chấm điểm setup) + suite 1024 test | P2: benchmark **hồi quy cho hội đồng** = chính `council_replay` (đang bị VETO vì chi phí) |
| | run history + cost dashboard | `STATE.md`, `logs/state_snapshot.json`, journal | P3 |
| **Dify** | workflow node + **human approval node** | `entries_gate` (cổng có hạn) + `ops_queue` (câu hỏi chờ người) | đã đủ |
| | observability/LLMOps + **annotation/dataset** | `tools/council_evals.py` (đối chiếu phiếu cũ với kết quả thật) | **P2**: dataset nhỏ để chấm điểm hội đồng theo thời gian |
| | API-first (backend-as-a-service) | mỗi năng lực = 1 lệnh CLI + `tools/capabilities.py --json` (28 tool) | P3: MCP server (§15.2) |

### 16.2 Đã làm ngay trong phiên 19/10 (đúng phán quyết hội đồng 1-4)

- **`tools/ops_artifact.py`** — mỗi quyết định vận hành sinh 1 file `logs/ops/<ts>-<slug>.md`:
  bối cảnh → **bảng phiếu hội đồng** (tự lấy từ `journal` theo đúng câu hỏi) → quyết định →
  hành động đã làm → kết quả kiểm chứng → mục truy vết. **18 test** (`tests/test_ops_artifact.py`),
  `--from-queue <id>`, `--list`, `--council-question` (khi câu hỏi hỏi hội đồng khác chữ với
  câu hỏi trong hàng đợi). **Hook**: `ops_queue.answer` tự sinh artifact sau khi trả lời.
  Đã backfill 5 quyết định thật của ngày 19/10 (parity TESTNET 3-1; bỏ root trùng 5-0;
  7 repo 1-4; LIVE 24h; credit) — chi phí LLM = **0**.
- **`tools/terminal_hygiene.py`** — dọn shell rác của VS Code (Cline tạo 1 terminal mỗi lần chạy
  lệnh, đo được **112 shell = 1138 MB**): 3 lớp an toàn (chỉ shell của `Code.exe`, chỉ shell
  **rảnh**, bỏ qua cây tiến trình đang chạy), `--watch` để chạy nền. **Tự động gọi ở cuối
  `council_vote.py`** ⇒ *mỗi lần hỏi hội đồng là terminal rác được dọn*. 18 test.

### 16.3 Điều KHÔNG nên copy (ghi lại để khỏi bàn lại)

1. **AutoGen đã ARCHIVED** (Microsoft chuyển sang Microsoft Agent Framework) ⇒ không đưa vào kiến trúc.
2. **Dify / AutoGPT platform** kéo theo server + Postgres + Redis + worker ⇒ không phù hợp máy 1 người.
   Chỉ mượn khái niệm (human approval node, run history, annotation).
3. **`council_replay`** (LangGraph time-travel + agbenchmark + CrewAI replay): **hội đồng VETO
   làm ngay** (4/5 phiếu) vì mỗi lần chạy tốn credit mà chưa có ngân sách riêng. Điều kiện mở lại:
   có `AGENT_DAILY_BUDGET_USD` dư **hoặc** chạy với `--models` chỉ 2-3 model rẻ (local llama + 1-2 model gateway).
4. **Vector DB / RAG cho "memory"**: dự án đã có `lessons` + `graph_memory` + journal; thêm embedding
   store là tăng hạ tầng mà chưa có bằng chứng cần (§10 đã kết luận tương tự).

cho agent** — agent dùng đúng bề mặt CLI của sản phẩm, nên hành vi kiểm chứng được.

| Ý tưởng | Áp dụng cho dự án | Ưu tiên |
|---|---|---|
| **Mỗi năng lực = 1 lệnh tự mô tả + harness test riêng** | **ĐÃ LÀM 16/10**: `tools/capabilities.py` quét `tools/*.py` → bảng `tool → mục đích → ví dụ → số test tham chiếu`, có `--json` cho agent và `--check` cho CI (tool thiếu docstring ⇒ fail). Đo được: 23 tool, nhiều tool còn 0 test tham chiếu | P1 (đã làm) |
| **"Meta-skill" dạy agent chọn đúng công cụ** | Hội đồng hiện chỉ *cố vấn*, không tự gọi được công cụ. Bước 2: đưa manifest (`capabilities.py --json`) vào **prompt của agent review/council** để nó đề xuất *lệnh cụ thể* (`python tools/…`) thay vì lời khuyên chung | P2 |
| **Ma trận năng lực + đếm test như chỉ số chất lượng** | Thêm vào `harness_audit.py` một dòng "tool nào chưa có test" (đã có dữ liệu từ `capabilities.check`) → buộc bổ sung test theo thời gian | P2 |
| **Nhiều "cửa" cài đặt cho nhiều agent** | Dự án đã có `AGENTS.md`/`CONTEXT.md` cho agent; có thể thêm `skills/` cho Cline/Copilot CLI đọc (cùng nội dung, khác định dạng) | P3 |

### 14.2 `miqdadbadjuber/anti-slop` (MIT, 6.2k★) — bộ luật lọc "slop" của AI

**Cốt lõi:** là **bộ lọc, không phải style guide**: `rules/` đánh số, `skills/*/SKILL.md`
**tham chiếu luật theo số** (không chép lại ⇒ thêm skill không đổi lõi), CLI + cài bằng
`npx antislop-ai`, cấu hình dùng chung `%APPDATA%\antislop\settings.json`, có **catalogue
mọi mẫu lỗi sinh tự động từ chính các skill và được kiểm trong CI**. Câu chốt của repo:
*"antislop is a filter, not magic."*

| Ý tưởng | Áp dụng cho dự án | Ưu tiên |
|---|---|---|
| **Luật đánh số + skill tham chiếu, không chép lại** | `CONTEXT.md` đã là "bảng lớp lỗi" đánh số theo ngày; nên **đặt mã cho từng lớp lỗi** (vd `E-COUNCIL-SILENT`) để test/commit trỏ tới mã đó thay vì mô tả dài | P2 |
| **Catalogue sinh tự động + kiểm trong CI** | Viết `tools/bug_catalog.py`: đọc `CONTEXT.md` → sinh `BUGS.md` (mã, ngày, triệu chứng, cách sửa, test nào chốt) + `--check` bắt mỗi lớp lỗi phải có **ít nhất 1 test** nhắc mã đó | P1 (đề xuất) |
| **Lọc "slop" ở đầu ra của LLM** | Phiếu hội đồng có thể "rỗng thông tin" (lý do chung chung, không số liệu). Thêm **bộ lọc tất định** ở `parse_decision`: lý do không có số/mã cặp ⇒ `note+="slop"`, ghi journal để `council_eval` đo **tỷ lệ slop theo model** (đúng tinh thần "filter, not style guide") | P1 (đề xuất) |
| **Cấm "slop" trong tài liệu công cụ** | **ĐÃ LÀM 16/10**: `capabilities.py --check` buộc mọi tool có docstring (không có tool "vô danh"); cùng tinh thần với `prompt_guard.py` (lọc chỉ thị lạ trong payload) | P2 (đã làm) |

**Ghi chú:** cả hai repo đều không phải công cụ giao dịch — giá trị áp dụng nằm ở **kỷ luật
đóng gói năng lực + lọc đầu ra**, đúng chỗ dự án đang yếu: hội đồng nói được nhưng *không
tự gọi được công cụ*, và phiếu có thể rỗng thông tin mà không ai đo.

## 15. (18/10) Đọc 2 repo + blueprint "agentic SDLC" của người vận hành

### 15.1 `Mintplex-Labs/anything-llm` (MIT, 67.3k★) — knowledge layer local-first

**Cốt lõi:** "Stop renting your intelligence" — ứng dụng RAG/agent chạy **local**: workspace
tách theo chủ đề, collector nạp tài liệu, vector DB tự chọn, agent + **MCP**, đa người dùng
(admin/manager/user), **citation** cho câu trả lời, API cho developer; telemetry mặc định tắt
và **không gửi nội dung**.

| Ý tưởng | Áp dụng cho dự án | Ưu tiên |
|---|---|---|
| **Citation/provenance cho tri thức** | `lessons.py` trả "tổ hợp X thua n lần" nhưng **không nói bằng chứng nào**. Thêm `evidence` mỗi bucket (`n`, `first_ts`, `last_ts`, 3 `sample_ts`) → in ra `LESSONS.md`; hội đồng trích bài học phải kèm mã bằng chứng ⇒ trả lời được "logic này ở đâu ra" | P1 (đề xuất) |
| **Workspace theo ngữ cảnh** | Đã tách kho theo instance (TESTNET/LIVE) + theo vai; bước sau: tách **theo chế độ thị trường** (trend/range) để `lessons.hint()` lấy đúng ngữ cảnh | P2 |
| **MCP để agent tự gọi công cụ** | Bọc các tool vận hành thành MCP server để client LLM điều khiển được bot — đích đến mà `capabilities.py --json` mới là bước 1 | P2 |
| **Đa người dùng + phân quyền** | Thêm **mã hoá vai** cho lệnh nguy hiểm (`restart_bot --reset`, `MARGIN_TYPE`) để agent không tự ý gọi | P3 |

### 15.2 `Open-Makers/ai-coding-agents-orchestrator` (Go, MIT) — workflow graph có cổng người

**Cốt lõi:** pipeline **Negotiate → Decompose → Implement (TDD) → Quality Review → Fix → Done**
với **cổng phê duyệt của người trước khi viết code**; vai PM (trọng tài) · QA · UX · Security ·
Coder; **beads** = sub-task bền vững ⇒ **resume được** khi đứt; **quality-gate loop** có trần
vòng lặp; artifact trong `.orchestrator/`; "recall project memory" trước khi làm; headless cho CI.

| Ý tưởng | Áp dụng cho dự án | Ưu tiên |
|---|---|---|
| **Beads — việc bền vững, resume được** | Việc vận hành của ta đang là *hành động rời* ⇒ hôm nay trả giá: watcher chờ BTW **hết 24h rồi thoát**, cổng khoá thêm ~2h (đã vá "đã phẳng thì làm tiếp", nhưng **hàng đợi bền vững** mới là gốc: `logs/ops_queue.json` + `resume`) | P1 (đề xuất) |
| **Cổng phê duyệt của người trước hành động nguy hiểm** | Bổ sung **hàng đợi câu hỏi** (`ops_questions.json`): bot/agent đặt câu hỏi → hiện ở `tools/ops.py` + Telegram → **chỉ chặn đúng hành động đó** tới khi có trả lời | P1 (đề xuất) |
| **Trọng tài + vòng lặp quality-gate có trần** | Hội đồng đã có `arbiter` + escalate/debate 2 vòng + trần ngân sách ✓; bổ sung: ghi rõ **vì sao trọng tài chọn** khi phiếu sát nút | P2 |
| **Artifact chuẩn hoá mỗi lần chạy** | Mỗi quyết định vận hành sinh 1 artifact `logs/ops/<ts>-<slug>.md` (bối cảnh → phiếu → hành động → kết quả) | P2 |

### 15.3 Blueprint của người vận hành — bản dịch sang dự án này

| Điểm trong blueprint | Tương ứng ở đây | Việc cần làm |
|---|---|---|
| **Knowledge warehouse chuẩn chỉ** (vì ít người can thiệp) | `lessons.py` + `lessons.json` + knowledge tree + `LESSONS_ENFORCE` | Thêm **provenance (mã bằng chứng)** + `tools/bug_catalog.py` (mã lớp lỗi ↔ test) như §13.2 |
| **Verification: testing · eval · traceability · observability** | 950 test · `council_eval` · `harness_audit` · `ops.py`/metrics · journal | **Mắt xích thiếu lớn nhất: TRACE theo từng lệnh** ("vì sao bot mở lệnh này?") ⇒ `tools/trace_trade.py`: in chuỗi signal → learner → lessons → phiếu hội đồng → size/risk → order → bảo vệ → đóng → bài học, kèm id/thời điểm |
| **"Honeycomb": graph business logic + call graph để sinh test** | `tests/` theo module, **chưa có graph** hành vi ↔ mã | Bản dịch nhỏ: `capabilities.py --json` (đã làm) + `bug_catalog.py`; xa hơn: graph `hành vi → hàm → test` |
| **Supervisor/lead + agent theo vai, handoff qua Jira/Confluence** | Hội đồng nhiều vai + `arbiter`; handoff của ta là journal + Telegram + `entries_gate` | Thêm **hàng đợi câu hỏi có resume** (14.2) = tương đương "nhắn lên Jira rồi chờ confirm" |
| **Nỗi lo 1: chất lượng code không bằng tự review** | Test bắt buộc trước commit + `capabilities --check` + `harness_audit` | Giữ kỷ luật; thêm luật "mỗi lớp lỗi phải có test chốt" (§13.2) |
| **Nỗi lo 2: "first brain" mất kiểm soát tri thức** | Đúng ca **"phiếu hội đồng bị nuốt"** và **"tier lite ⇒ 0 phiếu"**: hệ thống chạy mà *không ai biết nó quyết thế nào* | `trace_trade.py` + provenance + `event=OPS` cho mọi đổi trạng thái (đã có) |

**Đã làm ngay trong phiên này (từ 2 repo + blueprint):** `entries_gate` (cổng tạm dừng đọc lại
mỗi vòng, có vết journal) · `tools/wait_btw_isolate.py` (chờ → Isolated → hội đồng quyết →
resume) · `tools/capabilities.py` (manifest năng lực) · sửa **thứ tự interlock ⇒ hết vòng lặp
crash** (kill-switch ⇒ monitor-only, tự resume khi gỡ) · `RECONCILE` tự ghi bù lệnh đóng thiếu.
**P1 kế tiếp:** `trace_trade.py` · provenance cho lessons · `ops_queue.json` +
`ops_questions.json` · `bug_catalog.py`.

**(19/10) — CẢ 4 VIỆC P1 ĐÃ XONG** (mỗi việc có test chốt, xem `tools/bug_catalog.py --check`):
- `tools/trace_trade.py` — chuỗi "vì sao vào/đóng lệnh" (feature → phiếu hội đồng → review →
  bài học + **mã bằng chứng**), `--key "<tổ hợp>"` truy ngược bằng chứng từ journal.
- **provenance cho lessons**: `lessons.evidence_code()` (`EV-xxxxxx`, ổn định) +
  `lessons.evidence(journal, key)` (n/avgR/mốc thời gian/lệnh tệ nhất–tốt nhất) +
  cột **Mã** trong `LESSONS.md`.
- `tools/ops_queue.py` — hàng đợi câu hỏi cho người vận hành, **resume được qua phiên**
  (`logs/ops_questions.json` + `logs/ops_queue.json`), `--check` báo câu hỏi quá 24h.
- `tools/bug_catalog.py` — **20 lớp lỗi ↔ 33 test chốt**, `--check` báo khi test bị xoá/đổi tên
  (mất chốt chặn = lớp lỗi cũ có thể quay lại mà không ai biết).

**Còn lại (P2):** graph `hành vi → hàm → test`; 10 tool trong manifest chưa có test
(`python tools/capabilities.py --check` liệt kê).

**(19/10) — P2 đã làm phần khả thi (không cần khai báo tay, sinh từ dữ liệu thật):**
- **Graph `hành vi → file → test`**: `python tools/bug_catalog.py --graph` (Mermaid + bảng;
  nguồn là chính danh mục lớp lỗi nên không thể lệch thực tế). Hiện: **21 hành vi · 20 file · 36 test**.
- **26/26 tool có test** — `python tools/capabilities.py --check` = OK, `khong duoc test: khong co`
  (trước đó 10 tool không được test).
- **Bug catalog 21 lớp lỗi ↔ 36 test chốt** (`--check` báo khi test bị xoá/đổi tên) + lớp lỗi mới
  **B-021**: tiến trình test ghi đè `logs/heartbeat.json` của instance THẬT (pid 28000 không tồn tại).

## 17. (21/10) Đọc `abhixdd/ghgrab` — công cụ TUI tải file từ Git forge: áp dụng được gì

**Nó là gì:** CLI + TUI viết bằng Rust (`tokio` + `ratatui`) để *duyệt và tải từng file/thư mục*
từ GitHub/GitLab/Codeberg/Gitea/Forgejo mà không phải `git clone`; có tải release theo
OS/arch, LFS, preview file, và **2 bề mặt cho agent**: `ghgrab agent tree|download` (JSON) +
`ghgrab mcp` (MCP server stdio). Không liên quan nghiệp vụ giao dịch.

| Mục trong ghgrab | Bản chất | Với dự án này | Trạng thái |
|---|---|---|---|
| `Config::validate_path` + `Config::save` (kiểm tra thư mục cha/tồn tại/quyền ghi **trước** khi lưu) | Ghi cấu hình an toàn | Đối chiếu ⇒ phát hiện **5 chỗ ghi file trạng thái TRỰC TIẾP** (`.env`, `entries_pause.json`, `state.json`, `deadman.json`, artifact) ⇒ mất điện giữa lúc ghi là file cắt ngang | **ĐÃ ÁP DỤNG**: `atomic.py` (tmp → `fsync` → `os.replace`, retry khi Windows khoá file) + 6 call site + 10 test |
| Đọc/ghi state hỏng thì thế nào | — | `entries_gate.read()` trả `{}` cho **mọi** lỗi ⇒ file hỏng = bot **tự mở lại vào lệnh** trong khi người vận hành tưởng đang tạm dừng | **ĐÃ SỬA**: fail-safe (tạm dừng 6h rồi tự mở + ghi lại file hợp lệ) + 2 test |
| `truncated` trong response `agent tree` (API cắt bớt thì nói rõ) | Không im lặng cắt dữ liệu | Ta đã có: `watch_regress.read_tail_lines()` trả `(dòng, bị_cắt)`; `trace_trade --lines` | Đã có, không cần làm |
| `AgentEnvelope { api_version, ok, command, data, error{code,message} }` | Hợp đồng JSON ổn định cho agent/CI | 23 tool đã có `--json` nhưng **mỗi tool một kiểu** (`ok`/`err`/`error`/`status`); agent phải đoán | **ĐỀ XUẤT P2** (xem dưới) |
| `max_bytes` khi preview file (mặc định 8 KB) | Chặn phình context của agent | Đã có ở chỗ đọc log; riêng đọc journal vẫn theo số dòng, chưa có trần byte | P3 (thêm `--max-bytes` nếu cần) |
| `--token AUTO\|GH\|NONE` (tự lấy token, hoặc **tắt hẳn** xác thực) | Công tắc "không dùng credential" tường minh | Tương đương `DRY_RUN`/`--no-network`; hiện chưa có cờ chung "cấm gọi mạng" cho tool | P3 |
| `Credentials::new_for_url` + `Platform` enum (1 client cho 5 forge) | Trừu tượng đa nhà cung cấp | Chỉ có nghĩa khi thêm sàn thứ 2 (Bybit/OKX); hiện `exchange.py` đã gom Binance spot/futures/demo/live | P3 (khi cần) |
| `Downloader` song song `Semaphore(jobs=4)` | Giới hạn đồng thời | Ta quét symbol tuần tự + rate limit sẵn; song song hoá làm tăng rủi ro `-1003` | Không áp dụng |
| MCP server stdio (7 tool: `repo_tree`, `read_file`, `read_file_preview`, `list_releases`, `repo_info`, `search_repos`, `download_*`) | Cho AI ngoài (Cursor/Claude) gọi vào | Máy này giữ **KEY LIVE**; mở MCP = thêm bề mặt tấn công + nguy cơ lộ equity/journal. Nếu làm: chỉ read-only (`status`, `ops`, `journal tail`), `--no-keys`, chỉ stdio | **KHÔNG làm ngay** — cần hội đồng biểu quyết |
| `theme.toml` (thiếu key nào rơi về mặc định) / `log_error()` ghi file riêng, không làm chết app | Cấu hình khoan dung + lỗi không giết tiến trình | Ta đã theo đúng: `config.py` có default cho mọi biến, `ops` bắt lỗi im lặng | Đã có |
| Đóng gói đa hệ (cargo/pip/npm/nix/AUR) + readthedocs | Phân phối | 1 máy, 2 instance, không phát hành | Không áp dụng |

**Đã làm ngay trong phiên (đều là sửa lỗi, không phải tính năng):**
1. `atomic.py` — một chỗ duy nhất để ghi file trạng thái nguyên tử; `fsync` trước `replace`
   (nhiều "atomic write" quên `fsync` nên mất điện vẫn mất dữ liệu); retry `PermissionError`
   cho Windows (AV/indexer giữ handle).
2. Áp cho: `entries_gate`, `state_sync.go_live` (`.env` + `.bak-live` + `.live_flipped`),
   `run_forever` (nhịp tim + lock pid), `tools/deadman`, `tools/ops_artifact`, `tools/ops_queue`.
3. `entries_gate.read()` → **fail-safe** khi file hỏng (6h tự hết hạn, tự ghi lại file hợp lệ)
   thay vì fail-open. Đây là lỗi *im lặng* đúng nghĩa: bot vào lệnh trong khi người vận hành
   tin rằng đã tạm dừng.

**Phiếu hội đồng (21/10) — MCP server read-only: 1 ALLOW / 3 VETO ⇒ VETO.** Lý do của 3 phiếu
VETO: máy này giữ KEY LIVE trong `.env`, thêm một tiến trình MCP thường trực = thêm bề mặt tấn
công/lộ dữ liệu mà lợi ích chỉ là "hỏi trạng thái từ IDE khác"; ta đã có `tools/ops.py --json`
cho agent nội bộ. Không dựng MCP.

**Cần quyết (ghi vào `logs/ops_questions.json` nếu người vận hành muốn):**
- **P2 — Hợp đồng JSON chung** cho 23 tool: `{api_version, ok, command, data, error{code,message}}`.
  Lợi: hội đồng/agent đọc kết quả tool không cần regex, `bug_catalog` kiểm được schema.
  Hại: sửa 23 tool + test (rủi ro trung bình, không đụng đường tiền).
- **P2 — MCP read-only**: chỉ khi người vận hành thật sự muốn dùng Cursor/Claude Desktop để
  hỏi trạng thái bot; phải khoá cứng `--no-keys`, không có tool nào đặt/huỷ lệnh.

**Ghi chú kỹ thuật:** `download.rs` của ghgrab dùng `fs::write` trần (không tmp+rename) — tức
là **ta đang chặt hơn họ** ở khoản bền vững dữ liệu; thứ đáng học từ họ là *kiểm tra đích
trước khi ghi* và *hợp đồng JSON cho agent*, không phải cách tải file.

