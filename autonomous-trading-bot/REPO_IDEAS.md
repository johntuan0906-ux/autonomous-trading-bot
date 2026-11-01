

### 25.2 Việc cần làm (đã ghi vào `ops_queue` + sổ harness)

| Việc | Ai | Vì sao |
|---|---|---|
| **B-035** chuẩn hoá TÊN MODEL khi ghi sự kiện AGENT + bảng ánh xạ tên cũ trong `council_evals.py` (`local/llama3.2:3b` 83 vs `local/llama3.2-3b-local` 73; `mimo-v2.6-pro` 77 vs `cline-pass/mimo-v2.6-pro` 105; `qwen/cline-pass/...`; **135 sự kiện `model` RỖNG**) | hội đồng | Mẫu bị chia đôi ⇒ cổng `--ready` có thể kết luận SAI ("chưa đủ mẫu" cho model đã đủ dữ liệu) |
| Chạy `council_eval --ready` định kỳ và **chỉ nâng hội đồng lên veto thật khi exit 0** | hội đồng | Quyết định #4 — nay đo được, không cảm tính |
| Sau khi Copilot quay lại: `agents.py --council-health --hours 48` phải có **≥ 3 model trả phiếu** | hội đồng | B-027/B-033: im lặng mà không ai biết |
| Cảnh báo tự động khi agent bị **TẮT / hết quota** (hiện chỉ ghi journal) | người vận hành quyết | Đã mất 10 ngày im lặng (05–14/10) mà không ai biết |
| `MAX_POSITIONS=1` (LIVE) / trần risk 1.6% (TESTNET) ⇒ bot "hết chỗ" | người vận hành | Nới thì có thêm dữ liệu nhưng tăng rủi ro — **đánh đổi**, không tự đổi |
