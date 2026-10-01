# Bảng điều khiển biểu đồ tương tác (Live + Preview)

Mở file SVG trực tiếp trong Explorer (click vào) và xem trước, hoặc mở `PREVIEW_README.md` rồi bấm `Ctrl+Shift+V` để xem trước markdown. Nếu cần zoom/pan live, mở HTML thực tế: `graph_memory.html`, `memory_map.html`.

## 1. Graph Memory (code structure)

- File: `preview_graph.svg` — 370 nodes, 8423 edges.
  - Hiển thị None edge trong SVG preview (giới hạn 1200).
- Hubs: `preview_graph_hubs.svg` — 85 hub trung tâm, có nhãn.
  - Hiển thị None edge trong SVG preview (giới hạn 1200).

Điểm mạnh (top hub): [('memory_agent.py::__init__', 228), ('bot.py::__init__', 176), ('graph_memory.py::__init__', 176), ('memory_graph.py::__init__', 176), ('learner.py::__init__', 167), ('sentiment.py::__init__', 163)]

## 2. Memory Map (code + memories)

- File: `preview_map.svg` — 911 nodes, 16054 edges.
  - Hiển thị None edge trong SVG preview (giới hạn 1200).
- Hubs: `preview_map_hubs.svg` — 80 hub, có nhãn.
  - Hiển thị None edge trong SVG preview (giới hạn 1200).

Điểm mạnh (top hub): [('code:def:__init__', 1277), ('mem:def:__init__', 285), ('code:def:main', 248), ('mem:def:main', 198), ('code:def:sync', 191), ('code:def:save', 184)]

## 3. Glow Map — giao diện 3D kiểu "Codebase Memory" (offline, 0 thư viện)

- File: `glow_map.html` (mở trực tiếp bằng double-click / `file://`), ảnh chụp: `glow_map_preview.png`.
- **Bản WebGL thật**: `glow_map_webgl.html` (three.js r128 vendor hoá, UnrealBloom + Bokeh DoF) — cùng dữ liệu,
  cùng sidebar, xem mục *Bản WebGL* bên dưới.
- Tab `Graph Memory` (402 nodes / 8.756 edges) và `Memory Map` (939 nodes / 16.399 edges).
- Bố cục giống ảnh mẫu: header + sidebar `FILTERS` (chip theo node type & edge type kèm số lượng,
  `All | None`, legend spectral, `Show labels`, ô Search, danh sách file, 3 slider hiển thị) + canvas 3D.

### Cách có được giao diện này — 2 đường

1. **Dùng UI gốc** (`memory-mcp/graph-ui`, React + three.js + UnrealBloom — chính là ảnh bạn gửi):
   ```bash
   codebase-memory-mcp --ui=true --port=9749     # rồi mở http://127.0.0.1:9749
   ```
   Muốn sửa frontend: `cd memory-mcp/graph-ui && npm.cmd install && npm.cmd dev`
   (dùng `npm.cmd` vì `npm.ps1` bị chặn bởi ExecutionPolicy trên máy này; cần backend ở cổng 9749).
2. **Bản offline tự chứa** (không cần npm/node/CĐN — chạy được cả trong VS Code integrated browser):
   ```bash
   python build_glow.py        # đọc graph_memory.json + memory_map_data.json -> glow_map.html
   ```

### Bản offline đã copy đúng các thông số "look" từ graph-ui

| Thành phần | Nguồn trong graph-ui | Giá trị dùng lại |
|---|---|---|
| Layout 3D + xoay | `GraphScene.tsx` (three.js) | yaw/pitch + phối cảnh `CAM_DIST=3.2`, auto-rotate sau 60s, fly-to ease-out cubic |
| Node | `NodeCloud.tsx` + `lib/colors.ts` | màu theo **spectral class** (O 50+, B 26-50, A 13-25, F 7-12, G 4-6, K 2-3, M 0-1), size theo degree |
| Glow node | `lib/density.ts nodeGlowBoost` | `1.35 + blueness*2.4 + redness*0.9` (hub xanh sáng nhất) |
| Edge | `EdgeLines.tsx` | additive blending, cùng cluster `0.25` / khác cluster `0.06`, nhân `1/sqrt(edgeCount)` (`EDGE_REF=2500`) |
| Bloom | `GraphScene.tsx` `Bloom` | `intensity 1.45`, `radius 0.6` → pass blur + ngưỡng sáng + cộng màu |
| Highlight | `NodeCloud.nodeColor` | node không được chọn giảm còn ~0.15, edge 2 đầu không chọn bị bỏ |

