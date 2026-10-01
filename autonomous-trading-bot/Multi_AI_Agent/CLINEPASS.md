# Dùng 14 model ClinePass cùng làm việc trong VS Code

Phiên bản 1.1.0 — đối chiếu tài liệu ngày 01/10/2026.

Bạn có thể dùng **một API key của tài khoản Cline có ClinePass**, rồi để Python gửi nhiệm vụ đến nhiều model. Không cần tạo 14 tài khoản. Danh sách trong ảnh là danh sách model để lựa chọn; phần điều phối nhiều model cùng xử lý nhiệm vụ do chương trình Python này thực hiện.

Tài liệu Cline xác nhận ClinePass dùng được từ script bên ngoài, với model ID có tiền tố `cline-pass/`. Đây là đường tích hợp chính thức, không cần lấy token đăng nhập từ extension. Xem [ClinePass — Using ClinePass outside of Cline](https://docs.cline.bot/getting-started/clinepass) và [API Getting Started](https://docs.cline.bot/api/getting-started).

## 1. Chương trình làm gì?

Bạn nhập mục tiêu và chọn file liên quan. Python gửi cùng dữ liệu đó cho các chuyên gia có vai trò khác nhau, cho phép nhiều request đang chờ phản hồi cùng lúc. Khi các nhánh kết thúc, một lượt AI bổ sung đọc báo cáo, so sánh và tạo kết quả chung.

| Thành phần | Vai trò trong bản mẫu |
|---|---|
| VS Code | Mở dự án, nhập nhiệm vụ, chạy terminal và đọc báo cáo |
| ClinePass API | Cung cấp các model thuộc gói của tài khoản |
| Python `asyncio` | Khởi chạy các nhánh, giới hạn số request đồng thời, xử lý lỗi |
| 14 agent | Mỗi agent là một model ID + vai trò + dữ liệu đầu vào |
| Finalizer | Một lượt tổng hợp sau các chuyên gia; mặc định GLM-5.3 |

Đây là kiểu **phân tích song song rồi tổng hợp**, phù hợp sơ đồ phối hợp chuyên gia bạn đã gửi. Các chuyên gia chưa đọc kết quả của nhau trong đợt đầu; finalizer mới đối chiếu chúng. Chương trình chưa tạo hội thoại phản biện nhiều vòng giữa cả 14 model.

Kết quả gồm đề xuất, mã minh họa và báo cáo. Bản này **chưa tự sửa file dự án hoặc chạy code do AI tạo ra**. Phần 8 giải thích cách dùng kết quả với Cline để triển khai thay đổi.

## 2. Điều kiện cần có

- Windows, macOS hoặc Linux; VS Code và extension Python của Microsoft.
- Python **3.12** được khuyến nghị; mã cần tối thiểu 3.11.
- Internet để cài thư viện và gọi API; không cần GPU, Docker hoặc máy chủ riêng.
- Tài khoản Cline có ClinePass đang dùng được, còn quota và có quyền với các model đã chọn.
- API key tạo từ **chính tài khoản Cline đó**. Chỉ lưu ở máy bạn, không gửi key vào chat hoặc commit lên Git.

Python gọi API trực tiếp; không cần Cline sidebar mở trong lúc chạy. Extension và Python không tự chia sẻ lịch sử hội thoại: bạn truyền nhiệm vụ/file cho chương trình qua các tham số bên dưới.

## 3. Cài trên Windows, chạy mô phỏng trước

Giải nén gói `Multi_AI_Agent_VSCode.zip`. Trong VS Code chọn **File → Open Folder** và mở thư mục chứa `cline_multi.py`. Nếu đã có bản trước, nên giải nén bản này sang thư mục mới để không ghi đè `.env` của bạn.

Mở **Terminal → New Terminal**. Các lệnh sau dùng PowerShell, chạy tại thư mục dự án:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-clinepass.txt
.\.venv\Scripts\python.exe cline_multi.py list
```

Nếu máy không có lệnh `py` nhưng `python --version` là 3.11 trở lên, thay dòng đầu bằng `python -m venv .venv`.

Trong VS Code bấm `Ctrl+Shift+P` → **Python: Select Interpreter** → chọn `.venv`. Các lệnh ở đây gọi trực tiếp interpreter, không cần sửa ExecutionPolicy hoặc kích hoạt môi trường.

Chạy thử đủ 14 nhánh, không cần API key:

```powershell
.\.venv\Scripts\python.exe cline_multi.py run --provider mock --group all --concurrency 14 --task-file examples/review_task.txt --context examples/buggy_stats.py
```

Cuối terminal sẽ hiện đường dẫn `outputs/clinepass_.../report.md`. Bạn sẽ thấy nhãn **MÔ PHỎNG**, 14 chuyên gia và 1 lượt tổng hợp. Mock chỉ chứng minh luồng hoạt động; nội dung là câu trả lời giả lập, không phải kết quả AI phân tích file.

Với macOS/Linux, các bước tương đương:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-clinepass.txt
.venv/bin/python cline_multi.py run --provider mock --group all --concurrency 14 --task-file examples/review_task.txt --context examples/buggy_stats.py
```

Các lệnh còn lại chỉ cần thay `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`.

## 4. Kết nối tài khoản ClinePass

1. Mở [app.cline.bot](https://app.cline.bot), đăng nhập tài khoản đang dùng ClinePass trong ảnh.
2. Vào **Settings → API Keys**, tạo API key.
3. Nếu thư mục chưa có `.env`, chạy:

```powershell
Copy-Item .env.clinepass.example .env
```

4. Mở `.env`, đặt key vào dòng `CLINE_API_KEY`. Nếu bạn đã có `.env`, thêm các dòng cần thiết vào file hiện có, không dùng lệnh copy ghi đè.

```dotenv
CLINE_API_KEY=thay_bang_key_cua_ban
CLINE_CONCURRENCY=3
CLINE_REQUEST_TIMEOUT=180
CLINE_RUN_TIMEOUT=900
CLINE_MAX_RETRIES=2
CLINE_MAX_CALLS=45
CLINE_MAX_CONTEXT_CHARS=20000
CLINE_SUMMARY_CHARS_PER_AGENT=6000
```

Không cần `OPENAI_API_KEY` cho `cline_multi.py`. Biến đã đặt trong môi trường terminal được ưu tiên hơn `.env`; nếu sửa key mà vẫn gặp lỗi cũ, kiểm tra biến `CLINE_API_KEY` ở môi trường đó.

Thử một model trước:

```powershell
.\.venv\Scripts\python.exe cline_multi.py check --provider clinepass --model cline-pass/glm-5.3 --concurrency 1
```

Kiểm tra quyền truy cập tất cả model, tối đa 3 request cùng lúc:

```powershell
.\.venv\Scripts\python.exe cline_multi.py check --provider clinepass --group all --concurrency 3
```

`check` gửi một lời nhắc ngắn đến mỗi model, không gọi finalizer. Lệnh này **có gọi API và sử dụng quota**; retry có thể làm tăng số request. Một lần check thành công không bảo đảm model luôn sẵn sàng về sau.

Trong `run.json`, mỗi model có trạng thái `ok` hoặc lỗi cụ thể. `ok` nghĩa là nhận được phản hồi văn bản hoàn chỉnh, không chứng nhận chất lượng câu trả lời.

## 5. Chạy tất cả model cùng làm nhiệm vụ thật

```powershell
.\.venv\Scripts\python.exe cline_multi.py run --provider clinepass --group all --concurrency 14 --task-file examples/review_task.txt --context examples/buggy_stats.py
```

Đây là lệnh yêu cầu **14 nhánh song song ở phía client**. Sau đó có một lượt tổng hợp: bình thường **15 request** nếu không lỗi/retry. Việc máy chủ chấp nhận hoặc xếp hàng bao nhiêu request phụ thuộc tài khoản và tình trạng dịch vụ; chương trình không thể vượt giới hạn của nhà cung cấp.

Nếu bị lỗi 429, vẫn giữ đủ 14 model nhưng chạy theo đợt nhỏ hơn:

```powershell
.\.venv\Scripts\python.exe cline_multi.py run --provider clinepass --group all --concurrency 3 --task-file examples/review_task.txt --context examples/buggy_stats.py
```

| Tham số | Ý nghĩa |
|---|---|
| `--group all` | Chọn cả 14 chuyên gia trong catalog |
| `--group core` | Chọn 4 chuyên gia mẫu, phù hợp thử nhiệm vụ ban đầu |
| `--concurrency 14` | Cho phép tối đa 14 request đang chạy cùng lúc |
| `--concurrency 3` | Tối đa 3 request cùng lúc; các model còn lại đợi đến lượt |
| `--model ID` | Chọn model cụ thể; lặp tham số để chọn nhiều, thay cho group |
| `--provider mock` | Mô phỏng offline |
| `--provider clinepass` | Gọi Cline API bằng key; dùng quota thật |

Không tự thêm `cline-pass/` vào tên tùy ý. Model mới hoặc bị đổi tên cần được cập nhật bằng **ID thật** từ tài liệu/nhà cung cấp. Runner chỉ chấp nhận namespace `cline-pass/` và không tự chuyển sang model tính phí theo lượt khi lỗi.

## 6. Phân công 14 model trong ảnh

Đây là **cách phân vai minh họa**, không phải xếp hạng hay cam kết model nào giỏi nhất ở một lĩnh vực. Sửa `role`, `core` và `finalizer_model` trong `models.clinepass.json` theo bài toán của bạn.

| Model ID | Vai trò mẫu |
|---|---|
| `cline-pass/mimo-v2.6-flash` | Phân rã yêu cầu |
| `cline-pass/mimo-v2.6-pro` | Kiến trúc |
| `cline-pass/glm-5.3` | Triển khai Python |
| `cline-pass/deepseek-v4-pro` | Phản biện logic |
| `cline-pass/qwen3.8-max` | Giao diện hàm và API |
| `cline-pass/deepseek-v4.1-flash` | Ca kiểm thử |
| `cline-pass/muse-spark-1.3-contributor` | Trải nghiệm sử dụng |
| `cline-pass/kimi-k3` | Rà soát yêu cầu và dữ liệu |
| `cline-pass/glm-5.3-flash` | Tình huống biên |
| `cline-pass/minimax-m3` | Hiệu năng |
| `cline-pass/qwen3.7-plus` | Tài liệu sử dụng |
| `cline-pass/qwen3.7-max` | Tích hợp |
| `cline-pass/mimo-v2.5-pro` | An toàn dữ liệu |
| `cline-pass/mimo-v2.5` | Khả năng bảo trì |

Các ID được đối chiếu với [catalog ClinePass](https://docs.cline.bot/getting-started/clinepass); hai model MiMo 2.6 có trong [changelog Cline SDK, mục 0.0.85](https://github.com/cline/cline/blob/main/sdk/CHANGELOG.md). Quyền sử dụng thực tế cần kiểm tra bằng API của tài khoản bạn.

Ví dụ chỉ chọn hai model và một lượt tổng hợp:

```powershell
.\.venv\Scripts\python.exe cline_multi.py run --provider clinepass --model cline-pass/glm-5.3 --model cline-pass/deepseek-v4-pro --concurrency 2 --task "Đề xuất API Python quản lý việc cần làm, lưu SQLite, có tiêu chí kiểm thử."
```

## 7. Áp dụng với file dự án của bạn

Tạo `my_task.txt` ở thư mục runner, ghi rõ mục tiêu, ràng buộc và tiêu chí hoàn thành. Ví dụ:

```text
Đọc file Python được cung cấp và đề xuất sửa lỗi.
Giữ nguyên tên hàm công khai. Xác định hành vi khi đầu vào rỗng.
Đưa ra mã thay thế và các ca kiểm thử với kết quả mong đợi.
Không tuyên bố đã chạy test. Phân biệt lỗi chắc chắn với giả định cần hỏi lại.
```

Chọn những file thực sự liên quan:

```powershell
.\.venv\Scripts\python.exe cline_multi.py run --provider clinepass --group core --concurrency 3 --task-file my_task.txt --context "C:\du_an\src\stats.py" --context "C:\du_an\README.md"
```

Thay đường dẫn ví dụ bằng file thật. Mỗi `--context` là một file, không phải cả thư mục. Dữ liệu của các file bạn chọn được gửi đến các model và lượt tổng hợp. Không truyền bí mật hoặc file không được phép gửi ra dịch vụ AI.

Bộ đọc hỗ trợ UTF-8: `.py`, `.md`, `.txt`, `.json`, `.toml`, `.yaml`, `.yml`, `.csv`; mặc định tối đa tổng 20.000 ký tự context và 6.000 ký tự nhiệm vụ. Nó chặn một số tên file bí mật phổ biến, nhưng **không thay thế việc bạn tự kiểm tra nội dung**. Ảnh/PDF cần được trích xuất thành văn bản phù hợp trước khi dùng runner này.

Sau khi chạy, mở thư mục được in ở terminal:

- `report.md`: bản tổng hợp, đóng góp riêng và lỗi của từng model.
- `run.json`: model, trạng thái, thời gian, số lần thử, usage API nhận được.
- `events.jsonl`: thứ tự bắt đầu, hoàn thành, retry và kết thúc.

Mỗi phiên có thư mục riêng. Kết quả đã nhận được lưu dần; nếu bấm Ctrl+C hoặc timeout, mở lại báo cáo phần đã có. Bản mẫu chưa có chức năng tiếp tục phiên bị ngắt; chạy lại tạo phiên và request mới.

## 8. Dùng kết quả với extension Cline

Mở `report.md`, chọn giải pháp phù hợp rồi yêu cầu Cline áp dụng vào dự án đang mở. Ví dụ lời nhắc bạn có thể sửa lại:

```text
Đọc báo cáo tại [đường dẫn report.md thực tế tôi cung cấp] và các file dự án liên quan.
Xác minh các phát hiện trước khi thay đổi. Thực hiện phương án đã thống nhất,
chỉ sửa những file cần thiết, sau đó chạy các test phù hợp và báo kết quả thực tế.
Nếu báo cáo mâu thuẫn với mã hiện tại, giải thích và ưu tiên bằng chứng từ mã.
```

Đó là quy trình: nhiều model góp ý song song → một bản tổng hợp → Cline thực hiện thay đổi. Tránh cho nhiều phiên độc lập sửa cùng file mà không có cơ chế phối hợp.

Nếu mục tiêu là **nhiều agent trực tiếp sửa code cùng lúc**, Cline có [Agent Teams](https://docs.cline.bot/cli/agent-teams) cho CLI/SDK/Kanban; tài liệu hiện ghi tính năng này chưa áp dụng cho extension VS Code/JetBrains. [Kanban](https://docs.cline.bot/usage/kanban) là hướng khác để tổ chức công việc với Git worktree riêng. Đây là triển khai khác với runner đọc file/trả báo cáo trong gói này.

## 9. Hạn mức, retry và lỗi thường gặp

ClinePass dùng quota theo cửa sổ 5 giờ, tuần và tháng. Xem tình trạng trong [dashboard Cline](https://app.cline.bot). Chạy nhiều model sẽ dùng tổng quota của nhiều lượt; không suy ra rằng 14 model sẽ nhanh hơn 14 lần hoặc luôn tốt hơn 4 model.

Runner giới hạn số request, số retry, thời gian và độ dài đầu vào. Lời nhắc yêu cầu câu trả lời ngắn, **chưa áp dụng giới hạn token đầu ra cứng**: payload chỉ dùng các trường được tài liệu endpoint Cline mô tả. Số từ yêu cầu trong prompt không phải giới hạn chi phí. Không dùng số `cost` của phản hồi để tự suy ra hóa đơn ClinePass.

| Dấu hiệu | Cách xử lý |
|---|---|
| Thiếu `CLINE_API_KEY` | Tạo `.env` ở cùng thư mục với `cline_multi.py`, điền key của tài khoản Cline |
| HTTP 401 | Kiểm tra key, tạo lại nếu đã hết hiệu lực |
| HTTP 402/403 | Kiểm tra gói, quota và quyền sử dụng model trong tài khoản |
| HTTP 404 | Đối chiếu ID hiện hành; sửa catalog hoặc bỏ model khỏi lần chạy |
| HTTP 429 | Giảm concurrency; kiểm tra quota, đợi đủ thời gian được cấp lại |
| HTTP 5xx | Có thể là lỗi dịch vụ; runner retry có giới hạn |
| Timeout | Kiểm tra mạng, thử ít model; tăng timeout nếu nhiệm vụ cần thiết |
| `finish_reason=length` | Phản hồi bị cắt; nội dung được lưu nhưng không tính là hoàn chỉnh |
| Trạng thái `partial` | Có kết quả nhưng ít nhất một nhánh hoặc lượt tổng hợp lỗi |
| SOCKS proxy thiếu thư viện | Cài thêm bằng `python -m pip install "httpx[socks]==0.28.1"` trong đúng venv |

Theo [tài liệu lỗi Cline](https://docs.cline.bot/api/errors), không nên retry mù lỗi quyền truy cập hoặc request sai. Runner chỉ retry các lỗi tạm thời được chọn; `CLINE_MAX_RETRIES=2` nghĩa là tối đa 3 lần thử cho mỗi lượt. `CLINE_MAX_CALLS` tính cả retry, nên đạt ngân sách có thể khiến finalizer chưa được gọi.

Timeout/hủy phía client không bảo đảm máy chủ ngừng xử lý request đã nhận. Retry sau lỗi kết nối cũng có thể tạo thêm lượt xử lý. Usage trong báo cáo có thể thiếu với request thất bại; dashboard là nơi đối chiếu quota.

Finalizer nhận tối đa 6.000 ký tự của mỗi báo cáo theo mặc định. Nếu cần rút gọn, báo cáo ghi rõ việc đó; bản đầy đủ vẫn nằm trong `run.json` và `report.md`. Có thể điều chỉnh `CLINE_SUMMARY_CHARS_PER_AGENT` trong khoảng 500–20.000; tăng giá trị sẽ tăng ngữ cảnh tổng hợp.

## 10. Mã nguồn và kiểm chứng

| File | Chức năng |
|---|---|
| `cline_multi.py` | Giao diện lệnh, đọc cấu hình, chọn model và file |
| `agent_lab/clinepass.py` | Cline API client, semaphore, retry, điều phối và lưu báo cáo |
| `models.clinepass.json` | 14 model, vai trò và model tổng hợp |
| `.env.clinepass.example` | Cấu hình mẫu, không có key thật |
| `tests/test_clinepass.py` | Kiểm thử luồng và hợp đồng HTTP Cline |
| `main.py` và `README.md` | Lab ban đầu gồm Group Chat/Hand-off/Parallel qua mock hoặc OpenAI |

`cline_multi.py` là entry point cho ClinePass. Không dùng `main.py --provider clinepass`: entry point cũ chưa có provider này.

Request thật sử dụng `POST https://api.cline.bot/api/v1/chat/completions`, header `Authorization: Bearer ...`, `model`, `messages` và `stream: false`, theo [Chat Completions](https://docs.cline.bot/api/chat-completions). Runner không thay đổi Settings trong extension.

Đã kiểm tra trên Linux/Python 3.12: **12 test ClinePass** và **17 test lab gốc** thành công. Có test dùng HTTP giả lập để xác nhận 14 request chồng thời gian và finalizer chỉ bắt đầu sau khi các nhánh kết thúc. Có kiểm tra lỗi 404/429, ngân sách retry, lưu kết quả khi timeout/hủy, phản hồi bị cắt và mô phỏng offline.

Không sử dụng API key thật trong kiểm chứng; chưa kiểm tra quyền của tài khoản bạn, chất lượng AI thật, hiệu năng dịch vụ hoặc chạy trực tiếp trên Windows/macOS. Dùng `check --provider clinepass` để kiểm tra tại máy bạn.

Chạy riêng các test ClinePass sau khi cài bộ thư viện tối thiểu:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_clinepass.py -v
```

Để chạy toàn bộ lab và tất cả test, cài `requirements-lock.txt` rồi xem `VALIDATION.md`.
