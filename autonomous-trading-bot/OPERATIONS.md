# OPERATIONS.md — Vận hành 2 instance bot (nhanh, ổn định, ít lệnh)

> Cập nhật 12/10/2026. Đọc kèm `CONTEXT.md` (§0–§6) và `AGENTS.md`.
> Mục tiêu: mọi việc thường ngày chỉ cần **1 lệnh**, không phải mở log bằng tay,
> không có cửa sổ console nhảy lên, và không làm treo terminal VS Code.

---

## 1. Ba lệnh dùng hằng ngày

```bash
python tools/ops.py                 # 1) Sức khoẻ 2 instance (~25 dòng)
python tools/restart_bot.py --target live --reset --wait-flat   # 2) Restart an toàn
python tools/pick_symbols.py --target live --top 40 --dry-run   # 3) Xem danh sách cặp
```

Hoặc trong VS Code: **Ctrl+Shift+P → Tasks: Run Task** → chọn
`Ops: bao cao 2 instance` / `Ops: restart LIVE (reset + cho phang)` / `Test: toan bo suite`.
Task chạy ở panel riêng, **không** dùng shell tích hợp nên không bị "Command
completion could not be observed".

`tools/ops.py` in ra: vòng quét hiện tại, nhịp tim, kill-switch, số vị thế,
và **đếm lỗi trong N phút** (FETCH_TIMEOUT / DATA_FAIL / 429 / pool full /
ORDER_FAILED / SKILL_DATA...). Kết luận cuối là `OK` hoặc `CAN XEM: <instance>`.

---

## 2. Không còn cửa sổ console nhảy lên (12/10)

**Nguyên nhân**: bot chạy dưới `pythonw.exe` (không có console). Mọi tiến trình
con do Windows spawn từ tiến trình không-console sẽ **tự mở một cửa sổ console
mới** — cụ thể là `git.exe` mỗi 30 phút (do `state_sync.py` chạy `git commit/push`
từ supervisor), và `taskkill`/`tasklist` của watchdog.

**Cách sửa**: module `winproc.py` (một chỗ duy nhất):

```python
import winproc
subprocess.run(["git", "status"], **winproc.hide_kwargs())   # CREATE_NO_WINDOW + SW_HIDE
```

Đã áp cho: `state_sync.py` (git + taskkill), `run_forever.py` (taskkill/tasklist),
`restart_when_flat.py`, `status.py`, `memory_graph.py`, `memory_agent.py`,
`serve_glow.py`, `bench_retrieval.py`, `clinepass_review.py`, `agents.py`, và
`tools/restart_bot.py`. Test chốt: `tests/test_ops_tools.py::TestWinproc`.

---

## 3. Vì sao "làm hết mục tiêu Next" mất ~3 ngày — và cách rút ngắn

**Đo thực tế**: 3 ngày cho ~10 mục, trong đó thời gian *máy chạy* chỉ khoảng vài
giờ. Phần lớn là **vòng chờ + thao tác lặp**. Nguyên nhân cụ thể:

| # | Nguyên nhân | Thời gian mất | Cách rút ngắn (đã làm / cần làm) |
|---|---|---|---|
| 1 | **Shell VS Code chập chờn**: mỗi lệnh foreground mới *đóng* terminal cũ, lệnh đang chạy bị kill; `Start-Sleep 300+` bị cắt ngang; output log dòng dài hàng KB làm treo terminal | ~40% | Dùng **process tách rời + ghi ra file** (đã làm), **tasks.json** (đã làm), và `tools/ops.py` thay cho `Get-Content -Tail` |
| 2 | **Vòng quét 5 phút × 458 cặp**: mỗi thí nghiệm phải chờ 1–2 vòng mới biết đúng/sai | ~25% | Thu hẹp danh sách (LIVE 40 → POLL 120s; TESTNET 150 → POLL 180s): **phản hồi nhanh 2.5×** |
| 3 | **Sai giả thuyết lần 1** (cache OHLCV chưa đủ — còn OI/funding/liq ~1800 req/vòng) → phải sửa rồi chờ lại | ~15% | Đo **số request/vòng** trước khi sửa (đếm endpoint trong `_fetch_one`), không chỉ đo weight |
| 4 | **Kill-switch trip làm bot dừng** → phải dừng bot, reset, chạy lại (5–6 lệnh tay), rồi chờ khởi động lại | ~10% | `tools/restart_bot.py` (1 lệnh, đã làm) + `--wait-flat` đọc sàn thật |
| 5 | **Chờ bot khởi động lại + adopt vị thế + vòng 1 nặng** (mỗi lần restart ~5 phút) | ~7% | Tránh restart: đưa tham số quét vào `.env` (đã làm) và **không** restart khi chỉ đổi danh sách cặp — dùng `apply_symbols` + restart 1 lần |
| 6 | Máy nặng: 2 instance × 8 luồng + hội đồng 15 model + 690 test + VS Code | ~3% | Thu hẹp danh sách; chạy test module nhỏ trước, full suite sau |

**Quy tắc vàng để lần sau nhanh**:

1. **Vòng phản hồi ngắn nhất trước**: `python -m unittest tests.<module>` (≈0.2s)
   → rồi mới full suite (≈150s) → rồi mới chạy bot thật.
2. **Đo trước khi sửa**: log 1 vòng quét có bao nhiêu request/lỗi? (`tools/ops.py`).
3. **Thay đổi gộp theo lô**: nhiều fix trong 1 lần restart, không restart từng fix.
4. **Không chờ bằng `Start-Sleep` dài trong terminal**: spawn process nền + đọc file.
5. **Ưu tiên danh sách nhỏ**: 40 cặp cho LIVE vừa dễ kiểm soát rủi ro vừa cho vòng
   quét 2 phút → thấy kết quả nhanh gấp 2.5 lần.

### 3.1 Giật lag / treo máy / mất kết nối

- **Nguyên nhân chính**: (a) 458 cặp × 2 instance → ~1.4 request/giây mỗi instance
  + 8 luồng HTTP; (b) hội đồng LLM gọi CLI node/copilot mỗi lệnh; (c) `git commit/push`
  mỗi 30 phút; (d) log `turbo_err.log` phình (dòng tóm tắt 458 cặp ~5–10 KB/dòng).
- **Giảm tải đã áp**: danh sách 40/150 cặp; cache OHLCV tăng dần + cache OI/liq 600s
  (giảm ~75% request); `SCAN_WORKERS=8`; cửa sổ console đã ẩn (không còn tranh GPU/foreground).
- **Nếu vẫn lag**: `tools/pick_symbols.py --target testnet --top 80` rồi `apply_symbols`,
  hoặc tạm dừng TESTNET khi cần máy cho việc khác:
  `python tools/restart_bot.py --target testnet --dry-run` (xem trước) rồi
  `Stop-Process -Name pythonw` (tắt hết bot) — nhớ bật lại bằng
  `python tools/restart_bot.py --target both`.
- **Mất kết nối (dual-WAN)**: bot đã có retry + cache + cooldown; nếu thấy
  `FETCH_TIMEOUT` tăng vọt trong `ops.py`, kiểm tra mạng trước khi sửa code.

---

## 4. Thu hẹp danh sách cặp (LIVE 40 / TESTNET 150) — đã áp 12/10

**Vì sao**: 458 cặp trên tài khoản 19–20 USDT làm cả 2 instance **trip kill-switch
cùng ngày** (LIVE −2.27%, TESTNET −2.15%): nhiều lệnh nhỏ, khó kiểm soát rủi ro,
và vòng quét nặng. Danh sách hẹp + thanh khoản cao = spread thấp, dễ đạt notional
tối thiểu, vòng quét nhanh, dễ đối soát.

```bash
python tools/pick_symbols.py --target live --top 40 --dry-run   # xem trước
python tools/pick_symbols.py --target live --top 40             # ghi logs/live_whitelist.txt
python tools/apply_symbols.py --target live                     # nap vao atb-live/.env
python tools/restart_bot.py --target live --reset --wait-flat    # ap dung
```