> Canvas2D + `globalCompositeOperation='lighter'` nên không cần WebGL/three.js: mở bằng `file://` là chạy,
> không CDN, không CORS. Layout 3D (Coulomb + spring + vỏ cầu) được tính sẵn bằng numpy lúc build (~7s).

### Bản WebGL thật (`glow_map_webgl.html`) — three.js r128 + UnrealBloom + Bokeh

- File: `glow_map_webgl.html` (~1,2 MB, **tự chứa**: vendor three.js r128 nhúng inline + engine + payload,
  không CDN, không npm, mở `file://` là chạy). Nguồn: `glow_map_webgl_template.html` (shell + DOM/sidebar dùng
  chung với bản Canvas2D) và `glow_map_webgl_engine.js` (scene + passes).
- `python build_glow.py` sinh **cả hai** file từ **cùng một payload** (`const DATA = {...}`):
  `test_payload_matches_canvas2d` so trực tiếp `id` / `edges` / `pos` / `sat` giữa 2 bản nên không thể lệch dữ liệu.
- Kỹ thuật: node = `InstancedMesh` (màu + size theo instance), edge = `LineSegments` bucket theo
  (cluster, loại edge) đúng `W_SAME=0.25` / `W_CROSS=0.06`, cross-link 2 galaxy màu `#fb923c`,
  hạt flow = `Points`, bloom `strength 1.45 / radius 0.6 / threshold 0.3`, `BokehPass` cho DoF,
  `OrbitControls` cho kéo/xoay, nhãn node = overlay DOM `#wlabels` (không phải sprite) nên chữ luôn nét.
- Nếu máy không có WebGL: banner đỏ `#err` + link mở ngay bản Canvas2D `glow_map.html` (không màn hình trắng).
- Đồng bộ shell: `glow_map_webgl_template.html` **phải** giữ y nguyên `<head>/<style>/sidebar/header` của
  `glow_map_template.html` (2 file chỉ khác phần dữ liệu + engine + 3 placeholder
  `__GLOW_VENDOR__` / `__GLOW_ENGINE__` / `__GLOW_PAYLOAD__`). Sửa sidebar/header thì copy sang cả 2 file,
  test `test_shares_payload_and_shell_with_canvas2d` sẽ báo nếu lệch.

| Hiệu ứng | Checkbox | Cài đặt |
|---|---|---|
| Twinkle (sao nhấp nháy) | `fxTwinkle` | lệch pha theo instance, node sáng nháy mạnh hơn |
| Depth of field | `fxDof` | `BokehPass` — focus 3.4 / aperture 0.00013 / maxblur 0.009 |
| Dòng chảy cross edge | `fxFlow` | `Points` chạy dọc cross-link, `AdditiveBlending` |
| Sóng lan khi click | `fxRipple` | pool vòng tròn dựng theo mặt phẳng nhìn, bung ra rồi tắt (tối đa 8) |
| Galaxy vệ tinh | `fxSat` | 273 node `mem:*` + 281 cross-link (từ `cross_index.json`) |
| Nebula + vignette | `fxNebula` | 3 sprite nebula `NormalBlending` (opacity 0.16) + vignette CSS `#stage::after` |
| Tự xoay khi rảnh | `fxAuto` | quán tính yaw/pitch, dừng khi kéo, tự quay lại sau 60s |

### Kiểu khối cầu 3D (cụm sao / vỏ cầu / cầu đặc)

Cả 3 kiểu layout được tính sẵn ở Python trong **cùng một payload** (`pos`, `posShell`, `posBall`, và
`sat.pos*` cho vệ tinh) → đổi kiểu chỉ là đổi con trỏ mảng toạ độ đang dùng trong RAM: **không** dựng lại
danh sách edge, **không** đụng tới 7 hiệu ứng.

