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

## Tổng hợp việc nên làm tiếp

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

