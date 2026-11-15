# SECURITY_AUDIT — kiểm tra bảo mật 6 pha (theo `cloudflare/security-audit-skill`)

**Ngày:** 15/11/2026 · **Phạm vi:** `autonomous-trading-bot` (TESTNET) + `atb-live` (LIVE, cùng code base)
· **Dữ liệu máy đọc:** `security/findings.json` · **Lệnh kiểm:** `python tools\security_audit.py --check`

> Luật của báo cáo này (lấy từ skill của Cloudflare): **chỉ tính là lỗ hổng khi có một ranh giới bị vượt
> qua thật**, và mỗi mục phải kèm *bằng chứng máy kiểm được* (`file:line` + mẫu chuỗi) cùng *đường khai
> thác* cụ thể. Thiếu một tầng phòng thủ khi tầng khác đã chặn = **ghi chú hardening**, không phải lỗ hổng.
> Mức độ = *khả năng xảy ra × tác động*, không phải "lệch checklist".

## Pha 1 — Reconnaissance (bản đồ + ranh giới tin cậy)

**Ranh giới tin cậy (trust boundary) và bề mặt nhập (input surface)**

| # | Ranh giới | Đầu vào từ đâu | Ai kiểm | Ai chạm tiền |
|---|---|---|---|---|
| B1 | Internet → Telegram chat → `tools/telegram_bridge.py` | tin nhắn chat bất kỳ | allowlist `TELEGRAM_ALLOW_CHAT_IDS` + `TELEGRAM_ALLOW_WRITE` | có (`/restart`, `/reset ... confirm`) |
| B2 | HTTP cục bộ → `serve_glow.py` (mặc định `:8765`) | request HTTP bất kỳ trên máy | **không có** (chỉ loopback) | gián tiếp: đọc được `.env` |
| B3 | Tiến trình cục bộ → `vscode_lm_bridge` (`:8765`) | JSON "phiếu" giả | token tuỳ chọn (mặc định tắt) | không (phiếu chỉ để tham khảo) |
| B4 | Tin tức/mạng xã hội → prompt hội đồng | tiêu đề tin (văn bản lạ) | `agents.review_payload` allowlist | không (phiếu không mang size/SL) |
| B5 | Sàn (Binance) → `exchange.py` | lỗi/JSON từ API | phân loại lỗi + `api_ban` | có (đọc mã lỗi → quyết định huỷ) |
| B6 | File cục bộ → tool (`state_sync`, `restart_bot`, `selfops`) | `.env`, `logs/*.json`, PID | quyền ghi file của máy | có |
| B7 | Hội đồng → `turbo_demo` | phiếu JSON | trần độ tin (B-045) + interlock | có (nhưng phiếu không đặt được size) |

**Bề mặt HTTP/tiến trình (liệt kê đủ, không chọn mẫu):** `serve_glow.py` (stdlib `http.server`),
`graph_memory.py` + `memory_map.py` (chỉ phục vụ 1 file HTML, bind loopback), `vscode_lm_bridge/extension.js`
(HTTP nội bộ VS Code), `tools/telegram_bridge.py` (long-poll Bot API), `tools/restart_bot.py` +
`tools/ops.py` (taskkill/khởi động), `state_sync.py` (ghi `.env`).

**Khoá và bí mật nằm ở đâu:** tất cả trong `.env` của từng instance (`BINANCE_API_KEY/_SECRET`,
`BINANCE_LIVE_API_KEY/_SECRET`, `TELEGRAM_BOT_TOKEN`, token Cline/Copilot trong `~/.cline*`, `~/.copilot`).
`.env` + `logs/` **đã** bị git-ignore (`C-02`) — đây là lý do vụ `serve_glow` bên dưới phải tính là *rò rỉ
cục bộ*, không phải rò rỉ qua GitHub.

**Coverage ledger (đơn vị săn × lớp)**

