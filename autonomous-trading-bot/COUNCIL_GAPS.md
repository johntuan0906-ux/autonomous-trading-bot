# KE HOACH TU HOC CUA HOI DONG (tu sinh tu so lieu, khong phai y kien)

| # | Thieu hut | Do (hien tai -> can) | Tu lam |
|---|---|---|---|
| 1 | calibration | brier: 0.31 -> <= 0.25 | co |
| 2 | thin_models | so model co n_ghep < min_n: 10 -> 0 | co |
| 3 | value_negative | model co value_r <= 0: 2 -> 0 | KHONG (can nguoi) |

## calibration (high)
- Do: **brier = 0.31** (can: <= 0.25)
- Can thu thap / lam:
  - [ ] >= 30 phieu co `confidence` VA co ket qua that
  - [ ] phan bo confidence theo khoang (calibration bins) de biet lech o dau
  - [ ] so mau `lessons_hint` (n) di kem moi phieu — de biet co bang chung hay khong
- Viec phai lam: giu `AGENT_CALIB_CAP=true`; do lai brier sau >= 30 phieu moi
- Tu lam duoc: CO

## thin_models (med)
- Do: **so model co n_ghep < min_n = 10** (can: 0)
- Can thu thap / lam:
  - [ ] n_ghep >= 8 cho tung model (dang thieu: claude-haiku-4.5, cline-pass/claude-sonnet-5, cline-pass/claude-sonnet-5.5, cline-pass/kimi-k3, cline-pass/mimo-v2.6-pro, cline-pass/qwen3.7-plus, cline-pass/qwen3.8-max, gemini-3.8-flash, gpt-5.6-terra, grok-4.6)
  - [ ] 1 lan chay `tools/council_probe.py --live` de do A/B co kiem soat
- Viec phai lam: chay them phien (hoac bo model treo) roi do lai
- Tu lam duoc: CO

## value_negative (med)
- Do: **model co value_r <= 0 = 2** (can: 0)
- Can thu thap / lam:
  - [ ] value_r + n cua tung model (auto, cline-pass/qwen3.7-max)
  - [ ] xac nhan khong phai do ghep nham (xem `match_exact`)
- Viec phai lam: sau khi ghep chinh xac: them vao `CLINE_SKIP_MODELS`/`LOCAL_SKIP_MODELS`
- Tu lam duoc: KHONG — phai co nguoi (ghi vao `tools/ops_queue.py`)