| Kiểu | Chip / phím | Toạ độ dùng | Ghi chú |
|---|---|---|---|
| Cụm sao | `Cụm sao` / `1` | `pos` — Coulomb repulsion + spring theo edge + kéo về vỏ cầu r=1 (force layout 200/130 iter) | mặc định, giống ảnh graph-ui |
| Vỏ cầu | `Vỏ cầu` / `2` | `posShell` — rải đều Fibonacci **đúng trên mặt cầu r=1** (mọi node `\|r\| = 1.000`) | kèm lưới 5 vĩ tuyến + 6 kinh tuyến mờ (alpha 0.085) để nhìn rõ khối cầu |
| Cầu đặc | `Cầu đặc` / `3` | `posBall` — cùng hướng Fibonacci × bán kính `r = 0.10 + 0.90·∛u` | mật độ đều theo thể tích, bán kính trung bình ~0.78 |

- Galaxy vệ tinh (273 `mem:*`) cũng có 3 bộ toạ độ (`sat.pos`, `sat.posShell`, `sat.posBall`), luôn ở vỏ
  ngoài bán kính `2.15` → cross-link `#fb923c` + dòng chảy vẫn nối đúng vào node chính tương ứng.
- Bản Canvas2D thu khung hiển thị **0.60** cho vỏ cầu/cầu đặc (`LAY_SCALE`) để khối cầu + vệ tinh vừa khung
  nhìn; bản WebGL dùng `fov 50` + camera cách `3.7` nên bán kính 1 vừa khung sẵn. Hệ số này chỉ ảnh hưởng
  hiển thị, không đổi toạ độ dữ liệu (`stats().meanR` luôn đo theo dữ liệu: 0.321 / 1.000 / 0.775).
- Đo bằng **pixel thật** khi render (headless, tắt vệ tinh để đo khối chính): vỏ cầu `box=500x504 ratio=0.99`,
  cầu đặc `box=484x476 ratio=1.02` → đúng hình tròn; cụm sao `box=1086x700 ratio=1.55` (không đổi so với trước).
- Ảnh chụp thật để xem ngay: `glow_map_shell_preview.png` (vỏ cầu), `glow_map_ball_preview.png` (cầu đặc).
- Thử nhanh ở DevTools: `__glow.layout('shell')` · `__glow.layouts()` ·
  `__glow.stats()` → `{layout, globe, meanR, satMeanR, edges}`.

### Kiểm tra bản WebGL (headless, đọc pixel thật)

```bash
chrome --headless=old --use-gl=swiftshader --window-size=900,650 \
       --virtual-time-budget=25000 --dump-dom file:///<path>/glow_map_webgl.html
# -> <title>GLOW_WGL_OK 402n/8756e lit=100.0% bright=39803 gl=WebGL 2.0 (OpenGL ES 3.0 Chromium)</title>  (ví dụ)
```

- Self-test `wSelfTest()` đọc 600x360 pixel giữa framebuffer bằng `gl.readPixels`, đếm pixel sáng rồi ghi vào
  `document.title`: `GLOW_WGL_OK <n>n/<m>e lit=..% bright=.. gl=..`; JS chết / canvas trống (<2% sáng) / không có
  WebGL -> title `GLOW_WGL_ERR ...` + banner đỏ.
- `--screenshot` headless **không** xuất được PNG cho trang WebGL trên máy này (compositor SwiftShader treo),
  nên ảnh preview phải chụp bằng GPU thật: mở `glow_map_webgl.html` trong Chrome/Edge rồi screenshot.
- Kiểm tra tương tác (sat count, hover tooltip, chọn node, toggle fx, đổi dataset) bằng DevTools console:
  `window.__glow` (`stats()`, `fx('twinkle', false)`, `select(i)`, `hoverAt(x, y)`, `top()`, `view()`).

### Lớp "tín hiệu truy xuất AI" — 5 model agent chạy chung cho MỌI bản đồ

Cả `glow_map.html` (Canvas2D) và `glow_map_webgl.html` (WebGL) nhúng **nguyên văn**
cùng một bộ `glow_signals.js` + `glow_signals_lib.js` + `glow_signals.css`
(build thay placeholder `__GLOW_SIGNALS_LIB__` / `/*__GLOW_SIGNALS_CSS__*/`) nên
HUD, logic truy xuất, bus sự kiện **giống hệt nhau từng byte**.