Tiêu chí (tất định, in ra lý do từng cặp): bỏ cặp đã ban vĩnh viễn
(`logs/banned_pairs.json`) → bỏ cặp journal đã chứng minh thua (`n≥5`, `avgR≤−0.10`)
→ **giữ cặp đang có vị thế** → xếp theo khối lượng 24h → lấy top N.

Muốn quay lại danh sách đầy đủ: `python tools/pick_symbols.py --target live --clear`
rồi `apply_symbols --target live --no-whitelist`.


> Nếu vẫn thấy cửa sổ: đó là cửa sổ do **chính bạn** mở (chạy `.cmd`/`git` bằng tay)
> — script chạy ngầm không còn tạo cửa sổ nào.


---

## 5. Restart an toàn — 1 lệnh, đúng thứ tự

```bash
python tools/restart_bot.py --target both --reset --wait-flat --stagger 90
python tools/restart_bot.py --target live --dry-run          # xem truoc, khong lam gi
```

Thứ tự thực hiện (đúng như `CONTEXT.md` §6):

1. `--wait-flat`: chờ **hết vị thế** trước khi tắt. Nguồn sự thật là **sàn**
   (`fetch_positions`), không phải journal (journal hay còn dòng OPEN mồ côi).
   Không đọc được sàn ⇒ **không** tắt (fail-safe).
2. `taskkill /F /T` cây supervisor (kill cả tiến trình con + luồng), **ẩn cửa sổ**.
3. `--reset`: xoá `logs/risk_state.json` — **chỉ khi bot đã dừng** (nếu bot đang
   chạy, nó ghi lại state cũ ngay vài giây sau ⇒ reset vô hiệu).
4. Chạy lại `pythonw run_forever.py` (ẩn cửa sổ).
5. `--stagger 90`: chờ giữa 2 instance để 2 vòng quét đầu không chồng nhau.

Sau đó luôn kiểm tra: `python tools/ops.py`.

---

## 6. Shell VS Code chập chờn — nguyên nhân và cách làm việc

**Triệu chứng**: `[Command completion could not be observed]`, output biến mất,
lệnh sau kill lệnh trước, `Get-Content -Tail` trên log lớn làm treo panel.

**Nguyên nhân**:
1. Shell integration của VS Code đôi khi không báo kết thúc (đặc biệt khi có
   process con giữ stdout, hoặc output rất lớn).
2. Mỗi lệnh foreground mới trong cùng terminal **thay thế** lệnh đang chạy.
3. Log của dự án có dòng dài hàng KB (tóm tắt 458 cặp) → panel render cực nặng.

**Quy tắc làm việc (đã kiểm chứng trong phiên 12/10)**:

- Lệnh **ngắn** (<30s) chạy trực tiếp; **mọi việc dài** (chờ vòng quét, chạy suite,
  restart) → dùng **task VS Code** hoặc process nền rồi **đọc file kết quả**:
  `Start-Process python -ArgumentList ... -WindowStyle Hidden` + `Out-File`.
- Không bao giờ `Start-Sleep` > 60s trong terminal tích hợp.
- Không `Get-Content -Tail` log lớn: dùng `python tools/ops.py` (đọc trực tiếp file,
  in gọn ≤25 dòng).
- Nếu terminal đã "kẹt": mở terminal mới (nút `+`) thay vì gửi lệnh vào terminal cũ.
- Trong VS Code: giảm `terminal.integrated.scrollback` (vd 1000) để panel nhẹ hơn.

---

## 7. Bảng lệnh tham chiếu

