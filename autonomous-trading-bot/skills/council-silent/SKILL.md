---
name: council-silent
description: Dùng khi log ghi "hoi dong im lang", "N/N model ... deu abstain", "critic loi -> NO_OPINION" hoặc số phiếu tụt bất thường. Đo TRƯỚC khi sửa code.
metadata:
  openclaw:
    requires:
      bins: [python]
---

# Hội đồng im lặng — đo trước, sửa sau

Quy ước của repo (lỗi này đã tái diễn 4 lần, mỗi lần đều "im lặng"): **không đọc code trước, đo đã**.

## 1. Ba lệnh đo (chạy đúng thứ tự)

```bash
python tools/probe_cline.py --copilot      # Copilot CLI: từng model + ghi cache logs/model_probe.json
python tools/probe_cline.py                # Cline gateway: model nào còn chạy
python tools/probe_cline.py --qwen openai/<id>   # Qwen CLI (nếu định bật)
```

## 2. Đọc mã trả về (đừng đoán)

| Mã | Nghĩa | Việc cần làm |
|---|---|---|
| `OK` | chạy được | không sửa gì |
| `MODEL_GATED` | tên model **không có trong gói** | đổi cấu hình, KHÔNG sửa code |
| `PAYMENT` (402) | **hết credit** (Cline) | nạp credit; bot tự gỡ chặn sau 12h |
| `AUTH` | chưa đăng nhập | `copilot login` / kiểm token trong `.env` |
| `MODEL_FORMAT` | id model sai định dạng (Qwen CLI cần `modelType/model`) | sửa id, không đổi provider |
| `QUOTA` | hết quota tháng | chờ reset hoặc đổi provider |

## 3. Sau khi sửa

- Cấu hình nằm ở `.env` **cả 2 instance** (TESTNET + `atb-live`), kèm ngày + bằng chứng.
- Nâng gói Copilot: chỉ chạy `python tools/probe_cline.py --copilot --candidates`, hội đồng tự thêm
  model có cache `OK` (không sửa `.env`, không restart).
- Kiểm lại: `python agents.py --council-health --hours 1` — dòng `hoi dong N model: xA/yV`.

## 4. Không được làm

- Không thêm model chỉ để "đông": đo `python tools/council_eval.py --hours 720`, cần `prec` > 0,5 và
  `n_ghep` ≥ 8. Đã loại vì lý do này: `minimax-m3` (0,500), `muse-spark-1.3-contributor` (3/3 không ra
  phiếu), `local/llama3.2-3b-local` (value_r −1,303).
- Không nới `AGENT_COUNCIL_IGNORE` để "cho đủ phiếu".