| File | Vai trò |
|---|---|
| `glow_retrieval.py` | Lõi: inverted index + BM25-lite, cache LRU+TTL, tuner tự hạ `k` khi p95 vượt ngân sách ms, đo p50/p95, token trả về vs đọc nguyên file, `fingerprint()` (chuỗi 12 ký tự → 2 bản đồ đồng bộ) |
| `glow_agents.py` | Chạy đồng bộ nhiều agent trên dữ liệu thật → `retrieval_log.jsonl` + `--export glow_signals.json` |
| `retrieval_hook.py` | **Bất kỳ AI nào** (Cline / GPT / Claude / Qwen / DeepSeek / tool ngoài) ghi được 1 sự kiện truy xuất |
| `glow_signals.js` | Kernel thuần (tokenize / BM25 / cache / tuner / metrics) — giống hệt bản Python, không đụng DOM |
| `glow_signals_lib.js` | Bus `window.__GSL`: HUD, vòng sáng quanh node theo agent, SSE/poll, tự `reload` khi `signature` đổi |
| `serve_glow.py` | Server live: `/api/snapshot`, `/api/stream` (SSE), `/api/files`; watch dữ liệu → rebuild → phát `reload` |

Đội agent (5 model, chiến lược + ngân sách riêng — tối ưu tốc độ / token / độ sâu):

| id | model | chiến lược | vai trò |
|---|---|---|---|
| `scout` | gpt-4o-mini | `fast` | quét nhanh, top-K 8, ngân sách 45 ms |
| `analyst` | claude-3.5-sonnet | `deep` | 2-hop, top-K 20, đọc sâu |
| `coder` | qwen3-coder | `code` | khớp tiền tố identifier (snake/camel) |
| `auditor` | deepseek-v3 | `hybrid` | 1-hop để đối chiếu bằng chứng |
| `oracle` | bge-m3-embed | `semantic` | khớp chuỗi con, chạy offline (thay embedding) |

```bash
python glow_agents.py --rounds 3        # 5 agent x 7 truy vấn x 3 vòng -> retrieval_log.jsonl
python glow_agents.py --export          # -> glow_signals.json (snapshot cho server)
python retrieval_hook.py --agent cline --query "tim rule risk" \
        --hits "risk.py::stop_loss" --tokens 300 --baseline 4000
python serve_glow.py --watch            # live: SSE + tự rebuild khi dữ liệu đổi
```

- Mở trực tiếp `file://` → dùng snapshot **nhúng sẵn** lúc build (không cần server).
- Mở qua `python serve_glow.py` → thêm SSE: mọi bản đồ đang mở cùng nhận `snapshot`
  (log mới) và `reload` (dữ liệu đổi) → **cập nhật liên tục, 2 bản đồ luôn đồng bộ**.
- Phím tắt: `Q` chạy 1 vòng truy xuất, `Shift+A` tự động; checkbox `fxSignals`
  bật/tắt vòng/vệt sáng theo agent (ngoài 7 hiệu ứng gốc).
- HUD `#sigPanel`: số vòng/truy vấn, % token tiết kiệm, cache hit, p50/p95 theo agent,
  chi phí `$`, sự kiện mới nhất — dữ liệu từ `DATA.signals` nhúng trong payload.

### Kiểm tra

```bash
python build_glow.py                        # -> glow_map.html + glow_map_webgl.html (cung payload)
python -m unittest tests.test_glow_map -v   # template/payload/layout/ve tinh/hieu ung (Canvas2D + WebGL)
python -m unittest tests.test_glow_signals -v   # 75 test: 5 agent, token/cache/tuner, parity Python<->JS,
                                                # dong bo 2 ban do, CLI, SSE
python -m unittest discover -s tests        # toan bo suite (175 tests)
```

### Benchmark tốc độ tìm kiếm / truy xuất (`bench_retrieval.py`)

Đo **3 engine cùng payload** nhúng trong `glow_map.html` với 7 query thật ×
5 chiến lược × 200 lần lặp (batch 10/lượt để khỏi bị ảnh hưởng độ phân giải timer):

