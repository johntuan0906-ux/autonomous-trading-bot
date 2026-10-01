# Thiết lập Multi-AI Agent bằng Python trong VS Code

Phiên bản dự án: 1.1.0 — ngày 01/10/2026.

**Bạn dùng ClinePass như ảnh đã gửi? Bắt đầu ở [CLINEPASS.md](CLINEPASS.md).** Entry point mới `cline_multi.py` gọi 14 model ClinePass song song rồi tổng hợp, dùng `CLINE_API_KEY`. Cài tối thiểu `requirements-clinepass.txt`. Có mock không cần key. Phần dưới hướng dẫn lab gốc qua `main.py`, vẫn dùng mock/OpenAI và không cần thiết cho đường ClinePass.

Đây là dự án Python hoàn chỉnh ở mức ứng dụng dòng lệnh, có ba kiểu phối hợp trong hình bạn gửi: **Group Chat, Hand-off và phân tích song song rồi tổng hợp**. Có chế độ mô phỏng không gọi mạng và adapter gọi OpenAI Responses API thật. Bạn tải dự án, cài thư viện, thử mô phỏng, cấu hình API rồi áp dụng với nhiệm vụ và các file của mình.

**Ranh giới đã làm:** phân vai, gọi AI, điều phối, bàn giao, đọc file do bạn chỉ định, kiểm tra cấu trúc kết quả, giới hạn lượt, xử lý lỗi, lưu báo cáo và lịch sử. Các agent có thể đề xuất mã trong báo cáo. Bản này chưa tự ghi đè dự án khác, chạy mã do AI tạo, tìm kiếm web hay tự triển khai ứng dụng. Những khả năng đó cần các công cụ thực thi riêng; phần 13 giải thích cách mở rộng.

**Kiểm chứng:** 17 bài kiểm thử lab gốc và 12 bài kiểm thử ClinePass đã chạy thành công trên Python 3.12/Linux, cùng CLI mô phỏng. Test HTTP dùng `httpx.MockTransport`, không kết nối máy chủ AI. Chưa thực hiện kiểm thử AI thật hoặc chạy trực tiếp trên Windows trong phiên tạo dự án. Xem `VALIDATION.md` và `CLINEPASS.md` để kiểm tra API ở máy bạn.

## 1. Hiểu đúng ba sơ đồ

Multi-agent là cách tổ chức nhiều tác nhân phần mềm cùng xử lý một mục tiêu. Bạn không cần huấn luyện một mạng neural mới để triển khai những sơ đồ này. Một agent trong bản mẫu gồm tên/vai trò, chỉ dẫn, ngữ cảnh, mô hình và một giao thức trả kết quả.

Một mô hình có thể đóng nhiều vai: planner, builder và reviewer có thể cùng gọi `gpt-4.1-mini`, nhưng mỗi lần gọi dùng chỉ dẫn khác nhau. Dùng nhiều agent không có nghĩa là phải mua nhiều tài khoản hay chạy nhiều GPU.

| Hình | Cách phối hợp | Trong dự án | Khi dùng |
|---|---|---|---|
| Multi-Agent Group Chat | Manager đọc hội thoại và chọn agent phát biểu tiếp | `--mode group` | Nhiệm vụ cần thảo luận, phản biện, sửa lại nhiều lượt |
| Multi-Agent Hand-off | Agent đang xử lý chọn agent nhận việc tiếp theo | `--mode handoff` | Quy trình có các bước rõ, có thể quay lại sửa |
| Multi-Agent Collaborative Filtering | Các chuyên gia cùng xem mục tiêu, đánh giá độc lập; bước tổng hợp chọn ý kiến có căn cứ | `--mode parallel` | Cần đối chiếu nhiều góc nhìn và rút ngắn thời gian chờ các nhánh độc lập |

Tên “Collaborative Filtering” ở đây được triển khai theo ý phối hợp chuyên gia của sơ đồ. Bản mẫu không phải thuật toán gợi ý sản phẩm bằng ma trận người dùng–sản phẩm. Việc thêm finalizer là lựa chọn triển khai để có một đầu ra chung sau ba chuyên gia.

**Group Chat:** manager chọn ai nói tiếp; mỗi chuyên gia được nhận lịch sử các đóng góp trước đó. “Broadcast” được thực hiện bằng cách đưa lịch sử chung vào đầu vào của lượt tiếp theo, không phải phát qua mạng đến nhiều máy. Manager có thể yêu cầu builder sửa lại sau reviewer. Mã chỉ cho kết thúc khi đủ cả ba vai trò và đóng góp cuối là reviewer.