| Lớp săn | Đơn vị | Trạng thái |
|---|---|---|
| lộ bí mật qua HTTP/tĩnh | `serve_glow.py`, `graph_memory.py`, `memory_map.py` | **F-01** (sửa) |
| xác thực kênh điều khiển | `telegram_bridge.cfg_for/poll/_write_cmd`, `notify.py` | **F-02**, F-04 (sửa) |
| thực thi mã / tiêm lệnh | `tools/*` gọi subprocess, `agents.py` provider CLI | C-01, C-05 (không thấy) |
| ghi `.env` bằng code | `state_sync.py`, `tools/instance_env.py` | F-05 (chấp nhận) |
| kill/khởi động tiến trình | `tools/restart_bot.py`, `run_forever.py` | F-06 (chấp nhận) |
| tin cậy đầu ra LLM | `agents.py`, `council_evals.py`, `turbo_demo.py` | ghi chú hardening (§6) |
| bảo vệ tiền | `live_guard.py`, `risk.py`, `portfolio.py`, `entries_gate.py` | C-04 (có) |

## Pha 2 — Coverage-led hunting (mỗi lớp một "thợ săn", ghi lại đã kiểm gì)

| Lớp | Đã kiểm cụ thể | Kết quả |
|---|---|---|
| lộ bí mật | 3 server HTTP có phục vụ thư mục không? `SimpleHTTPRequestHandler` có `translate_path` chặn không? | **F-01**: 2/3 server chỉ phục vụ 1 file; `serve_glow` phục vụ cả repo |
| xác thực kênh điều khiển | allowlist rỗng thì sao? token sai thì sao? log có token không? | **F-02** (fail-open), **F-04** (token trong log) |
| thực thi mã | AST quét `eval/exec/os.system/pickle.load/yaml.load/shell=True` trong `*.py` + `tools/*.py` | 0 sink (C-01) |
| tiêm lệnh | `subprocess` dùng list-argv hay chuỗi? | toàn bộ dùng list-argv (C-05); riêng `restart_bot` nhận PID từ file (F-06) |
| đầu ra LLM | phiếu có đặt được size/SL không? có ghi được `reason_code` tuỳ ý không? | không; phiếu chỉ đổi `veto/allow`, size do `portfolio.position_size` tính |
| bảo vệ tiền | interlock LIVE có chạy trước mọi vòng? | có: `turbo_demo.py:1619` gọi `live_guard.enforce` trước ADOPT (C-04) |


## Pha 3 — Candidate validation (mỗi ứng viên do *người khác* kiểm, bằng phép đo)

Nguyên tắc của skill: **người kiểm không phải người tìm** — nên mỗi ứng viên được kiểm lại bằng một phép
đo chạy được, không bằng cách đọc lại suy luận.

| Ứng viên | Phép kiểm (chạy lại được) | Trước | Sau |
|---|---|---|---|
| F-01 `.env` lộ qua HTTP | `python serve_glow.py --port 8897` rồi `HEAD http://127.0.0.1:8897/.env` | **200, `Content-Length: 29804`** (= đúng size `.env`), `type=application/octet-stream` | **404** |
| F-02 allowlist rỗng | `tools.telegram_bridge.poll(cfg={"allow_ids": []}, get=1 update lạ)` | xử lý lệnh, trả lời chat lạ | `handled=[blocked]`, không gửi gì |
| F-04 token trong log | đọc `str(e)` của `urllib3`: lỗi chứa `url: /bot<TOKEN>/sendMessage` | `log.warning("... %s", e)` | `redact(e)` → `/bot<token>` |
| F-03 bridge không token | `extension.js:53` + cấu hình mặc định `token: ""` | mọi process cục bộ gọi được | **chấp nhận** (xem lý do) |
| C-01 "không có sink" | `ast_hits()` quét 2 glob | — | 0 sink |

**Ứng viên bị LOẠI (không đủ bằng chứng ⇒ không được ghi thành lỗ hổng):**

