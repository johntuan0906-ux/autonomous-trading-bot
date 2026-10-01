# Copilot LM Bridge (local) — cho bot Python dùng Copilot Pro không cần API key

Extension VS Code **nhỏ, cục bộ** mở một HTTP server trên `127.0.0.1` để tiến trình
Python (`agents.py`, provider `vscode_lm`) gọi được **GitHub Copilot** thông qua
**Language Model API chính thức của VS Code** (`vscode.lm.selectChatModels`).

## Vì sao phải là extension

Tài liệu VS Code chỉ mở Language Model API cho **extension** chạy trong extension
host — không có endpoint HTTP công khai, và cũng **không** được phép dùng endpoint
nội bộ của Copilot Chat cho mục đích khác. Cách hợp lệ để "mượn" subscription
Copilot (Pro/Business…) từ một bot Python là: extension gọi `vscode.lm`, Python nói
chuyện với extension qua localhost.

## Cài & chạy

```bash
# 1) copy/scaffold vào thư mục extension của VS Code (hoặc mở folder này bằng VS Code)
#    cách nhanh: symlink/junction thư mục này vào ~/.vscode/extensions/copilot-lm-bridge-0.1.0
# 2) mở VS Code (đã đăng nhập GitHub Copilot), chạy lệnh:
#    "Copilot LM Bridge: Start server"
```

Kiểm tra nhanh:

```bash
curl -s http://127.0.0.1:8765/complete -H "Content-Type: application/json" \
  -d "{\"system\":\"Tra JSON\",\"prompt\":\"Say OK\"}"
```

Trong `.env` của bot:

```bash
AGENTS_ENABLED=true
AGENTS_SHADOW=true
AGENT_PROVIDER=vscode_lm
AGENT_VSCODE_LM_URL=http://127.0.0.1:8765/complete
AGENT_VSCODE_LM_TOKEN=            # trùng copilotLmBridge.token nếu bạn đặt
```

## Giới hạn cần biết (tài liệu VS Code)

- Có **rate limit**; VS Code hiển thị rõ extension nào đang dùng model nào.
- Không dùng Language Model API cho **integration test** (tài liệu khuyến cáo) —
  trong repo này test của `agents.py` chạy bằng provider `stub`, không cần bridge.
- VS Code phải **đang mở** (extension host sống) thì bridge mới hoạt động; nếu tắt
  VS Code, `agents.py` sẽ fail-open về `NO_OPINION` (bot không bị ảnh hưởng).

## An toàn

- Chỉ listen `127.0.0.1`, không mở ra mạng ngoài.
- Token tuỳ chọn (`Authorization: Bearer …`) — nên đặt nếu máy nhiều người dùng.
- Bridge không log nội dung prompt; không gửi API key/số dư (bot chỉ gửi chỉ số thị trường).