**Hand-off:** planner chuyển sang builder; builder chuyển reviewer hoặc quay lại planner; reviewer có thể yêu cầu sửa hoặc kết thúc. Quyền điều khiển được chuyển bằng trường JSON `next_agent`; Python xác thực cạnh chuyển rồi gọi agent đó. Đây là hand-off do ứng dụng thực hiện, không phải hàm handoff của một framework cụ thể.

**Parallel:** cùng một bản chụp mục tiêu và file đầu vào được gửi cho ba chuyên gia. Chúng không đọc kết quả nhau trong đợt chạy này. `asyncio.gather` chờ kết quả; finalizer so sánh đóng góp, nêu bất đồng và tổng hợp. Thứ tự log hoàn thành có thể thay đổi. Nếu một chuyên gia lỗi, báo cáo được đánh dấu `partial`.

## 2. Điều kiện cần chuẩn bị

| Thành phần | Cần gì | Ghi chú |
|---|---|---|
| Máy tính | Windows, macOS hoặc Linux chạy được Python và VS Code | Hướng dẫn chính bên dưới dùng Windows PowerShell |
| Python | Chọn Python 3.12; mã cần từ 3.11 vì dùng `asyncio.timeout` | Môi trường đã kiểm thử: 3.12.14 |
| VS Code | Cài VS Code và extension Python của Microsoft | Dự án có danh sách extension gợi ý |
| RAM | Gợi ý thực tế 8 GB để dùng VS Code thoải mái | Không phải mức tối thiểu bắt buộc của mô hình |
| GPU | Không cần khi dùng API | Mô hình chạy phía nhà cung cấp |
| Internet | Cần khi cài thư viện và gọi AI thật | Sau khi đã cài thư viện, mock và test chạy không cần API |
| Tài khoản AI | API key, quyền dùng model, quota/số dư API phù hợp | Không cần key khi chạy mock |
| Đầu vào | Mục tiêu cụ thể, tiêu chí hoàn thành, file liên quan nếu có | Chất lượng ngữ cảnh ảnh hưởng trực tiếp kết quả |
| Ngân sách | Theo dõi lượt gọi và usage API | Nhiều agent thường tăng tổng token |

Bản mẫu dùng **API key thông thường và thanh toán/quota API**. Nó không dùng phiên đăng nhập ChatGPT hay tự lấy hạn mức từ gói Plus. Cơ chế Sign in with ChatGPT cho ứng dụng hỗ trợ là một tích hợp khác, chưa có trong dự án này.

Không cần Docker, Redis, cơ sở dữ liệu vector, VPS hay AutoGen để chạy ba chế độ này trên một máy. Chọn Python điều phối trực tiếp giúp bạn nhìn rõ luồng, sau đó có thể chuyển sang framework nếu cần tính năng lớn hơn.

## 3. Cài đặt trên Windows từ đầu

### Bước 1 — Cài Python và VS Code

