# skills/ — runbook dạng Agent Skill

Mỗi thư mục là một skill theo [Agent Skills spec](https://agentskills.io): `SKILL.md` với frontmatter
**chỉ 2 field bắt buộc** (`name`, `description`), phần thân là hướng dẫn cho agent.

Vì sao có thư mục này: 4 lỗi dưới đây đã tái diễn nhiều lần và **mỗi lần đều im lặng**, nên quy ước
"gặp X thì chạy Y" được tách khỏi `OPERATIONS.md` (300 dòng) thành skill mà **bất kỳ** agent nào
(Claude Code, Codex, Copilot CLI, Cursor) cũng nạp được.

| Skill | Dùng khi |
|---|---|
| `council-silent/` | hội đồng im lặng / số phiếu tụt / `NO_OPINION` hàng loạt |
| `close-dust/` | không đóng được vị thế < 5 USDT |
| `reconcile-first/` | sắp kết luận bất cứ điều gì về tiền (LIVE) |
| `drift-report/` | vừa sửa code số liệu/tên tool/mã lỗi; trước khi commit |

Kiểm hợp lệ (đã có test chốt `tests/test_skills_spec.py`): tên thư mục = `name`, có `description`,
và mỗi skill phải nhắc tới ít nhất 1 tool thật trong `tools/`.

Đọc thêm: `RESEARCH_1211.md` mục 3 (vì sao chọn định dạng này), `OPERATIONS.md` (bảng lệnh đầy đủ).