| Ứng viên | Vì sao loại |
|---|---|
| "Tin tức độc hại (prompt injection) làm bot vào lệnh sai" | Phiếu không mang size/SL/giá; quyền veto **đo được = 0** (`agents.py --authority`: 11/11 "bằng chứng ngược dấu") ⇒ tác động tiền = 0. Giữ làm **hardening note** (§6), không phải lỗ hổng |
| "Journal bị tiêm dòng giả" | `json.dumps` escape `\n`, `journal.log_trade` ghi 1 dòng/trade; không có đường ghi chuỗi thô |
| "`--instance live` của `selfops` đụng state LIVE" | Đã chặn bằng code (việc đụng state `auto=False` + `--allow-live-state`), có test chốt trong `tests/test_selfops.py` |
| "Key Binance có quyền withdrawal" | **Không kiểm được từ code** — phải xem quyền key trên web Binance ⇒ `needs_validation`, ghi ở §6 |

## Pha 4 — Structured output (bảng phát hiện, máy đọc: `security/findings.json`)

| ID | Mức | Trạng thái | Ranh giới | Tóm tắt |
|---|---|---|---|---|
| F-01 | high | fixed (B-054) | HTTP cục bộ → file | `serve_glow.py` phục vụ cả repo ⇒ `GET /.env` trả nguyên key thật |
| F-02 | medium | fixed (B-055) | Internet → bot | allowlist chat_id **rỗng thì cho qua** (fail-open) |
| F-03 | medium | accepted | tiến trình cục bộ → phiếu | bridge Copilot không token + **trùng cổng 8765** (đã tách: `serve_glow` → **8770**) ⇒ giả phiếu |
| F-04 | low | fixed (B-054) | lỗi HTTP → log | token Telegram nằm trong chuỗi lỗi được ghi log |
| F-05 | low | accepted | tool → `.env` | `state_sync` ghi key LIVE vào `.env` bằng code, không backup |
| F-06 | low | accepted | file state → tiến trình | `restart_bot` kill PID đọc từ file state |

**Kiểm soát đã có (không phải lỗ hổng — kiểm bằng máy, `security_audit.py` xác nhận từng dòng)**

| ID | Kiểm soát | Cách kiểm |
|---|---|---|
| C-01 | Không có sink thực thi mã trong code sản xuất | AST trên `*.py` + `tools/*.py`: 0 hit `eval/exec/os.system/pickle.load/yaml.load/shell=True` |

## Pha 5 — Independent verification (máy kiểm lại báo cáo)

`python tools\security_audit.py --check` không tin phần văn xuôi: nó đọc **lại code** và so với từng mục.

| Loại bằng chứng | Ý nghĩa | Bắt được lỗi gì |
|---|---|---|
| `file` + `line` + `pattern` | dòng báo cáo phải đúng là dòng code thật (lệch ≤ 2 dòng còn chấp nhận) | sửa code nhưng quên cập nhật báo cáo |
| `absent` | mẫu **không được còn** trong file | lỗ hổng quay lại (hồi quy) |
| `present` | mẫu **phải còn** | ai đó gỡ mất lớp chặn |
| `tests` | `module.py::Class::test` phải tồn tại thật | báo cáo "đã sửa" mà không có test |
| AST (`controls`) | quét cú pháp, không grep | grep khớp cả chú thích ⇒ bỏ sót/ báo nhầm |
| bảng trong `.md` | số dòng `F-` phải bằng số phát hiện trong JSON | báo cáo và số liệu lệch nhau |

Số đo hiện tại: **6 phát hiện** (high 1 · medium 2 · low 3) · **5 kiểm soát** · **5 test chốt** · **4 kiểm chứng V-01…V-04** · `--check` = **0 lệch**.

## Pha 6 — Reporting (trung lập với mục tiêu, có việc làm tiếp)

**Việc làm ngay (đã làm trong đợt này):** F-01 chặn `translate_path`; F-02 đảo thành fail-closed;
F-04 `redact()` ở cả 2 nơi ghi log; thêm cảnh báo khi `serve_glow --host` mở ra mạng ngoài;
**tách cổng**: `serve_glow.py` mặc định **8770** (trước 8765, trùng cổng bridge Copilot).