```bash
python bench_retrieval.py                      # py + node + chrome headless
python bench_retrieval.py --iters 200 --json bench_results.json
python bench_retrieval.py --no-browser --no-node   # chỉ Python
```

| Nhóm đo | Ý nghĩa |
|---|---|
| startup tooling | đọc 2 file JSON + dựng index (dùng cho `glow_agents`/`serve_glow`/`build_glow`) |
| parse + dựng index | `JSON.parse` payload, `docsFromDs`, `buildIndex` — chi phí lúc mở bản đồ |
| search p50/p95 `[QPS]` | BM25 theo từng chiến lược `fast/code/hybrid/deep/semantic`, kèm hit TB + % token tiết kiệm |
| cache µs/op + sidebar | LRU+TTL (miss/hit) và ô Search của sidebar (dừng ở 500 hit) |
| 1 vòng 5 agent × 7 query | đúng hành động bấm `Q` trong bản đồ: cold/warm, cache hit %, token tiết kiệm |

Kết quả mẫu (máy này, 200 iters — xem `bench_report.txt` / `bench_results.json`):
search p50 **0.01–0.5 ms** (nhanh nhất `fast` ~25k–90k QPS, chậm nhất `code`
~2k–3k QPS do quét tiền tố), 1 vòng `Q` **3.5–8 ms cold** và **0.3–0.9 ms warm**
(cache hit 100%), tiết kiệm **98–99.7%** token so với đọc nguyên file.
Bộ test đi kèm: `python -m unittest tests.test_bench -v` (10 test, có parity
Python↔Node về số hit).


Self-test trong trang: sau frame đầu, `document.title` = `GLOW_OK <n>n/<m>e lit=<pixel sáng>`; nếu JS chết
hoặc canvas trắng thì hiện banner đỏ `#err` + title `GLOW_ERR ...` (test headless đọc DOM để bắt lỗi này).
Bản WebGL dùng hook tương tự: `GLOW_WGL_OK ...` / `GLOW_WGL_ERR ...` (mục *Kiểm tra bản WebGL* ở trên).

### Mở preview ở đâu



- Mở tab markdown: `Ctrl+Shift+V` trên `PREVIEW_README.md` -> click vào link SVG trong file.
- Mở file `.svg` trong Explorer -> click chuột phải -> `Open With` -> `SVG Preview` (hoặc extension SVG Preview).
- Ảnh chụp sẵn của bản đồ sao: `glow_map_preview.png` (cụm sao), `glow_map_shell_preview.png` (vỏ cầu),
  `glow_map_ball_preview.png` (cầu đặc) — click là xem, không cần mở browser.
- Mở HTML thực tế nếu cần zoom/pan live: `graph_memory.html`, `memory_map.html`.
  - Mở trực tiếp (double-click / `file://`) là xem được ngay: dữ liệu đã nhúng sẵn
    (`graph_memory.html` nhúng inline, `memory_map.html` nạp `memory_map_data.js`).
  - Muốn chế độ LIVE (tự nạp lại data 15s) thì chạy qua http: `python memory_map.py --serve`
    (cửa sổ `file://` sẽ hiện nhãn `STATIC (file://)` thay vì `LIVE 15s`).

## Sinh lại dữ liệu bản đồ

```bash
python graph_memory.py    # graph_memory.json + graph_memory.html (code structure)
python memory_map.py      # memory_map_data.json/.js + memory_map.html (code + memories)
python -m unittest tests.test_map_html -v   # kiem tra template/canvas/JS con nguyen ven
```

> Template HTML có 2 lỗi lịch sử đã fix (làm bản đồ trắng): thiếu CSS sizing cho `<canvas>`
> (canvas chỉ 300x150 bị panel che) và thiếu 1 dấu `}` trong `step()` khiến toàn bộ JS không parse được.
> Ngoài ra dữ liệu nhúng nay được escape `</` -> `<\/` để không đóng sớm thẻ `<script>`.


## Lưu ý

- SVG preview chỉ hiển thị một phần edge (tối đa 1200) để không quá nặng; nếu cần toàn bộ, dùng file `.html` có zoom/pan.
- Hubs SVG chỉ hiển thị 80 nút trung tâm + nhãn (để biết nhanh qui tụ).