| Việc | Lệnh |
|---|---|
| Sức khoẻ 2 instance | `python tools/ops.py [--minutes 15] [--json]` |
| Restart an toàn | `python tools/restart_bot.py --target both --reset --wait-flat` |
| Xem/chọn danh sách cặp | `python tools/pick_symbols.py --target live --top 40 --dry-run` |
| Nạp danh sách vào `.env` | `python tools/apply_symbols.py --target both` |
| Vị thế thật trên sàn | `python positions.py` (chạy trong từng instance) |
| Kill-switch | `python risk.py --reset` (bot phải đã dừng) |
| Test nhanh 1 module | `python -m unittest tests.test_ops_tools` |
| Audit model hội đồng | `python tools/model_audit.py [--target live]` |
| Audit 1 repo HF | `python tools/model_audit.py --hf <repo> --params-b <B> --bits 8` |
| Kiểm kê lệnh chờ (thường + **algo**) | `python tools/orders_audit.py [--target live]` |
| Gom lệnh còn 1 SL + 1 TP / vị thế | `python tools/orders_audit.py --target live --dedupe` |
| **Chấm điểm setup** (1 lệnh, offline) | `python tools/harness_audit.py --both` |
| Chấm điểm + kiểm tra lệnh bảo vệ thật | `python tools/harness_audit.py --target live --with-exchange` |
| **Rút kinh nghiệm từ journal** | `python tools/learn_review.py [--target live] [--impact]` |
| Đo quyền veto (luật VETO-vs-baseline) | `python agents.py --authority --rule baseline` |
| **Sức khoẻ hội đồng** (model nào treo) | `python agents.py --council-health --hours 48` |
| **Lý do thật từng phiếu** (model nào treo vì gì) | `python tools/journal_tail.py 40 [live]` |
| Dò model hội đồng nào thật sự chạy (song song) | `python tools/probe_cline.py` |
| Kill-switch LIVE + chạy lại (dừng → xoá risk_state → chạy) | `python tools/restart_bot.py --target live --reset` |
| **Hội đồng đọc tài liệu/diff và cho ý kiến** | `python clinepass_review.py --task strategy_review --bundle none --file <tài liệu>.md --engine clinepass --provider clinepass --model cline-pass/mimo-v2.6-pro --concurrency 3 --output-dir logs/council_review` |
| Model nào còn chạy được (dò song song, tốn quota) | `python tools/probe_cline.py` — hoặc `python clinepass_review.py --check` |
| **Chấm điểm TỪNG model hội đồng** (theo kết quả thật) | `python tools/council_eval.py [--target live] [--hours 336] [--min-n 8] [--json]` |
| **Sao lưu có kiểm chứng** (.env + journal + state) | `python tools/backup.py [--target live] [--keep 14]` → `backups/*.zip` |
| **Đăng ký backup hằng ngày** (Task Scheduler) | `python tools/backup.py --install-task [--task-time 03:30]` / gỡ: `--uninstall-task` |
| **Dead-man switch** (báo khi bot NGỪNG) | `python tools/deadman.py [--dry-run] [--json]` — điền `HEALTHCHECKS_URL` vào `.env` để nhận cảnh báo ngoài máy |
| **Đăng ký dead-man mỗi 15 phút** | `python tools/deadman.py --install-task [--task-min 15]` / gỡ: `--uninstall-task` |
| **`/evolve`** (rút kỹ năng có tên từ tổ hợp) | `python tools/learn_review.py --dry --evolve` |
| **`/prune`** (trục xuất tổ hợp cũ khỏi lessons.json) | `python tools/learn_review.py --prune --stale-days 30` |
| Kiểm chứng 1 model qua gateway | `python -c "from agents import ClineProvider as C; print(C(model='cline-pass/qwen3.7-plus').complete('sys','Tra loi JSON: {\"action\":\"ALLOW\"}'))"` |
| Quét ngưỡng lessons | `python tools/learn_review.py --target live --sweep` |
| Đổi model local (llamafile ↔ ollama) | `python tools/switch_local_model.py .env llamafile` |
| Metrics cho Prometheus | `python tools/ops.py --prom` → `logs/metrics.prom` |
| Model local không cần daemon | `python tools/llamafile_setup.py --check` |
| Test toàn bộ | `python -m unittest discover -s tests` (**690 test**) |
| Đẩy code | `tools\git-sync.cmd "mo ta"` |