**Kiểm chứng bằng phép đo (15/11) — 4 mục, ghi trong `security/findings.json` → `validations`:**

| ID | Câu hỏi | Cách đo | Kết quả |
|---|---|---|---|
| V-01 | Key có quyền rút tiền không? | `sapiGetAccountApiRestrictions` (chỉ đọc) | `enableWithdrawals=false` · `enableInternalTransfer=false` · `permitsUniversalTransfer=false` · `enableFutures=true` · `ipRestrict=true` ⇒ **không rút được tiền**; riêng **`enableSpotAndMarginTrading=true` là quyền thừa, nên tắt** |
| V-02 | Token Telegram có vào log chưa? | quét regex `bot<so>:<chuoi>` trên `logs/` **cả 2 instance** | **0 lần** ⇒ F-04 là rủi ro tiềm ẩn, chưa xảy ra |
| V-03 | Cooldown theo cặp chặn đúng? | `in_cooldown('<cặp vừa lỗ>', now=t+10′ / t+61′)` với `t` = mốc CLOSE thật | AERO −1,0147R: t+10′ **chặn** (còn 50′), t+61′ **cho qua** |
| V-04 | Code mới đã chạy thật? | `restart_bot.py --target testnet` rồi `--target live`, sau đó `ops.py` | TESTNET 102884 (round 1, equity 3226,95, 4 vị thế) · LIVE 80788 (round 1, equity 38,04, 3 vị thế) · **0 lỗi/7 phút**, không mất vị thế |

**Việc còn lại (chờ người quyết — đã ghi vào `ops_queue.py`):**
1. **Tắt quyền Spot/Margin** của key futures (V-01) — thao tác trên web Binance, không làm bằng code được.
2. **Cổng 8765**: nếu bật quyền veto cho hội đồng thì đặt token bridge (F-03); `serve_glow` đã rời sang 8770.
3. **Rotate token Telegram**: KHÔNG cần vì V-02 = 0 lần; chỉ rotate nếu nghi máy bị đọc trộm.

**Hardening note (không phải lỗ hổng, nhưng nên làm khi rảnh):**
- Prompt hội đồng chứa tiêu đề tin từ nguồn ngoài (B4): hiện vô hại vì phiếu không mang quyền size/SL và
  quyền veto = 0. **Điều kiện đổi**: trước khi bật `AGENT_VETO_AUTHORITY`, phải có bộ lọc "văn bản lạ"
  (đếm chỉ thị trong tin) — nếu không, đây sẽ thành lỗ hổng thật.
- `state_sync` (F-05): thêm backup `.env` trước khi ghi key (đã có tiền lệ: `.env.bak-*` bị git-ignore).
- `restart_bot` (F-06): đối chiếu tên tiến trình trước khi `taskkill`.

**Điều báo cáo này KHÔNG kết luận:** không kết luận "hệ thống an toàn". Nó chỉ nói: với 7 ranh giới ở Pha 1,
6 mục trên là những gì tìm được bằng bằng chứng; 3 mục đã sửa (F-01, F-02, F-04), 3 mục chấp nhận có lý do
và điều kiện đổi trạng thái. Chạy lại lần nữa (nhiều lượt) sẽ tìm thêm — skill của Cloudflare đo được rằng
một lượt chỉ tìm khoảng **một nửa** số lỗi mà nhiều lượt tìm được.

| C-02 | `.env` và `logs/` bị git-ignore | quét `.gitignore`; `git ls-files logs` = **0 file** |
| C-03 | Server HTTP của bot chỉ listen loopback | quét `graph_memory.py`, `memory_map.py`, `extension.js` |
| C-04 | Interlock LIVE trước mọi vòng trade | quét `live_guard.py`: `LIVE_CONFIRM != true` + `MIN_TRADES` + `MIN_PF` |
| C-05 | `telegram_bridge` gọi tool bằng argv cố định | quét `run_tool(argv: list` + không có `shell=True` |
