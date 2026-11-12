# KE HOACH TU HOC CUA HOI DONG (tu sinh tu so lieu, khong phai y kien)

| # | Thieu hut | Do (hien tai -> can) | Tu lam |
|---|---|---|---|
| 1 | calibration | brier: 0.3398 -> <= 0.25 | co |
| 2 | match_exact | ty le ghep CHINH XAC (decision_id): 0.099 -> 0.8 | co |
| 3 | thin_models | so model co n_ghep < min_n: 11 -> 0 | co |
| 4 | value_negative | model co value_r <= 0: 1 -> 0 | KHONG (can nguoi) |

## calibration (high)
- Do: **brier = 0.3398** (can: <= 0.25)
- Can thu thap / lam:
  - [ ] >= 30 phieu co `confidence` VA co ket qua that
  - [ ] phan bo confidence theo khoang (calibration bins) de biet lech o dau
  - [ ] so mau `lessons_hint` (n) di kem moi phieu — de biet co bang chung hay khong
- Viec phai lam: giu `AGENT_CALIB_CAP=true`; do lai brier sau >= 30 phieu moi
- Tu lam duoc: CO

## match_exact (high)
- Do: **ty le ghep CHINH XAC (decision_id) = 0.099** (can: 0.8)
- Can thu thap / lam:
  - [ ] 56/729 phieu NOI duoc theo id nhung chi 101/729 da co lenh DONG de cham diem ⇒ can them ket qua (cho lenh dong)
  - [ ] >= 30 phieu/model co `decision_id` de so sanh
  - [ ] 10 cap ghep mau (phieu -> lenh) de kiem tay bang `tools/trace_trade.py`
- Viec phai lam: chay lai `python tools/council_eval.py` sau khi co them lenh dong
- Tu lam duoc: CO

## thin_models (med)
- Do: **so model co n_ghep < min_n = 11** (can: 0)
- Can thu thap / lam:
  - [ ] n_ghep >= 8 cho tung model (dang thieu: auto, claude-haiku-4.5, cline-pass/claude-sonnet-5, cline-pass/claude-sonnet-5.5, cline-pass/kimi-k3, cline-pass/mimo-v2.6-pro, cline-pass/minimax-m3, cline-pass/qwen3.7-plus, gemini-3.8-flash, gpt-5.6-terra, grok-4.6)
  - [ ] 1 lan chay `tools/council_probe.py --live` de do A/B co kiem soat
- Viec phai lam: chay them phien (hoac bo model treo) roi do lai
- Tu lam duoc: CO

## value_negative (med)
- Do: **model co value_r <= 0 = 1** (can: 0)
- Can thu thap / lam:
  - [ ] value_r + n cua tung model (local/llama3.2-3b-local)
  - [ ] xac nhan khong phai do ghep nham (xem `match_exact`)
- Viec phai lam: sau khi ghep chinh xac: them vao `CLINE_SKIP_MODELS`/`LOCAL_SKIP_MODELS`
- Tu lam duoc: KHONG — phai co nguoi (ghi vao `tools/ops_queue.py`)