1. Cài Python 3.12 từ [python.org](https://www.python.org/downloads/). Nếu trình cài có lựa chọn, bật thêm Python vào PATH.
2. Cài [Visual Studio Code](https://code.visualstudio.com/).
3. Trong VS Code, mở Extensions bằng `Ctrl+Shift+X`, cài **Python** của Microsoft. Pylance và Python Debugger giúp đọc mã và debug; dự án có đề xuất cả ba extension.
4. Mở terminal mới, kiểm tra:

```powershell
py -3.12 --version
```

Nếu `py` không được nhận diện, khởi động lại VS Code sau khi cài. Nếu bạn có Python 3.11 trở lên dưới lệnh `python`, có thể dùng `python -m venv .venv` ở bước sau.

### Bước 2 — Giải nén và mở đúng thư mục

Giải nén `Multi_AI_Agent_VSCode.zip`, ví dụ vào `C:\AI\Multi_AI_Agent_VSCode`.

Trong VS Code: **File → Open Folder** → chọn thư mục có `main.py`, `requirements.txt`, `.env.example` và thư mục `agent_lab`.

Mở **Terminal → New Terminal**. Các lệnh bên dưới phải được chạy trong thư mục có `main.py`:

```powershell
Get-Location
Get-ChildItem
```

Không chạy trực tiếp bên trong cửa sổ xem ZIP. Nếu giải nén tạo hai thư mục trùng tên lồng nhau, mở thư mục bên trong có `main.py`.

### Bước 3 — Tạo môi trường riêng và cài thư viện

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Các lệnh dùng trực tiếp Python trong `.venv`, nên không cần kích hoạt `Activate.ps1` hoặc thay Execution Policy của PowerShell.

Ba thư viện chính đã ghim phiên bản: `openai==2.54.0`, `pydantic==2.13.5`, `python-dotenv==1.2.4`. `requirements-lock.txt` ghi toàn bộ dependency của môi trường đã kiểm thử. Để tái lập bộ phiên bản đó, thay lệnh cài cuối bằng:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

### Bước 4 — Chọn Python đúng trong VS Code

Nhấn `Ctrl+Shift+P` → **Python: Select Interpreter** → chọn `.venv\Scripts\python.exe`.

Nếu chưa thấy, chọn **Enter interpreter path** và trỏ đến file đó trong dự án. Bước này giúp nút Run, debugger và test của VS Code dùng đúng thư viện.

### Bước 5 — Kiểm tra cài đặt và chạy mô phỏng

```powershell
.\.venv\Scripts\python.exe main.py doctor
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py run --provider mock --mode handoff --task-file examples/task.txt
```

Bạn sẽ thấy log `planner`, `builder`, `reviewer`, `finalizer`, sau đó `Trang thai: completed`. Thư mục kết quả được in ra. Với handoff mock bình thường, có 4 lượt gọi mô phỏng.

`doctor` mặc định chỉ kiểm tra cài đặt và cấu hình. `completed` ở mock chỉ chứng minh chương trình điều phối đã chạy hết luồng; nội dung trả lời là mẫu cố định, chưa phải kết quả AI.

## 4. Cấu hình để dùng AI thật

### Bước 6 — Chuẩn bị API key

Đăng nhập [OpenAI API Platform](https://platform.openai.com/), chọn project phù hợp, kiểm tra quota/thanh toán API rồi tạo API key ở phần quản lý API keys. Đối chiếu [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart) nếu giao diện thay đổi.

Chỉ lưu key vào môi trường máy bạn hoặc `.env`. Không cần gửi key trong chat, ảnh màn hình hay đưa vào mã nguồn.

### Bước 7 — Tạo `.env` cạnh `main.py`

Chạy lệnh sao chép **lần đầu**, khi chưa có `.env` chứa cấu hình của bạn:

```powershell
Copy-Item .env.example .env
```

Mở `.env` bằng VS Code rồi sửa:

```dotenv
PROVIDER=openai
OPENAI_API_KEY=dien_key_that_tren_may_cua_ban
OPENAI_MODEL=gpt-4.1-mini
MAX_TURNS=6
MAX_CALLS=16
MAX_OUTPUT_TOKENS=2200
MAX_CONCURRENCY=3
```

Giữ các dòng cấu hình còn lại như file mẫu. Không đặt tên thành `.env.txt`. Key không được có khoảng trắng ở giữa; không dùng key của Binance hoặc Telegram.

`gpt-4.1-mini` là lựa chọn minh họa đã được đối chiếu có Responses và Structured Outputs. Đây không phải tuyên bố là model mới nhất hay tốt nhất cho mọi nhiệm vụ. Bạn có thể đổi sang model mà tài khoản được quyền dùng và hỗ trợ cùng hai tính năng. Một số model cần cấu hình/token đầu ra khác.

Thứ tự ưu tiên provider: `--provider` trên dòng lệnh → biến môi trường terminal → `.env` → mặc định `mock`. Những biến khác đã export trong terminal cũng ưu tiên hơn `.env`. Chương trình chỉ đọc `.env` cạnh `main.py`.

### Bước 8 — Xác minh kết nối

```powershell
.\.venv\Scripts\python.exe main.py doctor --live
```

Lệnh gửi một request nhỏ, có thể phát sinh phí API. Thành công nghĩa là **key, model finalizer, kết nối và schema** đã hoạt động cho request đó. Nó không kiểm tra mọi model khác bạn tự cấu hình, không đảm bảo mọi nhiệm vụ AI sẽ đúng.

Sau đó chạy nhóm agent thật:

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode handoff --task-file examples/task.txt
```

## 5. Chạy đủ ba kiểu phối hợp

### Hand-off — nên bắt đầu ở đây

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode handoff --task-file examples/task.txt
```

Luồng thường gặp: planner lập yêu cầu, builder tạo giải pháp, reviewer kiểm tra, finalizer tổng hợp. Reviewer có thể bàn giao lại builder khi cần sửa. Không có lượt manager riêng trong chế độ này.

### Group Chat — manager chọn người xử lý tiếp

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode group --task-file examples/task.txt
```

Mỗi vòng thường có một lần gọi manager và một lần gọi chuyên gia. Khi manager chọn `finish` hợp lệ, finalizer tạo báo cáo. Vì manager cũng dùng AI, group thường tốn nhiều lượt hơn handoff cho nhiệm vụ đơn giản.

### Parallel — ba chuyên gia chạy đồng thời

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode parallel --task-file examples/task.txt
```

Ba chuyên gia nhận cùng nhiệm vụ rồi finalizer tổng hợp. Bình thường 4 lượt gọi nếu không retry. Thời gian có thể giảm khi các nhánh độc lập; tổng token không tự giảm và còn có lượt tổng hợp.

Muốn thử ba luồng miễn phí API, thay `--provider openai` thành `--provider mock` trong các lệnh.

## 6. Đưa nhiệm vụ và file của bạn vào

Viết yêu cầu trực tiếp:

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode handoff --task "Thiết kế chương trình Python đọc CSV, kiểm tra dữ liệu và xuất báo cáo lỗi. Cho mã và các ca kiểm thử."
```

Với mô tả dài, tạo `my_task.txt` bằng VS Code, lưu UTF-8 rồi dùng `--task-file my_task.txt`. Tối đa 6.000 ký tự cho nhiệm vụ; ngữ cảnh file có hạn mức riêng.

Ví dụ sửa lỗi trên file mẫu:

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode handoff --task-file examples/review_task.txt --context examples/buggy_stats.py
```

Ví dụ đối chiếu hai file của một dự án khác, thay đường dẫn cho đúng máy bạn:

```powershell
.\.venv\Scripts\python.exe main.py run --provider openai --mode group --task-file my_task.txt --context "C:\du_an\main.py" --context "C:\du_an\utils.py"
```

**Khi dùng provider openai, nội dung nhiệm vụ và những file `--context` sẽ được gửi đến API.** Chương trình chỉ đọc file bạn chỉ định; không tự quét toàn ổ đĩa. Nó chặn tên `.env*`, tên chứa `secret`/`credential` và kiểu file không hỗ trợ, nhưng không thể phát hiện mọi bí mật được nhúng trong file `.py`. Hãy loại key/password khỏi bản ngữ cảnh trước khi gửi.

Các đuôi hỗ trợ: `.py`, `.md`, `.txt`, `.json`, `.toml`, `.yaml`, `.yml`, `.csv`. CSV ở đây được đọc dưới dạng văn bản, không tự phân tích bằng pandas. Không đọc PDF/Word/ảnh ở bản mẫu này. Mỗi file tối đa 1 MB, tổng nội dung mặc định tối đa 20.000 ký tự; nếu vượt, chương trình báo lỗi thay vì âm thầm cắt mất phần còn lại.

Muốn AI đối chiếu quan hệ giữa các file, cần truyền đủ các file liên quan hoặc mô tả interface/import. AI không nhìn thấy tự động toàn bộ project đang mở trong VS Code.

## 7. Xem kết quả và kiểm tra có chạy đúng không

Mỗi lần chạy có một thư mục riêng trong `outputs`, ví dụ `outputs/20261001T060000Z_ab12cd34`:

| File | Nội dung | Cách xem |
|---|---|---|
| `report.md` | Kết quả cuối, đóng góp, giới hạn, lỗi và thống kê | Mở bằng VS Code; nhấn `Ctrl+Shift+V` để preview |
| `transcript.json` | Trạng thái, các quyết định, nội dung từng agent, usage, metadata file | Dùng để kiểm tra luồng hoặc nạp vào ứng dụng khác |
| `events.jsonl` | Mỗi dòng là một sự kiện có thời gian UTC | Theo dõi gọi API, retry, bàn giao, dừng |

Lịch sử đóng góp được ghi sau từng kết quả. Ctrl+C cố gắng lưu trạng thái `interrupted`. Nếu mất điện hoặc bị kill ngay lập tức, các checkpoint đã ghi vẫn còn, nhưng trạng thái cuối có thể chưa cập nhật. Bản này chưa có resume tự động; chạy lại tạo một phiên mới.

| Trạng thái | Ý nghĩa | Việc tiếp theo |
|---|---|---|
| `completed` | Luồng đã có bản tổng hợp cuối | Đọc kết quả, chạy test của sản phẩm trước khi dùng |
| `partial` | Parallel thiếu ít nhất một báo cáo | Xem agent nào lỗi và giới hạn trong báo cáo |
| `limit_reached` | Chạm giới hạn lượt, số lần gọi hoặc tổng thời gian | Xem transcript; thu hẹp yêu cầu hoặc điều chỉnh cấu hình |
| `failed` | Có lỗi khiến luồng không hoàn thành | Xem `errors`, log và bảng xử lý lỗi |
| `interrupted` | Có yêu cầu hủy | Kiểm tra các đóng góp đã lưu |

Mã thoát `0` là luồng completed; `2` là lỗi hoặc kết quả chưa đủ; `130` là Ctrl+C. `completed` không đồng nghĩa “AI luôn đúng” hoặc “code đã được chạy thành công”.

## 8. Bên trong dự án: sửa file nào?

| File | Trách nhiệm | Khi cần sửa |
|---|---|---|
| `main.py` | CLI, doctor, chọn provider, tải đầu vào | Thêm lệnh/tuỳ chọn |
| `agent_lab/config.py` | Đọc `.env`, kiểm tra cấu hình | Thêm tham số |
| `agent_lab/prompts.py` | Vai trò và chỉ dẫn cho mỗi agent | Đổi chuyên môn/nhiệm vụ |
| `agent_lab/schemas.py` | JSON có cấu trúc của quyết định và kết quả | Đổi giao thức trao đổi |
| `agent_lab/providers.py` | Mock và OpenAI Responses API | Thêm nhà cung cấp/model local |
| `agent_lab/engine.py` | Ba kiểu điều phối, retry, concurrency và giới hạn | Thêm agent hoặc kiểu phối hợp |
| `agent_lab/context.py` | Đọc file được chọn, giới hạn kích thước | Đổi nguồn tri thức |
| `agent_lab/storage.py` | Log, checkpoint, Markdown report | Đổi lưu trữ sang database |
| `tests/` | Test điều phối và hợp đồng HTTP/SDK | Kiểm tra sau khi sửa mã |
| `.vscode/` | Extension, interpreter và debug configuration | Chạy F5 trong VS Code |

Không đặt file của bạn tên `openai.py`, `asyncio.py`, `json.py` hoặc `pydantic.py` ở gốc dự án vì có thể che tên thư viện.

Ví dụ giao thức bàn giao mà model phải trả:

```json
{
  "content": "Đã đề xuất cấu trúc và mã cần thay đổi; chưa chạy test.",
  "next_agent": "reviewer",
  "handoff_note": "Kiểm tra đầu vào rỗng, dữ liệu sai kiểu và tài nguyên chưa đóng."
}
```

OpenAI được yêu cầu trả đúng JSON Schema; Pydantic kiểm tra lại cấu trúc và nội dung rỗng. Python kiểm tra thêm `next_agent` có được phép trong trạng thái hiện tại không. Schema đúng chỉ đảm bảo hình dạng dữ liệu, không đảm bảo nhận định của AI đúng.

## 9. Tùy biến vai trò và mô hình

Ví dụ muốn chuyên về phân tích dữ liệu: giữ tên nội bộ planner/builder/reviewer để chưa phải sửa router, rồi đổi chỉ dẫn trong `prompts.py` thành người phân tích yêu cầu dữ liệu, người đề xuất xử lý và người kiểm tra chất lượng.

Muốn dùng model khác cho reviewer:

```dotenv
OPENAI_MODEL=gpt-4.1-mini
MODEL_REVIEWER=ten_model_tai_khoan_cua_ban_duoc_dung
```

Dòng trên là chỗ điền cấu hình, không phải tên model thật. Các trường `MODEL_MANAGER`, `MODEL_PLANNER`, `MODEL_BUILDER`, `MODEL_REVIEWER`, `MODEL_FINALIZER` để trống sẽ dùng `OPENAI_MODEL`.

Muốn thêm agent thứ tư, phải sửa đồng bộ: danh sách agent, `Literal` trong schema, `ROLES`, cạnh `HANDOFFS`, quy tắc kết thúc Group Chat, danh sách model theo vai trò và test. Chỉ thêm tên vào prompt sẽ không tự tạo agent có khả năng thực thi.

Các nhà cung cấp khác hoặc model local cần adapter mới cài giao diện `generate(ModelRequest) -> ModelResult` và `close()`, cùng schema/error mapping tương ứng. Bản này không quảng cáo tương thích chỉ bằng đổi `base_url`. Chạy local còn phụ thuộc dung lượng model, lượng tử hóa, RAM/VRAM và backend inference.

## 10. Kiểm soát số lần gọi, token và thời gian

| Cấu hình | Mặc định | Tác dụng |
|---|---:|---|
| `MAX_TURNS` | 6 | Số đóng góp chuyên gia tối đa trong group/handoff; không tính finalizer |
| `MAX_CALLS` | 16 | Tổng lần thử gọi model, gồm manager, finalizer và retry; bộ đếm dùng chung cho các nhánh |
| `MAX_OUTPUT_TOKENS` | 2200 | Trần output cho mỗi chuyên gia/finalizer; manager tối đa 500 |
| `MAX_CONCURRENCY` | 3 | Số request đang chờ tối đa |
| `MAX_RETRIES` | 2 | Số lần thử lại tối đa sau lần đầu cho lỗi tạm thời |
| `REQUEST_TIMEOUT_SECONDS` | 90 | Giới hạn thời gian của mỗi lần thử |
| `RUN_TIMEOUT_SECONDS` | 600 | Giới hạn toàn phiên |
| `MAX_CONTEXT_CHARS` | 20000 | Giới hạn ký tự từ các file đầu vào |

Với Group Chat, sau lượt chuyên gia cuối trong hạn mức, nếu chưa có quyết định `finish` của manager thì trạng thái là `limit_reached`. Đó là cách dừng theo lượt của bản mẫu, không phải lỗi kết nối. Parallel luôn có ba nhánh cố định, nên `MAX_TURNS` không thay đổi số nhánh.

Trong mock mặc định: handoff 4 calls, group 8 calls, parallel 4 calls. Với AI thật, handoff/group có thể nhiều hơn khi agent yêu cầu sửa; retry cũng tăng lượt. Nếu hết MAX_CALLS trước finalizer, chương trình giữ đóng góp đã có và không gọi thêm chỉ để tổng hợp.

`MAX_CALLS` là trần lượt gọi của **một phiên**, không phải trần tiền theo tháng. Số tiền phụ thuộc token, model, giá hiện hành và các tác vụ khác trong tài khoản. Một request mất kết nối có thể đã được xử lý phía máy chủ; retry có thể thêm phí. Usage trong log chỉ cộng số token API thực sự trả về được cho chương trình, không phải hóa đơn đầy đủ.

Cách giảm chi phí thực tế: dùng handoff khi đã biết quy trình; gửi đoạn code liên quan; yêu cầu đầu ra ngắn; giảm số vòng; dùng model phù hợp từng vai trò; với project lớn, bổ sung chọn file/tóm tắt/cache có kiểm soát. Ba agent đọc lại cả kho code thường tốn token hơn một agent.

`store=False` trong request tắt lưu Response theo tính năng đó; không đồng nghĩa không có bất kỳ lưu giữ dữ liệu nào của dịch vụ. Báo cáo/log trên máy bạn vẫn chứa nhiệm vụ và nội dung AI trả lời. Không đưa các log nhạy cảm lên kho công khai.

## 11. Xử lý các lỗi thường gặp

| Dấu hiệu | Nguyên nhân cần kiểm tra | Cách xử lý |
|---|---|---|
| `py`/`python` không được nhận diện | Chưa cài hoặc PATH chưa cập nhật | Cài Python, mở lại terminal, kiểm tra `py -3.12 --version` |
| Không thấy `main.py` | Terminal ở sai thư mục hoặc đang xem ZIP | Giải nén; Open Folder đúng thư mục; `Get-ChildItem` |
| `ModuleNotFoundError` | Dùng Python khác với nơi đã cài | Dùng `.\.venv\Scripts\python.exe`; cài lại requirements bằng chính interpreter đó |
| PowerShell chặn `Activate.ps1` | Chính sách thực thi script | Dùng lệnh Python trực tiếp trong hướng dẫn, không cần activation |
| `OPENAI_API_KEY` chưa cấu hình | `.env` sai tên/vị trí hoặc trống | Đặt `.env` cạnh `main.py`; không để `.env.txt`; chạy doctor |
| Sửa `.env` nhưng giá trị chưa đổi | Terminal có biến môi trường ghi đè | Kiểm tra tên biến đã export; mở terminal sạch hoặc xóa đúng biến cũ |
| HTTP 401 | Key sai, thu hồi hoặc sai project | Tạo/cập nhật đúng key trên máy; không sửa code router |
| HTTP 403 | Thiếu quyền hoặc giới hạn tài khoản | Kiểm tra quyền project, quyền model và truy cập API |
| HTTP 404 | Model không tồn tại/không có quyền | Kiểm tra `OPENAI_MODEL` và các `MODEL_*` |
| HTTP 429 quota | Thiếu quota/số dư hoặc vượt hạn mức | Kiểm tra API Billing/Usage; lỗi này không được retry liên tục |
| HTTP 429 rate limit | Gửi quá nhanh | Giảm `MAX_CONCURRENCY`; app retry có backoff |
| HTTP 400/schema | Model/tham số không tương thích | Dùng model có Responses + Structured Outputs; thử cấu hình mẫu |
| Phản hồi chưa hoàn tất | Output quá dài hoặc API chưa hoàn tất | Rút gọn nhiệm vụ; tăng output tokens trong giới hạn model nếu cần |
| Timeout/mất mạng | Internet, VPN, proxy, TLS hoặc model chậm | Kiểm tra kết nối; tăng timeout hợp lý; không tắt kiểm tra TLS |
| `limit_reached` | Chạm hạn mức chủ động | Đọc warnings và transcript; sửa phạm vi nhiệm vụ hoặc hạn mức |
| Context quá lớn | Nhiều file/đoạn văn dài | Chọn file/đoạn liên quan; không tăng giới hạn vô hạn |
| AI trả code nhưng file gốc không đổi | Bản này tạo đề xuất trong báo cáo | Đọc đề xuất, áp dụng vào nhánh riêng và chạy test |

Nếu vừa sửa `.env` mà terminal giữ key cũ, trên PowerShell có thể xóa riêng biến đó trong phiên terminal hiện tại bằng:

```powershell
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

Sau đó chạy lại `doctor`. Lệnh này không xóa `.env` hay key trên máy chủ.

## 12. Debug, kiểm thử và đánh giá chất lượng

Nhấn `F5`, chọn **1. Mo phong Hand-off** để quan sát không gọi AI. Cấu hình thứ hai chạy OpenAI thật và có thể tốn phí API. Có thể đặt breakpoint ở `Engine.handoff`, `Engine.group`, `Engine.parallel` hoặc `OpenAIProvider.generate`.

Chạy lại test sau khi sửa code:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

17 test kiểm tra: ba luồng kết thúc/lưu kết quả; broadcast; manager kết thúc sớm; handoff quay lại sửa; bàn giao sai; concurrency và đầu vào độc lập; nhánh lỗi; giới hạn call/turn; timeout toàn phiên; hủy và checkpoint; đọc context; cấu trúc request SDK; phản hồi thiếu/JSON lỗi; refusal; ánh xạ lỗi API; retry và token usage.

Test dùng mock xác nhận phần điều phối, không đo trí thông minh. Để đánh giá áp dụng thật, tạo một bộ nhiệm vụ nhỏ có đáp án/tiêu chí rõ và chạy cả ba chế độ trên cùng đầu vào. Ghi: đạt yêu cầu hay không, lỗi còn lại, số lượt, input/output tokens, tổng thời gian. So sánh cả với một lượt AI đơn lẻ trước khi quyết định dùng nhiều agent.

Với ví dụ `buggy_stats.py`, tiêu chí kiểm tra cụ thể là: average([]) báo ValueError; average([2,4]) bằng 3; last_three([1,2,3,4]) bằng [2,3,4]; danh sách ngắn giữ nguyên; không sửa đối tượng đầu vào. Chỉ sau khi áp dụng mã và chạy test thực sự mới kết luận mã sửa chạy được.

## 13. Mở rộng sang agent thực thi công việc

Để hệ thống tự sửa file/chạy kiểm thử, cần bổ sung **tools**, không chỉ viết “hãy sửa và test” vào prompt.

| Năng lực muốn thêm | Thành phần triển khai | Bằng chứng thành công |
|---|---|---|
| Đọc dự án lớn | Liệt kê file trong root cho phép, chọn đoạn liên quan, đọc có giới hạn | Log file/đoạn đã đọc; không tuyên bố thấy file chưa nạp |
| Tạo/sửa mã | Tool tạo patch và áp patch trên nhánh/worktree riêng | Diff thực tế giữa trước và sau |
| Chạy test | Executor tách biệt, thư mục cố định, timeout và lệnh cho phép | Exit code, stdout/stderr, tên test và thời điểm chạy |
| Nghiên cứu web | Công cụ tìm kiếm/fetch, kèm URL và thời điểm | Nguồn truy xuất thật hỗ trợ từng kết luận |
| Nhớ qua nhiều phiên | Database phiên, phiên bản schema và cơ chế resume | Tải lại phiên cũ và tiếp tục đúng bước |
| Giao diện | UI gọi engine; trạng thái tác vụ và hủy | Hiển thị kết quả/log từ run thật |
| Chạy nhiều người | API backend, xác thực, hàng đợi, giới hạn theo người | Các tác vụ không đọc/ghi lẫn dữ liệu |

Cho agent dùng tools theo chu trình: model yêu cầu một tool → ứng dụng kiểm tra tên/tham số/quyền → tool thực thi → trả kết quả thực cho model → tiếp tục. Có thể sử dụng function calling hoặc một framework agent cho phần này. Không dùng `eval()` để thực thi văn bản AI và không đưa chuỗi lệnh AI chưa kiểm tra vào shell.

Với công việc sửa mã: giao một agent sở hữu một phạm vi file hoặc một worktree, hợp nhất thay đổi bằng Git, rồi chạy test độc lập. Tránh nhiều agent ghi đồng thời cùng file. Có thể tổ chức theo hybrid: manager phân việc, các nhánh độc lập chạy song song, reviewer duyệt diff và kết quả test. Chỉ thêm concurrency khi công việc thực sự độc lập.

Nếu muốn đưa vào vận hành dài hạn, cần bổ sung theo quy mô thực tế: bộ eval với tiêu chí rõ; lưu trữ/resume bền vững; thống kê chất lượng và chi phí; quản lý key; xử lý công việc trùng khi retry; kiểm thử quyền của tools; kế hoạch xử lý khi dịch vụ lỗi. Đây là những phần phát triển tiếp, chưa được tính là tính năng đã có trong ZIP.

## 14. macOS/Linux và cách dừng

Trong thư mục dự án:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
./.venv/bin/python main.py doctor
./.venv/bin/python main.py run --provider mock --mode handoff --task-file examples/task.txt
```

Chỉ sao chép `.env.example` lần đầu. Điền key bằng trình soạn thảo rồi chạy `doctor --live` và `--provider openai` như trên, thay đường dẫn Python bằng `./.venv/bin/python`.

Chương trình xử lý một nhiệm vụ rồi thoát. Nhấn **Ctrl+C** để dừng sớm. Nó chưa phải dịch vụ chạy 24/7. Đóng terminal/VS Code, tắt máy hoặc cho máy ngủ có thể ngắt tác vụ. Nếu cần hoạt động liên tục, phải chạy bằng tiến trình/dịch vụ có giám sát trên một máy luôn hoạt động.

## 15. Nguồn tài liệu đối chiếu

Tài liệu tham chiếu được đọc ngày 01/10/2026. Kiến trúc và giới hạn cụ thể trong hướng dẫn này mô tả mã nguồn đính kèm; không phải lời đảm bảo của nhà cung cấp.

- [Microsoft — Multi-agent design patterns](https://github.com/microsoft/ai-agents-for-beginners/blob/main/08-multi-agent/README.md)
- [VS Code — Getting Started with Python](https://code.visualstudio.com/docs/python/python-tutorial)
- [OpenAI — Developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [OpenAI — Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI — GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [OpenAI — API pricing](https://developers.openai.com/api/docs/pricing)
- [ChatGPT — Pricing và phân biệt usage API](https://learn.chatgpt.com/docs/pricing)
- [OpenAI — Production best practices](https://developers.openai.com/api/docs/guides/production-best-practices)
