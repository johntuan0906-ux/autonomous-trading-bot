"""Danh muc LOP LOI da tung xay ra + TEST chot lai (bug catalog).

    python tools/bug_catalog.py                 # bang tom tat
    python tools/bug_catalog.py --grep "hoi dong"   # tim lop loi theo trieu chung
    python tools/bug_catalog.py --kind im-lang # loc theo loai
    python tools/bug_catalog.py --code B-003    # chi tiet 1 lop
    python tools/bug_catalog.py --json
    python tools/bug_catalog.py --check         # XAC MINH moi test duoc dan CO THAT

Vi sao (19/10, REPO_IDEAS §15.3 — "verification: traceability"): repo co ~960 test nhung
**khong co ban do "lop loi -> test"**. Da gap that: sua mot lop loi roi ve sau vo tinh
xoa/doi ten test => **mat chot chan ma khong ai biet** (dung lop loi "im lang" cua du an).
`--check` doc `tests/` va bao test bi thieu => "moi lop loi phai co test chot" tro thanh
luat KIEM TRA DUOC bang may, khong phai loi nhac.

Quy uoc `tests`: `file.py` (ca file) hoac `file.py::Class::test` (chinh xac) hoac
`file.py::Class` (ca lop) — de khi doi ten 1 test le khong bao dong gia.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KINDS = {
    "im-lang": "That bai IM LANG (khong ai biet he thong da bo qua / quyet khac)",
    "rui-ro": "Lien quan TIEN / rui ro / bao ve vi the",
    "cau-hinh": "Cau hinh bi doc sai / thay doi khong co hieu luc",
    "van-hanh": "Van hanh: watcher, pause, restart, khoi phuc",
    "ai": "Hoi dong AI: phieu, provider, do tin cay",
    # (26/10) Lop moi: DU LIEU SAI (journal/log/so lieu) — nguy hiem hon loi code vi no
    # khong lam he thong dung, no lam MOI KET LUAN ve he thong thanh RAC (B-031: `r` trong
    # journal co ban ghi 793R) ⇒ nguoi van hanh "sua" theo so lieu sai.
    "du-lieu": "Du lieu SAI (journal/log/so lieu) ⇒ moi ket luan dua tren no deu rac",
}

# Moi muc: code (on dinh, dung de tham chieu trong CONTEXT.md), title, kind, symptom
# (cach NHAN RA), guard (cai gi dang chan bay gio), files, tests, seen (ngay gap that).
CLASSES = [
    {
        "code": "B-001", "kind": "im-lang", "seen": "12/10/2026",
        "title": "Phieu hoi dong bi NUOT (log_decision gap dict)",
        "symptom": "`--council-health` bao 0/0 du hoi dong da bo phieu; journal thieu ban ghi COUNCIL",
        "guard": "`log_decision` chiu ca dict lan Decision; council_health nhom theo MODEL that (khong theo `critic_agent`)",
        "files": ["agents.py", "tools/council_vote.py"],
        "tests": ["test_agent_authority.py::TestCouncilHealth::test_phieu_hoi_dong_nhom_theo_model_khong_theo_critic_agent",
                  "test_agents.py::TestMultiModelCouncil::test_chay_het_cac_model_va_bo_qua_model_treo"],
    },
    {
        "code": "B-002", "kind": "ai", "seen": "16/10/2026",
        "title": "Tier `lite` => 0 phieu (moi model Cline lam duoc phieu deu xep `hard`)",
        "symptom": "Log `do kho 0.00 -> tier 'lite' (1 model)` + `hoi dong 1 model: 0A / 0V` ngay tren duong vao lenh",
        "guard": "`_council_models_by_tier()` loai model bi IGNORE TRUOC khi chon tier + mo rong dan khi <2 model; `AGENT_COUNCIL_SINGLE_BELOW=0`",
        "files": ["agents.py", ".env"],
        "tests": ["test_agents.py::TestMultiModelCouncil::test_tier_lite_khong_tra_ve_model_bi_ignore",
                  "test_agents.py::TestMultiModelCouncil::test_tier_lite_van_tra_du_model_khi_khong_co_ignore"],
    },
    {
        "code": "B-003", "kind": "cau-hinh", "seen": "15/10/2026",
        "title": "Danh sach SKIP khong khop TIEN TO => model da chet van duoc goi",
        "symptom": "Model trong `CLINE_SKIP_MODELS` van xuat hien trong luot goi (cham, rac journal)",
        "guard": "`agents._apply_skip()` so khop CA 2 dang ten (co/khong tien to provider), ap cho ca 5 provider",
        "files": ["agents.py", ".env"],
        "tests": ["test_agents.py::TestMultiModelCouncil::test_liet_ke_model_bi_skip"],
    },
    {
        "code": "B-004", "kind": "im-lang", "seen": "15/10/2026",
        "title": "Model bi SKIP BIEN MAT im lang (khong vao `abstained`)",
        "symptom": "Thieu phieu nhung khong biet vi sao: `votes` rong + `abstained` cung rong",
        "guard": "`multi_model_council` tra them `skipped` (model -> ten bien SKIP) va gop vao `abstained`; `turbo_demo` ghi ro ly do vao journal",
        "files": ["agents.py", "turbo_demo.py"],
        "tests": ["test_agents.py::TestMultiModelCouncil::test_model_bi_danh_sach_skip_hien_dien_trong_abstained"],
    },
    {
        "code": "B-005", "kind": "cau-hinh", "seen": "15/10/2026",
        "title": "`.env` doc theo THU MUC MODULE (khong theo cwd) => tool nham instance dung sai key/mode",
        "symptom": "`-2015 Invalid API-key` khi nham `../atb-live`; snapshot LIVE ghi `testnet=true` => `live_guard` BO QUA moi chot chan",
        "guard": "`config.load_instance_env()` + bien `ATB_ENV_FILE` (dat TRUOC khi import, `override=True`); chan doan: `python tools/instance_env.py`",
        "files": ["config.py", "tools/instance_env.py", "state_sync.py"],
        "tests": ["test_ops_tools.py::TestEnvTheoInstance::test_load_instance_env_ghi_de_bien_cu",
                  "test_ops_tools.py::TestEnvTheoInstance::test_state_sync_duong_dan_theo_instance"],
    },
    {
        "code": "B-006", "kind": "van-hanh", "seen": "15/10/2026",
        "title": "`restart_when_flat` nham SAI instance (kill supervisor cua instance kia)",
        "symptom": "LIVE khong bao gio duoc ap cau hinh moi; nguy hon: kill nham instance dang co vi the mo",
        "guard": "`--target {testnet,live}` + `chdir` vao instance TRUOC khi doc `Settings()`; truyen `root` xuong moi ham con",
        "files": ["restart_when_flat.py"],
        "tests": ["test_ops_tools.py::TestRestartWhenFlatTarget::test_anh_xa_instance",
                  "test_ops_tools.py::TestRestartWhenFlatTarget::test_target_la_thi_thoat"],
    },
    {
        "code": "B-007", "kind": "rui-ro", "seen": "02/10/2026",
        "title": "Kill-switch trip OAN do lenh DUST (lo khong dang ke)",
        "symptom": "Trip voi `5 consecutive losses` nhung tong lo < 1 USDT (1 lenh pnl = -0.0011)",
        "guard": "`MIN_LOSS_USDT` (mac dinh 0.5): lo nho hon nguong la TRUNG TINH, khong tinh vao chuoi thua",
        "files": ["risk.py"],
        "tests": ["test_p0_safety.py::TestKillSwitchLoNho::test_lo_that_van_tinh_va_trip_dung_lan_thu_5"],
    },
    {
        "code": "B-008", "kind": "van-hanh", "seen": "18/10/2026",
        "title": "Kill-switch KHONG tu xoa => instance ket pause VO THOI HAN",
        "symptom": "TESTNET `tripped:true` tu 15/10, round van chay `monitor_only_end`, luot goi LLM cuoi cung 15/10 (3.6 ngay khong hoc duoc gi)",
        "guard": "Co y KHONG tu xoa (`risk.note_equity`) — phai `risk.py --reset`; do la diem chan an toan, nen phai CO NGUOI/TIEN TRINH NHAC (xem `tools/ops_queue.py`)",
        "files": ["risk.py"],
        "tests": ["test_p0_safety.py::TestRiskStateSongSotRestart::test_sang_ngay_moi_KHONG_tu_mo_lai_kill_switch",
                  "test_risk_mode.py::TestNoteEquityMode::test_doi_che_do_khong_tu_xoa_tripped"],
    },
    {
        "code": "B-009", "kind": "van-hanh", "seen": "19/10/2026",
        "title": "Cong tam dung vao lenh KHONG co han => 'tam dung roi quen mo lai'",
        "symptom": "`logs/entries_pause.json` `paused:true` tu nhieu ngay; bot khong mo lenh moi ma khong ai biet",
        "guard": "`entries_gate.pause(..., hours=N)` ghi `until`; qua han TU MO LAI + ghi vet `by` (provenance)",
        "files": ["entries_gate.py", "restart_when_flat.py"],
        "tests": ["test_ops_tools.py::TestEntriesGateExpiry::test_het_han_thi_tu_mo_lai",
                  "test_ops_tools.py::TestEntriesGateExpiry::test_until_hong_thi_van_tam_dung",
                  "test_ops_tools.py::TestRestartWhenFlatPause::test_pause_truoc_khi_restart"],
    },
    {
        "code": "B-010", "kind": "ai", "seen": "18/10/2026",
        "title": "`402 Payment Required` => hoi dong IM LANG (va co the tu hoi sau vai gio)",
        "symptom": "Moi model tra 402; `--council-health` chi thay `treo`; probe lai thay 7/8 model OK",
        "guard": "Chot chan provider theo thoi han (`AGENT_PROVIDER_BILLING_PAUSE_SEC`, mac dinh 12h) + bao nguoi van hanh; gap 402 thi LUON `python tools/probe_cline.py` lai truoc khi ket luan het tien",
        "files": ["agents.py", "tools/probe_cline.py"],
        "tests": ["test_agents.py::TestProviderLoiThanhToan::test_loi_thuong_van_pause_ngan",
                  "test_agents.py::TestProviderPause::test_pause_het_han_tu_mo_lai"],
    },
    {
        "code": "B-011", "kind": "ai", "seen": "18/10/2026",
        "title": "Probe 'OK' KHONG co nghia la BO DUOC PHIEU (muse-spark)",
        "symptom": "`council_vote` liet ke 6 model nhung chi 5 phieu; model tra JSON hop le khi hoi rieng van vao `abstained` (3/3 lan)",
        "guard": "`council_vote` in ro `KHONG TRA VE PHIEU (n)`; nguyen tac: danh sach liet ke = so model THUC SU bo phieu",
        "files": ["tools/council_vote.py", ".env"],
        "tests": ["test_ops_tools.py::TestCouncilVoteReport::test_model_khong_tra_phieu_duoc_bao_ro"],
    },
    {
        "code": "B-012", "kind": "rui-ro", "seen": "15/10/2026",
        "title": "Lenh CLOSE khong co OPEN (DUST) sinh to hop GIA `? | ? | ? | ?`",
        "symptom": "`LESSONS.md` co muc n=84 avgR=+0.383 trong 'NEN UU TIEN' — tin hieu khong co that",
        "guard": "`load_closed(unpaired='mark')` gan `origin='no_open'`; `bucket_stats` loai cac lenh nay khoi thong ke",
        "files": ["lessons.py"],
        "tests": ["test_lessons.py::TestLoadClosed::test_close_khong_co_open_van_dem_duoc"],
    },
    {
        "code": "B-013", "kind": "rui-ro", "seen": "12/10/2026",
        "title": "Lenh STOP/TP treo CU khong bi huy => nhieu lenh bao ve chong nhau, co the dong nham vi the MOI",
        "symptom": "`orders_audit` thay nhieu hon 2x so vi the; vi the moi bi dong ngay sau khi mo",
        "guard": "`cancel_symbol_orders()` TRUOC khi arm; dong lenh cung don lenh treo; partial re-arm theo qty con lai",
        "files": ["exchange.py", "turbo_demo.py", "tools/orders_audit.py"],
        "tests": ["test_p0_safety.py::TestBotSafety::test_close_don_sach_lenh_treo",
                  "test_p0_safety.py::TestBotSafety::test_partial_arm_lai_sl_tp_theo_qty_con_lai"],
    },
    {
        "code": "B-014", "kind": "rui-ro", "seen": "12/10/2026",
        "title": "Loi mang SAU khi lenh da khop => tuong that bai roi MO TRUNG",
        "symptom": "2 vi the cung cap; `managed_state` lech so voi san",
        "guard": "Ghi so TRUOC khi arm + doi chieu lai san khi loi mang (khong mo lai khi da khop)",
        "files": ["turbo_demo.py", "position_sync.py"],
        "tests": ["test_p0_safety.py::TestBotSafety::test_loi_mang_ma_lenh_DA_khop_thi_ghi_nhan_khong_mo_trung"],
    },
    {
        "code": "B-015", "kind": "rui-ro", "seen": "12/10/2026",
        "title": "Vi the do NGUOI khac mo tren LIVE bi bot 'nhan nuoi' (tu dat SL/TP, tu dong)",
        "symptom": "Vi the khong do bot mo bi dong/chot loi ngoai y muon",
        "guard": "`ADOPT_SKIP_SYMBOLS` (nhan ca `BTW` lan `BTW/USDT:USDT`): bo qua hoan toan; doc qty loi thi GIU vi the (khong xoa mu)",
        "files": ["position_sync.py", ".env"],
        "tests": ["test_p0_safety.py::TestDonViTheMa::test_khong_doc_duoc_qty_thi_GIU_vi_the",
                  "test_p0_safety.py::TestDonViTheMa::test_san_xac_nhan_qty_0_thi_xoa_khoi_portfolio"],
    },
    {
        "code": "B-016", "kind": "rui-ro", "seen": "12/10/2026",
        "title": "Tran risk danh muc / DD tinh tren BALANCE hardcode => tran 2% khong dung nghia 2% tai khoan",
        "symptom": "4 vi the x 1% = 4% > `MAX_DAILY_LOSS_PCT` 2%; DD bao sai so voi equity that",
        "guard": "`MAX_TOTAL_RISK_PCT` (theo moc 1R) + `risk.note_equity` lay EQUITY THAT dau ngay lam moc DD",
        "files": ["risk.py", "portfolio.py"],
        "tests": ["test_p0_safety.py::TestRiskDanhMuc::test_can_add_risk_chan_khi_vuot_tran",
                  "test_p0_safety.py::TestBotSafety::test_equity_tach_khoi_balance_tran_size",
                  "test_p0_safety.py::TestRiskStateSongSotRestart::test_dd_tinh_tren_equity_that_khong_phai_balance_hardcode"],
    },
    {
        "code": "B-017", "kind": "ai", "seen": "15/10/2026",
        "title": "Phieu HAU KIEM lam nhieu bang diem model (thien lech nhin truoc)",
        "symptom": "Bang diem co dong cua model `review` (bo phieu SAU khi lenh dong) => +0.044 gia",
        "guard": "`council_evals.is_pre_trade()` loai `status=CLOSED/REVIEW` + vai `review/review_agent` khoi `pair_cases()`",
        "files": ["council_evals.py", "tools/council_eval.py"],
        "tests": ["test_council_evals.py::TestPairCases::test_bo_phieu_hau_kiem_khoi_bang_diem"],
    },
    {
        "code": "B-018", "kind": "ai", "seen": "19/10/2026",
        "title": "Hoa phieu hoi dong bi hieu nham la 'da dong thuan'",
        "symptom": "2 ALLOW / 2 VETO => khong ai biet phai lam gi; de bi doc thanh 'hoi dong dong y'",
        "guard": "`_tally` tra `NO_OPINION` khi bang phieu; `council_vote` in `hoa/khong du phieu`; hoa => GIU NGUYEN trang thai (fail-safe)",
        "files": ["agents.py", "tools/council_vote.py"],
        "tests": ["test_agents.py::TestMultiModelCouncil::test_hoa_phieu_thi_no_opinion_khong_chan_lenh"],
    },
    {
        "code": "B-019", "kind": "im-lang", "seen": "19/10/2026",
        "title": "Thay doi `.env` KHONG co hieu luc voi tien trinh DANG chay",
        "symptom": "`.env` ghi tran 1.0% nhung log van `> 2.00% (MAX_TOTAL_RISK_PCT)`",
        "guard": "Ap bang watcher `restart_when_flat.py` (restart khi HET vi the, khong cat ngang lenh) + ghi vet vao CONTEXT.md; kiem chung `Settings()` bang `ATB_ENV_FILE`",
        "files": ["restart_when_flat.py", "config.py"],
        "tests": ["test_ops_tools.py::TestRestartWhenFlatPause::test_pause_ghi_dung_file_instance"],
    },
    {
        "code": "B-020", "kind": "van-hanh", "seen": "19/10/2026",
        "title": "Cong cu khong TU MO TA duoc => agent/nguoi phai doc code moi biet no lam gi",
        "symptom": "Tool chay duoc nhung khong biet muc dich, tham so, co test hay khong",
        "guard": "`tools/capabilities.py` (manifest: ten, muc dich, test) + `--check` bao tool thieu docstring / khong co test",
        "files": ["tools/capabilities.py"],
        "tests": ["test_ops_tools.py::TestCapabilities::test_quet_duoc_tool_va_muc_dich",
                  "test_ops_tools.py::TestCapabilities::test_check_phat_hien_tool_thieu_docstring"],
    },
    {
        "code": "B-021", "kind": "im-lang", "seen": "19/10/2026",
        "title": "TIEN TRINH TEST ghi de STATE cua instance THAT (nhip tim ma)",
        "symptom": "`logs/heartbeat.json` = `{\"pid\": 28000, \"round\": 2, \"phase\": \"monitor_only\"}` nhung pid 28000 KHONG ton tai; chay suite xong `ops.py`/`STATE.md`/`deadman` doc phai so lieu MA",
        "guard": "`turbo_demo.heartbeat(path=None)` nhan `path`/`ATB_HEARTBEAT_PATH`; dang chay duoi test runner (`__main__.__file__` chua `unittest`/`pytest`) thi TU DONG ghi vao file tam — khong bao gio cham state that",
        "files": ["turbo_demo.py", "tests/test_p0_safety.py"],
        "tests": ["test_p0_safety.py::TestHeartbeatKhongGhiStateThat::test_duoi_test_runner_thi_tu_dong_ghi_file_tam",
                  "test_p0_safety.py::TestHeartbeatKhongGhiStateThat::test_chi_dinh_path_thi_ghi_dung_do",
                  "test_p0_safety.py::TestMonitorOnly::test_kill_cleared_doc_state"],
    },
    {
        "code": "B-022", "kind": "cau-hinh", "seen": "19/10/2026",
        "title": "`MAX_POSITIONS` la \"chot gia\" tren LIVE: `turbo_demo` bo qua VO DIEU KIEN",
        "symptom": "`.env` dat `MAX_POSITIONS=1` nhung LIVE co **8** vi the, TESTNET **14** vi the (do that 19/10 15:03); nguoi van hanh + hoi dong tuong da gioi han concurrency 1",
        "guard": "`turbo_demo.max_positions_block()` chan som tren LIVE (`SKIP_MAX_POS`); mac dinh `TURBO_BYPASS_MAX_POSITIONS` = DEMO-moi-bo-qua (`config._default_turbo_bypass`); thu pham chan that su con lai la `MAX_TOTAL_RISK_PCT` + kill-switch",
        "files": ["turbo_demo.py", "config.py", "run_forever.py"],
        "tests": ["test_turbo_gate.py::TestMaxPositionsBlock::test_live_het_slot_thi_chan",
                  "test_turbo_gate.py::TestMaxPositionsBlock::test_demo_thi_bo_qua",
                  "test_turbo_gate.py::TestMaxPositionsBlock::test_thieu_thuoc_tinh_thi_ton_trong_gioi_han",
                  "test_turbo_gate.py::TestMacDinhTheoCheDo::test_live_mac_dinh_ton_trong",
                  "test_turbo_gate.py::TestMacDinhTheoCheDo::test_demo_mac_dinh_bo_qua"],
    },
    {
        "code": "B-023", "kind": "rui-ro", "seen": "20/10/2026",
        "title": "`-2022 ReduceOnly Order is rejected`: san tu choi `reduceOnly` cho lenh MARKET",
        "symptom": "`close X failed: ... -2022` + `monitor X failed: ... -2022` hang chuc lan/ngay (**157 lan** ngay 20/10) ⇒ `kill.register_error()` ⇒ **kill-switch TRIP OAN** ('7 consecutive API errors', 09:06 20/10); `_flatten` sau do dong 16 vi the ma **KHONG dong duoc vi the nao** ⇒ so sach SACH trong khi san van giu du 16 vi the (vi the mo coi — chi con bao ve da arm truoc do)",
        "guard": "`exchange.close_position`: gap `-2022` ⇒ doc lai vi the THAT **cua DUNG PHIA** (`position_qty(..., direction=...)` — HEDGE co 2 dong LONG/SHORT cung symbol); qty=0 ⇒ `already_closed` (coi nhu DA DONG); con vi the ⇒ `_close_exact()` gui lai MARKET **KHONG `reduceOnly`** voi `qty = min(qty_san, qty_yeu_cau)`. DO THAT (demo, 20/10): `reduceOnly=True` MARKET bi tu choi VO DIEU KIEN (qty=1 tren vi the 31 hop dong VAN bi tu choi); `closePosition=true` cung khong dung duoc cho MARKET (`-4136 Target strategy invalid for orderType MARKET`); chi lenh khong reduceOnly + qty dung vi the moi FILLED. Sau khi dong: DOC LAI ⇒ bao `left_over`/`flipped`; khong doc duoc ⇒ `verify_failed`. Memo `_ro_market_rejected` (khong ton 1 request chac chan that bai moi lan dong)",
        "files": ["exchange.py", "bot.py", "position_sync.py", "tools/ops.py"],
        "tests": ["test_exchange_hedge.py::TestCloseDaDong2022",
                  "test_p0_safety.py::TestBotSafety::test_close_2022_coi_nhu_da_dong_va_van_don_lenh_treo",
                  "test_p0_safety.py::TestBotSafety::test_partial_gap_2022_thi_ghi_CLOSE_nhu_SL_va_khong_trip_kill_switch",
                  "test_p0_safety.py::TestBotSafety::test_close_dong_lai_bang_qty_that_thi_khong_bao_loi",
                  "test_p0_safety.py::TestBotSafety::test_close_vi_the_LAT_CHIEU_thi_bao_DONG_nhung_khong_crash",
                  "test_p0_safety.py::TestDonViTheMa::test_doc_qty_theo_DUNG_PHIA_cua_vi_the"],
    },
    {
        "code": "B-024", "kind": "im-lang", "seen": "20/10/2026",
        "title": "Vi the bui KHONG THE dong: lap lai nghi thuc that bai MOI VONG, mai mai",
        "symptom": "`ERROR DUST BANK/USDT:USDT qty=1: san TU CHOI dong (notional qua nho) -> GIU LAI vi the` moi ~4 phut (do that 20/10: vi the **1 hop dong = 0.026 USDT** trong khi san yeu cau toi thieu **5 USDT** ⇒ khong lenh MARKET/LIMIT nao dong duoc); moi vong con ghi 1 dong **CLOSE GIA** vao journal (lam sai WR/PF) + arm lai SL/TP (ton han ngach stop-order)",
        "guard": "`bot._dust_give_up()`: dem so lan that bai (`dust_fail`, `DUST_MAX_FAILS=3`) ⇒ ghi symbol vao `logs/dust_skip.json` + bo khoi so sach + bao **1 lan**; `position_sync.adopt` bo qua symbol trong file do (khong keo lai moi vong/restart). Muon theo doi lai: xoa symbol khoi file",
        "files": ["bot.py", "position_sync.py"],
        "tests": ["test_p0_safety.py::TestViTheBuiChet::test_that_bai_lap_lai_thi_bo_quan_ly_va_ghi_file",
                  "test_p0_safety.py::TestViTheBuiChet::test_dong_duoc_thi_khong_ghi_gi_va_xoa_bo_dem",
                  "test_p0_safety.py::TestViTheBuiChet::test_adopt_bo_qua_symbol_da_bo_quan_ly"],
    },
    {
        "code": "B-025", "kind": "im-lang", "seen": "21/10/2026",
        "title": "File trang thai ghi KHONG nguyen tu — mat dien giua luc ghi la file bi cat ngang",
        "symptom": "`.env` (chua KEY API), `logs/entries_pause.json`, `logs/state.json`, `logs/deadman.json`, artifact quyet dinh deu ghi bang `Path.write_text()` tran: mat dien/kill giua luc ghi ⇒ file hong. Voi `.env` thi bot **khong khoi dong duoc**; voi `state.json` thi supervisor/deadman doc ra `{}` ⇒ tuong bot chet ⇒ restart loop; artifact hong = mat vet quyet dinh",
        "guard": "`atomic.py`: ghi file tam CUNG THU MUC -> `flush` + `os.fsync` (xuong dia TRUOC khi doi ten) -> `os.replace` co retry `PermissionError` (Windows: AV/indexer giu handle). Loi ⇒ **file cu giu nguyen**, file tam duoc don. Ap cho `entries_gate`, `state_sync.go_live`, `run_forever` (nhip tim + lock), `tools/deadman`, `tools/ops_artifact`, `tools/ops_queue`",
        "files": ["atomic.py", "entries_gate.py", "state_sync.py", "run_forever.py",
                  "tools/deadman.py", "tools/ops_artifact.py", "tools/ops_queue.py"],
        "tests": ["test_atomic_write.py::TestWriteTextAtomic::test_loi_khi_replace_thi_giu_nguyen_file_cu",
                  "test_atomic_write.py::TestWriteTextAtomic::test_retry_khi_bi_khoa_tam_thoi",
                  "test_atomic_write.py::TestWriteTextAtomic::test_file_tam_nam_cung_thu_muc",
                  "test_atomic_write.py::TestWriteJsonAtomic::test_roundtrip_giu_chu_viet_va_indent"],
    },
    {
        "code": "B-026", "kind": "im-lang", "seen": "21/10/2026",
        "title": "`entries_pause.json` hong ⇒ bot TU MO LAI vao lenh (fail-open) trong khi nguoi van hanh tuong dang tam dung",
        "symptom": "`entries_gate.read()` tra `{}` cho MOI loi (ke ca JSON hong) ⇒ `paused()` = False. File bi cat ngang (B-025), sua tay, hoac o dia loi ⇒ **cong tam dung bien mat trong im lang**, bot vao lenh moi. Chinh docstring module ghi 'file hong => VAN tam dung' nhung code lam nguoc lai",
        "guard": "`entries_gate.read()` phan biet: khong co file ⇒ `{}` (khong tam dung); co file nhung JSON hong ⇒ **FAIL-SAFE**: tra ban ghi `paused=True`, `corrupt=True`, `until = mtime + CORRUPT_GRACE_H (6h)` ⇒ `paused()` bao dang tam dung; qua 6h tu goi `resume()` ghi lai file hop le (khong khoa vinh vien)",
        "files": ["entries_gate.py"],
        "tests": ["test_ops_safety.py::TestEntriesGate::test_file_hong_thi_tam_dung_an_toan",
                  "test_ops_safety.py::TestEntriesGate::test_file_hong_tu_het_han_sau_grace",
                  "test_ops_tools.py::TestEntriesGateExpiry::test_file_hong_thi_tam_dung_an_toan"],
    },
    {
        "code": "B-027", "kind": "im-lang", "seen": "21/10/2026",
        "title": "Daemon hoi dong cham tran ⇒ MAT NHIP TIM (im lang) + dem sai luot da hoi",
        "symptom": "Daemon chay 15 phut/lan o che do live: moi lan **khong co chu de** van bi tinh 1 luot ⇒ het tran 12 luot sau ~3 gio; `cycles_blocked`/`budget_blocked` **return TRUOC khi ghi** `logs/council_heartbeat.json` ⇒ `--status` bao 'KHONG CO NHIP' (do that 21/10: nhip cu **4,6 gio**) du daemon hoan toan khoe. Cham tran la chuyen binh thuong, nhung bi bao nhu da chet = dung lop loi 'im lang'",
        "guard": "`run_cycle` dem luot CHI khi THUC SU hoi hoi dong (`live and topics`); `_beat()` ghi nhip tim o **MOI duong thoat** (locked / cycles_blocked / budget_blocked / binh thuong) kem co `blocked` + `reason` de phan biet 'bi chan' voi 'da chet'",
        "files": ["tools/council_daemon.py"],
        "tests": ["test_council_daemon.py::TestNhipTimVaTran::test_khong_co_chu_de_thi_khong_tinh_chu_ky",
                  "test_council_daemon.py::TestNhipTimVaTran::test_cham_tran_van_ghi_nhip_tim",
                  "test_council_daemon.py::TestNhipTimVaTran::test_cham_tran_chi_phi_van_ghi_nhip_tim"],
    },
    {
        "code": "B-028", "kind": "im-lang", "seen": "22/10/2026",
        "title": "Van de tien trinh/an toan chi duoc IN ra (khong vao hang doi) + do phu bao ve KHONG AI KIEM",
        "symptom": "`watch_regress --check` phat hien kill-switch TRIPPED / supervisor chet / nhip tim cu nhung chi `print` roi `return 1`: khong co cau hoi nao vao `ops_queue` ⇒ nguoi van hanh khong bao gio duoc hoi (dung lop loi 'im lang'). Kem theo: khong co gi dinh ky kiem 'moi vi the co du 1 SL + 1 TP' ⇒ lenh bao ve TRUNG tich tu den khi cham tran stop-order (`-4045`) moi biet (do that 22/10 LIVE: BICO co **4** lenh bao ve = 2 cap TRUNG). Cong cu `orders_audit` bao 'KHONG co SL/TP' cho ca vi the BUI da ghi `dust_skip.json` ⇒ vua bao dong gia vua CHE MAT vi the TRAN that",
        "guard": "`watch_regress.notify()` day ca `problems` vao `ops_queue` theo LOAI van de (`problem_kind`: kill/naked/dupes/supervisor/child/heartbeat/council) ⇒ bao lai moi 1h khi van con loi (khong spam, khong tat); `refresh_orders()` + `--orders` (task `ATB-WatchRegress` moi 10 phut) ghi `logs/orders_snapshot.json` va bat vi the TRAN / cap lenh TRUNG; `orders_audit.load_dust()` tach BUI (khong the dat SL/TP) khoi TRAN va ket luan rieng cho TRAN; `ops.py` + `harness_audit --with-exchange` hien thi/canh bao TRUNG/TRAN",
        "files": ["tools/watch_regress.py", "tools/orders_audit.py", "tools/ops.py",
                  "tools/harness_audit.py"],
        "tests": ["test_watch_regress.py::TestBaoVeTrenSan::test_notify_day_van_de_tien_trinh_vao_hang_doi",
                  "test_watch_regress.py::TestBaoVeTrenSan::test_health_bat_vi_the_tran_va_lenh_bao_ve_trung",
                  "test_watch_regress.py::TestBaoVeTrenSan::test_problem_kind_on_dinh_khi_SO_thay_doi",
                  "test_watch_regress.py::TestBaoVeTrenSan::test_refresh_orders_tra_naked_va_dupes_va_ghi_snapshot",
                  "test_orders_audit.py::TestViTheBuiVaTran::test_vi_the_tran_thi_ket_luan_rieng",
                  "test_orders_audit.py::TestViTheBuiVaTran::test_bui_khong_bao_dong_gia"],
    },
    {
        "code": "B-029", "kind": "im-lang", "seen": "26/10/2026",
        "title": "Hang doi van hanh ghi theo cwd ⇒ Task Scheduler (cwd=System32) lam canh bao BIEN MAT trong thinh lang",
        "symptom": "`tools/ops_queue.py` dung duong dan TUONG DOI (`logs/ops_questions.json`) ⇒ phu thuoc cwd. Task `ATB-WatchRegress` khong dat `<WorkingDirectory>` ⇒ cwd = `C:\\Windows\\System32`; Windows CO SAN `System32\\logs` nhung **khong ghi duoc** (`PermissionError` — do that) ⇒ `_write_list` tra False TRONG THINH LANG. Do that 24/10 12:00: `logs/regress_watch.log` co dong `VAN DE naked @ LIVE: 1 vi the TRAN (khong SL/TP): 1000CAT/USDT:USDT` nhung hang doi TRONG ⇒ khong ai duoc hoi",
        "guard": "`ops_queue._instance_base()`: chi coi cwd la instance khi co `logs/` VA **dau hieu bot** (`turbo_demo.py`/`config.py`/`bot.py`), khong thi dung `ROOT`; `_write_list` tu `mkdir` thu muc dich + bao loi ra **stderr** (khong im lang); `watch_regress.notify()` dinh kem `open_path` theo TUNG instance (LIVE -> `atb-live/logs/ops_questions.json`) va ghi vet `KHONG GHI DUOC HANG DOI` vao `regress_watch.log` khi that bai",
        "files": ["tools/ops_queue.py", "tools/watch_regress.py"],
        "tests": ["test_ops_tools.py::TestOpsQueue::test_cwd_khac_thi_dung_thu_muc_repo",
                  "test_ops_tools.py::TestOpsQueue::test_ghi_loi_thi_bao_ra_stderr",
                  "test_watch_regress.py::TestBaoVeTrenSan::test_notify_dinh_kem_DUONG_DAN_hang_doi_cua_instance",
                  "test_watch_regress.py::TestBaoVeTrenSan::test_notify_ghi_vet_khi_KHONG_ghi_duoc_hang_doi"],
    },
    {
        "code": "B-030", "kind": "im-lang", "seen": "26/10/2026",
        "title": "Mo lenh THANH CONG bi dem la 'loi' ⇒ ops bao 'CAN XEM' gia (bao dong gia lam nguoi van hanh quen bao dong that)",
        "symptom": "`tools/ops.py` de `\"OPENED\"` trong `COUNT_PATTERNS` — do la STATUS cua lenh mo THANH CONG (`{'status': 'OPENED'}` trong dong tong ket vong) ⇒ moi lan mo lenh, `errors_win` co `OPENED: 1` ⇒ ops ket luan **'CAN XEM: TESTNET'** du he thong hoan toan khoe (do that 26/10 13:52, ngay sau khi doi hinh hoc: TESTNET round 2 co 1 lenh OPENED ⇒ bao dong gia). Cung lop loi voi `LIVE INTERLOCK OK` da sua truoc do",
        "guard": "Bo `\"OPENED\"` khoi `COUNT_PATTERNS`; tach `ops.count_errors(lines)` de test duoc; loi mo lenh THAT co mau rieng (`ORDER_FAILED`/`ERROR`/`REJECTED`) VAN duoc dem",
        "files": ["tools/ops.py"],
        "tests": ["test_ops_tools.py::TestDemLoiBaoDongGia::test_OPENED_khong_bi_dem_la_loi",
                  "test_ops_tools.py::TestDemLoiBaoDongGia::test_loi_that_van_bi_dem",
                  "test_ops_tools.py::TestDemLoiBaoDongGia::test_mau_OPENED_da_bi_bo_khoi_danh_sach"],
    },
    {
        "code": "B-031", "kind": "du-lieu", "seen": "26/10/2026",
        "title": "Truong `r` trong journal SAI (co ban ghi r=793 va r=+196 cho lenh LO) ⇒ moi thong ke dung `r` la RAC",
        "symptom": "Do that 26/10 tren `logs/journal.jsonl` TESTNET (3342 ban ghi CLOSE): max `r`=793.07, 319 ban ghi `r`>5, min `r`=-14.84, trung vi `r`=+0.076 (vo ly voi WR 43%). Vi du cu the: DASH entry 49.32 -> exit 48.84 (LENH LO) nhung ghi `r`=+196.36; BNB entry 727.33 -> exit 730.04 ghi `r`=793.07; 315 ban ghi FLATTEN co |r|>5. Nghia la **moi ket luan dua tren `r`/`avgR`/`PF` doc tu journal deu vo nghia** — ke ca \"do luong hinh hoc moi tot hay xau\": suyt nua thi `tools/review_due.py` da bao \"nen avgR=+1.521 PF=5.89\" (do la RAC). Nguon goc trong `trade_mgmt.r_multiple` (co chan `dist<=0` ⇒ 0.0) CHUA xac dinh — nghi `initial_sl` bi dat sat entry khi `position_sync.adopt` vi the; dang theo doi, KHONG ket luan khi chua do duoc. **ANH HUONG DO THAT (do 26/10)**: `STATE.md` bao **PF(R)=5.345** — chinh la PF tinh tu truong `r` (da kiem chung: pos/neg cua `r` = 5.345) — trong khi **PF(R) THAT** (937 lenh ghep duoc, R tinh tu gia) chi **1.013**, avgR=+0.004, WR=53% ⇒ bot dang **hoa von**, KHONG phai \"lai khung\"; cac cong dung `pf_r` doc tu journal (`state_sync.py` -> STATE.md, `live_ready.py` PF(R)>=1.2, `live_guard.py` PF>=1.2) vi vay **dang cham bang so RAC**",
        "guard": "`tools/review_due.pair_trades()` ghep OPEN->CLOSE theo (pair, direction) va tinh **R THAT tu gia**: `r = (exit-entry)/|entry-sl|` (± theo chieu); loai ban ghi ngoai dai hop ly `R_BAND=(-1.6, 5.0)` va DEM `n_dropped` de minh bach; `rr` cung tinh tu gia (khong tin truong `rr` san co)",
        "files": ["trade_mgmt.py", "bot.py", "monitor_report.py", "lessons.py",
                  "strategy.py", "tools/review_due.py"],
        "tests": ["test_review_due.py::TestPairTrades::test_rr_tinh_tu_gia_khong_tin_truong_rr",
                  "test_review_due.py::TestPairTrades::test_bo_R_ngoai_dai_hop_ly",
                  "test_review_due.py::TestRun::test_ban_ghi_rac_bi_loai_truoc_khi_tinh"],
        "guard2": ("Da va GOC (28/10): `trade_mgmt.risk_distance_ok/r_multiple/trade_result` tra `r_valid=False` + R=0 khi khoang cach 1R khong hop le; `bot.py` ghi `r_valid` vao MOI duong dong; `monitor_report._r_ok` + `lessons.R_BAND` + `strategy.R_BAND` LOAI R rac khoi pf_r/e_r/sum_r; dung lai `logs/strategy_stats.json` 2 instance (backup .bak-b031)"),
        "tests2": ["test_trade_mgmt.py::TestChanRRacB031::test_r_multiple_khong_no_khi_sl_sat_entry",
                   "test_trade_mgmt.py::TestChanRRacB031::test_manage_khong_kich_hoat_partial_khi_R_rac",
                   "test_monitor_report.py::TestLocRRacB031::test_r_ngoai_dai_bi_loai",
                   "test_lessons.py::TestRRacKhongCongVaoSumR::test_r_ngoai_dai_bi_bo_qua_nhung_giu_n"],
    },
    {
        "code": "B-032", "kind": "du-lieu", "seen": "28/10/2026",
        "title": "Nhan `won` cho learner SAI (lenh LAI bi danh dau THUA) ⇒ learner lech MOT CHIEU ve phia bi quan ⇒ BLOCKED_LEARN chan gan het setup",
        "symptom": "Do that 28/10 tren journal: TESTNET **220/1717 lenh co PnL>0 (13%) bi danh dau THUA** (FLATTEN=189, DUST=28, CLOSE=3) va **0 chieu nguoc lai**; LIVE 71/436 (16%). Nhan cu `won = reason in (TP,TRAIL) or (BE and partial) or (partial and pnl>0)` ⇒ moi lenh dong do FLATTEN/DUST/CLOSE du CO LAI van bi tinh la THUA ⇒ learner (logistic online, hoc tu `won`) hoc lech mot chieu ve phia bi quan ⇒ `edge` am ⇒ turbo_demo chan `BLOCKED_LEARN` (~349 luot trong 500 dong log TESTNET, ly do \"learner edge -0.80\") ⇒ bot dung yen DU DA go STRATEGY_BLOCK",
        "guard": "`learner.money_label(pnl)` = **su that TIEN** (`pnl > 0`); `turbo_demo` dung nhan nay khi goi `_learner.update`; `logs/learner.json` duoc DUNG LAI bang replay journal theo thu tu thoi gian voi nhan tien (backup `.bak-b032`) ⇒ TESTNET 913 lan hoc (63% WIN theo tien), LIVE 560 (67%)",
        "files": ["learner.py", "turbo_demo.py"],
        "tests": ["test_learner_label.py::TestNhanTheoTienB032::test_lenh_lai_do_FLATTEN_van_la_WIN",
                  "test_learner_label.py::TestNhanTheoTienB032::test_hoc_tu_nhan_tien_thi_khong_lech_mot_chieu"],
    },
    {
        "code": "B-033", "kind": "ai", "seen": "28/10/2026",
        "title": "Learner chan OAN vi KHONG kiem dinh calibration (SGD online lech) ⇒ bot dung yen du moi cong khac da mo",
        "symptom": "Do that 28/10 (200 lenh ghep cap gan nhat): TESTNET **WIN thuc te 58% nhung learner du doan p = 23%** (edge -0.53, `b` = -0.479) ⇒ chan 64% setup ⇒ ~349 luot `BLOCKED_LEARN`/500 dong log; LIVE 60% vs 48% (chan 13%). Learner MOI (chua hoc) cho edge +0.33 tren CUNG bo feats ⇒ loi nam o TRONG SO da hoc. `update()` la SGD logistic DUNG cong thuc nhung chay ONLINE tren chuoi KHONG DUNG ⇒ trong so cuoi bi chi phoi boi ~100 lenh gan nhat ⇒ lech calibration (model dung de chan tien that ma khong ai kiem dinh)",
        "guard": "`tools/learner_refit.py`: fit logistic chinh quy (L2) tren train 80% cu nhat + KIEM DINH holdout 20% moi nhat (log-loss vs base-rate); LUOI AN TOAN: khong thang base-rate ⇒ ghi learner TRUNG TINH (w=0, b=logit(base_rate)) ⇒ khong bao gio chan; bao cao mo ta DUNG model se ghi; backup .bak-refit. Ket qua that: TESTNET THANG (0.6885 < 0.6940) ⇒ chan 0%; LIVE khong thang ⇒ TRUNG TINH ⇒ chan 0%",
        "files": ["tools/learner_refit.py", "learner.py"],
        "tests": ["test_learner_refit.py::TestFitVaKiemDinh::test_khong_tin_hieu_thi_TRUNG_TINH_va_khong_chan",
                  "test_learner_refit.py::TestFitVaKiemDinh::test_co_tin_hieu_thi_KHONG_trung_tinh",
                  "test_learner_refit.py::TestFitVaKiemDinh::test_write_ghi_file_dung_dang_va_co_backup"],
    },
    {
        "code": "B-036", "kind": "van-hanh", "seen": "01/11/2026",
        "title": "Hang doi cau hoi bi SPAM: 1 cau hoi Y NGUYEN duoc them lai moi gio (LIVE 90 dong OPEN, 88 dong trung)",
        "symptom": "`logs/ops_questions.json` cua LIVE co **90 cau OPEN** (01/11), trong do **88 dong Y NGUYEN**: 'LIVE: 1 cap lenh bao ve TRUNG -> gom lai (python tools/orders_audit.py --dedupe)' — 1 cau/gio trong 4,5 ngay (id 1..90). Hau qua: nguoi van hanh KHONG doc duoc hang doi; hoi dong bi hoi lai cung 1 cau (`council_outbox`: 'Co 1 cau hoi van hanh ton dong qua 24 gio'); `ops_queue --check` bao 'ton dong' lien tuc nen canh bao that bi lan voi nhieu",
        "guard": "`tools/ops_queue.add()` CHONG TRUNG: cau hoi Y NGUYEN dang OPEN ⇒ KHONG them dong moi, chi tang `n_repeat` + cap nhat `last_ts` (giu `ts` GOC nen quy tac 'ton dong > 24h' van dung); da tra loi ⇒ duoc hoi LAI; CLI `list` hien '(lap xN)'",
        "files": ["tools/ops_queue.py"],
        "tests": ["test_ops_tools.py::TestOpsQueue::test_cau_hoi_TRUNG_thi_khong_them_dong_moi",
                  "test_ops_tools.py::TestOpsQueue::test_cau_hoi_da_tra_loi_thi_duoc_hoi_LAI"],
    },
    {
        "code": "B-037", "kind": "van-hanh", "seen": "01/11/2026",
        "title": "BAO DONG GIA 'pid KHONG chay' khi `tasklist` loi (set() rong bi hieu la 0 pid)",
        "symptom": "Hang doi LIVE co 2 cau bao dong SAI sinh lech nhau 0,4 giay: 'supervisor pid 91852 KHONG chay' + 'tien trinh con pid 44840 KHONG chay' — trong khi `Get-CimInstance` cho thay CA HAI pid VAN SONG (pythonw.exe `run_forever.py` + `turbo_demo.py`). Nguyen nhan: `list_pids()` bat loi roi tra `set()` RONG, ma `health()` kiem 'pid co nam trong tap' ⇒ tap rong = 'khong pid nao dang chay' ⇒ bao dong cho MOI pid. Kem theo: `build_report` goi `len(pids)` ⇒ `len(None)` = TypeError neu doi sang None",
        "guard": "`list_pids()` loi ⇒ tra `None` = KHONG BIET (khong doan bua); `health(pids=None)` BO QUA phan kiem pid; `build_report` tra them `pids_known` va khong goi `len(None)`",
        "files": ["tools/watch_regress.py"],
        "tests": ["test_watch_regress.py::TestListPidsAnCuaSo::test_tasklist_loi_thi_tra_None_chu_khong_phai_set_rong",
                  "test_watch_regress.py::TestHealth::test_khong_biet_pid_thi_KHONG_bao_dong_gia",
                  "test_watch_regress.py::TestHealth::test_build_report_khi_khong_biet_pid_thi_khong_crash"],
    },
    {
        "code": "B-038", "kind": "ai", "seen": "01/11/2026",
        "title": "Test do NGAY thay vi do CODE: assert trang thai `.env` (copilot bi chan theo ngay) ⇒ tu dong do khi moc chan het han",
        "symptom": "Sang thang 11 (01/11) suite bao `FAIL: test_hau_to_cli_duoc_bo` — nhung CODE khong doi. Nguyen nhan: test assert `AG._provider_blocked('copilot', Settings())` la TRUTHY, tuc la dua vao `AGENT_COUNCIL_COPILOT_UNTIL` trong `.env`; moc chan cu (31/10) HET HAN dung luc sang thang ⇒ ham tra '' ⇒ test do. Hau qua: suite do theo LICH, khong theo ma — dung lop loi 'test do nhieu nen nguoi ta bo qua test'",
        "guard": "Test dung cfg GIA (`SimpleNamespace(agent_council_copilot_until=<ngay tuong lai>)`) + xoa trang thai session `_PROVIDER_BLOCKED` ⇒ do dung Y DINH (chuan hoa hau to `_cli`) va KHONG phu thuoc `.env`/ngay",
        "files": ["tests/test_agent_authority.py"],
        "tests": ["test_agent_authority.py::TestChuanHoaTenProvider::test_hau_to_cli_duoc_bo"],
    },
    {
        "code": "B-039", "kind": "van-hanh", "seen": "01/11/2026",
        "title": "Lenh bao ve TRUNG chi duoc BAO (hoi) chu khong TU GOM ⇒ hoi lap moi gio du tinh trang la ANH CHUP CU",
        "symptom": "Hang doi LIVE co cau 'LIVE: 1 cap lenh bao ve TRUNG -> gom lai' voi `n_repeat=4` (truoc khi va B-036 la 88 dong rieng); trong khi `orders_audit --target live --dedupe` xac nhan **giu 2, huy 0** ⇒ KHONG co gi de sua. Hau qua: nguoi van hanh bi hoi lien tuc ve 1 tinh trang khong con ton tai (quyet dinh 01/11: 'lenh neu trung bo qua lam cap giao dich khac')",
        "guard": "`watch_regress.auto_dedupe()` + `apply_auto_dedupe()`: watcher (task `ATB-WatchRegress` moi 10 phut) TU chay `orders_audit --target <t> --dedupe` khi thay cap TRUNG; thanh cong ⇒ BO van de khoi bao cao (khong hoi nua); THAT BAI ⇒ giu van de (khong im lang). Tat bang `--no-auto-dedupe`",
        "files": ["tools/watch_regress.py"],
        "tests": ["test_watch_regress.py::TestTuGomLenhTrung"],
    },
    {
        "code": "B-035", "kind": "ai", "seen": "06/11/2026",
        "title": "Ten model trong journal bi CHIA NHO (cung 1 model, nhieu ten) ⇒ bang diem EVAL vo nghia va de xuat bo model 'oan'",
        "symptom": "Do that tren journal TESTNET 06/11: `local/llama3.2:3b` **83 phieu** va `local/llama3.2-3b-local` **73 phieu** la CUNG mot model (tag ollama vs alias llamafile); `mimo-v2.6-pro` **77** vs `cline-pass/mimo-v2.6-pro` **105** cung vay; `qwen/cline-pass/qwen3.7-plus` (tien to provider LAP); **135 ban ghi `model` RONG** va mot so ban ghi `model='None'`. Hau qua: `model_leaderboard` chia moi model thanh 2-3 dong, moi dong qua it mau (`min_n=8`) ⇒ nhieu dong roi vao `thin` (khong ket luan duoc), `skip_lines` de xuat bo 1 NUA model (quyet dinh dua tren so lieu bi cat), va `CLINE_SKIP_MODELS=,...` sinh phan tu rong",
        "guard": "`council_evals.normalize_model()` + `MODEL_CANON` (alias khai bao) + `CLINE_MODELS` (ten cline-pass da biet, tu them tien to) + `EMPTY_NAMES` (rong/None/'?' -> ''): bo tien to provider lap, them tien to thieu, gop alias local. Ap o CA noi DOC (`_model_of`, `model_leaderboard`, `skip_lines`) LAN noi GHI (`agents.AgentLayer.log_decision` ghi `model` chuan + giu `model_raw`). KHONG gop 2 model KHAC nhau (`claude-sonnet-5` ≠ `claude-sonnet-5.5`)",
        "files": ["council_evals.py", "agents.py"],
        "tests": ["test_council_evals.py::TestChuanHoaTenModel::test_local_tag_ollama_va_alias_llamafile_la_MOT_model",
                  "test_council_evals.py::TestChuanHoaTenModel::test_bo_tien_to_provider_bi_LAP",
                  "test_council_evals.py::TestChuanHoaTenModel::test_them_tien_to_cho_model_cline_pass_da_biet",
                  "test_council_evals.py::TestChuanHoaTenModel::test_ban_ghi_thieu_model_tra_RONG",
                  "test_council_evals.py::TestChuanHoaTenModel::test_hai_model_KHAC_nhau_khong_bi_gop",
                  "test_council_evals.py::TestChuanHoaTenModel::test_dong_skip_khong_con_phan_tu_rong",
                  "test_council_evals.py::TestChuanHoaTenModel::test_bang_diem_gop_hai_ten_cu_thanh_MOT_dong",
                  "test_council_evals.py::TestChuanHoaTenModel::test_ghi_journal_luu_ten_CHUAN_va_giu_ten_GOC"],
    },
    {
        "code": "B-040", "kind": "ai", "seen": "06/11/2026",
        "title": "Wrapper `.cmd` cua npm PHA dau nhay trong prompt ⇒ Copilot/Qwen CLI luon loi ⇒ cau dao TAT provider (hoi dong mat giong, tuong 'het quota')",
        "symptom": "Do that 06/11: goi dung provider cua bot (`agents.CopilotCliProvider`) tra `copilot CLI rc=255: 'VETO' is not recognized as an internal or external command, operable program or batch file` — chi 0,2s. Nguyen nhan: tren Windows `npm\\\\copilot.cmd` chuyen tiep tham so qua **cmd.exe**, ma cmd.exe pha dau nhay kep trong prompt JSON ⇒ chuoi `{\"action\":\"VETO\"}` bien thanh LENH SHELL. Moi cuoc goi that bai ⇒ 5 loi lien tiep ⇒ `AgentBudget` ghi `disabled_by['copilot']` ⇒ hoi dong mat 1 giong va nguoi van hanh tuong 'Copilot het quota' (dung lop loi B-023: loi bi hieu sai thanh nguyen nhan khac). Sau khi bypass: `node npm-loader.js -p ...` + `COPILOT_GITHUB_TOKEN` tu `.env` ⇒ tra `{\"action\":\"ALLOW\",\"confidence\":0.5}` trong **15,6s** (do that)",
        "guard": "`agents._npm_loader_cmd()`: neu bin resolve ra `.cmd`/`.bat` cua npm VA tim thay `node_modules/<pkg>/npm-loader.js` ⇒ doi sang `[node, npm-loader.js]` (argv truyen NGUYEN VEN, khong qua cmd.exe). Ap cho CA `CopilotCliProvider` va `QwenCliProvider`; khong tim thay loader ⇒ giu nguyen (khong lam hong cach cai khac/OS khac)",
        "files": ["agents.py"],
        "tests": ["test_agents.py::TestBypassWrapperNpm::test_wrapper_cmd_duoc_thay_bang_node_loader",
                  "test_agents.py::TestBypassWrapperNpm::test_qwen_cung_duoc_bypass",
                  "test_agents.py::TestBypassWrapperNpm::test_khong_tim_thay_loader_thi_giu_nguyen",
                  "test_agents.py::TestBypassWrapperNpm::test_khong_phai_cmd_thi_giu_nguyen",
                  "test_agents.py::TestBypassWrapperNpm::test_provider_copilot_dung_loader_khi_build_lenh"],
    },
    {
        "code": "B-041", "kind": "van-hanh", "seen": "06/11/2026",
        "title": "Agent AI bi TAT / het quota thang KHONG ai duoc bao — chi thay 'hoi dong im lang' ma khong biet vi sao",
        "symptom": "Do that 05–14/10: Copilot het quota thang (365 dong 'You have exceeded your monthly quota') ⇒ 5 loi lien tiep ⇒ cau dao TAT provider `copilot` ⇒ hoi dong mat 1 giong suot **9 ngay**. Khong co co che nao bao: `watch_regress` chi kiem nhip tim/tien trinh/vi the, khong doc `logs/agent_state.json` ⇒ nguoi van hanh chi thay 'hoi dong im lang' va phai tu doan (ton 2 phien dieu tra moi ra: quota + auto-disable + tran cuoc goi/ngay)",
        "guard": "`watch_regress.scan_instance()` doc `logs/agent_state.json` (`disabled`, `disabled_by`) + dem dong 'exceeded your monthly quota' trong 24h ⇒ `health()` bao thanh VAN DE (kem lenh go tay `python agents.py --reset-budget`), di qua dung duong canh bao cu (ops_queue + `regress_watch.log`)",
        "files": ["tools/watch_regress.py"],
        "tests": ["test_watch_regress.py::TestCanhBaoAgentHetQuota::test_provider_bi_cau_dao_tat_thi_bao",
                  "test_watch_regress.py::TestCanhBaoAgentHetQuota::test_tat_toan_cuc_thi_bao",
                  "test_watch_regress.py::TestCanhBaoAgentHetQuota::test_quota_trong_24h_thi_bao",
                  "test_watch_regress.py::TestCanhBaoAgentHetQuota::test_he_khoe_thi_khong_bao"],
    },
    {
        "code": "B-042", "kind": "im-lang", "seen": "06/11/2026",
        "title": "Cua so PowerShell MO COI (ngoai VS Code) treo ⇒ Windows bat popup 'The window is no longer responding' lien tuc",
        "symptom": "Nguoi van hanh bao popup 'Keep waiting / Reopen / Close' hien lien tuc + chup man hinh 1 cua so `powershell.exe` RONG (khong co lenh nao) nam ngoai VS Code. Nguyen nhan: moi lenh cua agent Cline sinh 1 shell moi; shell do (khong con viec) van mo cua so THAT, va khi message loop treo ⇒ Windows bat hop thoai 'not responding'. `terminal_hygiene` chi XOA shell ranh co parent `Code.exe`, khong dong toi cua so dang HIEN",
        "guard": "`terminal_hygiene.hide_stray_consoles()`: `EnumWindows` + `GetWindowThreadProcessId` + `tasklist` ⇒ an (`ShowWindow SW_HIDE`) cua so HIEN cua powershell/pwsh/cmd/conhost/OpenConsole/WindowsTerminal; chi an cua so console (khong cham VS Code/trinh duyet); co `--hide-consoles`, dry-run duoc, mac dinh TAT (opt-in) de khong an nham cua so nguoi dung dang dung",
        "files": ["tools/terminal_hygiene.py"],
        "tests": ["test_terminal_hygiene.py::TestAnCuaSoConsole::test_ham_khong_no_ra_va_tra_du_truong",
                  "test_terminal_hygiene.py::TestAnCuaSoConsole::test_run_once_bat_co_thi_an_cua_so",
                  "test_terminal_hygiene.py::TestAnCuaSoConsole::test_khong_bat_co_thi_KHONG_cham_cua_so"],
    },
    {
        "code": "B-043", "kind": "rui-ro", "seen": "06/11/2026",
        "title": "`MAX_POSITIONS>1` VO HIEU: da co 1 vi the thi CHAN MOI cap khac ⇒ bot chi vao lenh khi vi the cu cham TP/SL",
        "symptom": "Nguoi van hanh bao: 'chi treo 1 lenh, khong vao lenh cap khac, chi cho cap hien tai cham TP/SL'. Do that 06/11: `.env` ca 2 instance dat `MAX_POSITIONS=1` + `RISK_PER_TRADE_PCT=1.2` trong khi `MAX_TOTAL_RISK_PCT=1.6` (1 lenh da an 1.42% ⇒ lenh thu 2 vuot tran: `SKIP_RISK` x1669+); **LIVE `SKIP_MAX_POS` x2777** ('max positions 1 reached'). NANG HON: `PortfolioManager.can_open()` co luat cung `if self.positions and not allow_hedge_opposite: return False, 'single-best-setup'` — chan MOI cap khac **du co 4 slot**, nen tang `MAX_POSITIONS` mot minh KHONG sua duoc (phat hien khi doc code, khong phai doan)",
        "guard": "`can_open()`: 'single-best-setup' CHI con dung khi `max_positions <= 1`; nhieu slot ⇒ cho phep nhieu cap KHAC SYMBOL, tran tong risk van do `can_add_risk(MAX_TOTAL_RISK_PCT)` giu. `.env`: chia nho risk thay vi tang tong — TESTNET `MAX_POSITIONS=4` + `RISK_PER_TRADE=0.4` (4x0.4=1.6 = tran cu); LIVE `MAX_POSITIONS=3` + `RISK_PER_TRADE=0.6` + tran 3.0% (von 38 USDT: san bat notional toi thieu 5 USDT nen risk that 1 lenh ~0.65-1.2%)",
        "files": ["portfolio.py", "tests/test_bot.py"],
        "tests": ["test_bot.py::TestPortfolio::test_nhieu_slot_thi_cho_phep_cap_KHAC_symbol_B043",
                  "test_bot.py::TestPortfolio::test_1_slot_van_giu_single_best_setup",
                  "test_bot.py::TestPortfolio::test_trung_symbol_van_bi_chan",
                  "test_bot.py::TestPortfolio::test_che_do_hedge_van_chan_cung_chieu"],
    },
    {
        "code": "B-044", "kind": "van-hanh", "seen": "06/11/2026",
        "title": "San chan IP (`-1003` / `418 I'm a teapot`) nhung bot VAN quet moi vong ⇒ tu lam ban dai them",
        "symptom": "Do that LIVE 06/11: **367** dong `I'm a teapot` tu **16:33 den 23:20**; thong bao that: `{\"code\":-1003,\"msg\":\"Way too many requests; IP(222.253.53.82) banned until 1793987694544\"}` (bi chan toi ~00:55). Bot van gui hang tram request moi vong (40 cap x nhieu endpoint) ⇒ Binance tang thoi gian ban (2 phut -> 3 ngay) ⇒ cang chay cang lau hoi; kem theo `errors` cham tran 5 ⇒ kill-switch TRIP (LIVE dung trade han)",
        "guard": "`turbo_demo.parse_ban_until()` doc moc `banned until <ms>`; `set_api_ban()` ghi `logs/api_ban.json` (CHI TANG, atomic); vong lap thay moc ⇒ **bo qua vong quet** (`phase=api_ban`, ngu toi moc) va chi bao Telegram 1 lan. File hong ⇒ coi nhu KHONG bi chan (fail-open o day la dung: khong duoc lam bot dung mai)",
        "files": ["turbo_demo.py", "tests/test_api_ban.py"],
        "tests": ["test_api_ban.py::TestParseBanUntil::test_doc_moc_mili_giay",
                  "test_api_ban.py::TestParseBanUntil::test_doc_moc_giay",
                  "test_api_ban.py::TestParseBanUntil::test_khong_co_moc_thi_0",
                  "test_api_ban.py::TestApiBanFile::test_ghi_va_doc",
                  "test_api_ban.py::TestApiBanFile::test_khong_ghi_lui",
                  "test_api_ban.py::TestApiBanFile::test_moc_0_thi_khong_ghi",
                  "test_api_ban.py::TestApiBanFile::test_file_hong_thi_coi_nhu_KHONG_chan"],
    },
    {
        "code": "B-045", "kind": "du-lieu", "seen": "09/11/2026",
        "title": "Journal KHONG co ma ly do may doc duoc + khong co khoa noi PHIEU hoi dong voi LENH ⇒ moi bao cao \"vi sao bi chan\" va \"model nao dung\" deu la doan",
        "symptom": "Do that tren `logs/journal.jsonl` (7.071 dong): **0** truong `reason_code` (moi ly do la van ban tu do `reasons:[\"...\"]`/`reason=\"tran risk...\"`), va **0** khoa chung giua ban ghi `AGENT` (phieu) va `OPEN` (lenh) ⇒ `tools/council_eval.py` phai ghep theo (symbol, huong, cua so 1 gio) va chi ghep duoc **31/133** phieu (23%) — bang diem 7 model dua tren qua it mau de ket luan. Kem theo: `brier 0.341` (>0.25 = doan bua), hoi dong khai 83% trong khi chi thang 57%, va KHONG co co che nao chan dieu do (prompt chi la loi nhac)",
        "guard": "`reason_codes.py`: 40 ma / 7 nhom + `STATUS_CODES` (status that cua vong quet -> ma) + `code_for_status()` + `new_id()`; `turbo_demo.turbo_round()` gan ma cho MOI ket qua o MOT cho (cuoi vong) va ghi `decision_id` + `reason_code` vao ban ghi `OPEN`; `agent_vote_setup`/`agent_veto` truyen cung `decision_id` vao moi phieu `AGENT`; `agents.log_decision` tu suy ma tu van ban neu noi goi khong truyen; `council_evals.pair_cases` uu tien ghep theo `decision_id` (chinh xac) va bao `match_stats()` tach \"chinh xac\" khoi \"doan\"; `agents.cap_confidence` + `evidence_n` ha confidence xuong <=0.7 khi n<20 mau bang chung (env `AGENT_CALIB_CAP`/`AGENT_CALIB_N_FULL`/`AGENT_CALIB_MAX_CONF`)",
        "files": ["reason_codes.py", "turbo_demo.py", "agents.py", "council_evals.py",
                  "config.py", "tests/test_reason_codes_wiring.py"],
        "tests": ["test_reason_codes_wiring.py::TestStatusMap::test_moi_ma_trong_bang_deu_ton_tai",
                  "test_reason_codes_wiring.py::TestStatusMap::test_status_that_trong_turbo_round_deu_co_ma",
                  "test_reason_codes_wiring.py::TestStatusMap::test_2019_la_order_reject_khong_phai_thieu_du_lieu",
                  "test_reason_codes_wiring.py::TestPairByDecisionId::test_ghep_dung_nho_decision_id_ngoai_cua_so",
                  "test_reason_codes_wiring.py::TestPairByDecisionId::test_phieu_bi_chan_thi_KHONG_gan_bua_vao_lenh",
                  "test_reason_codes_wiring.py::TestCalibration::test_ha_tran_khi_mau_it",
                  "test_reason_codes_wiring.py::TestVoteLogsReasonCode::test_log_decision_tu_suy_ma_tu_van_ban",
                  "test_agents.py::TestCouncil::test_co_bang_chung_du_thi_khong_ha_tran",
                  "test_council_evals.py::TestNoiTheoId::test_lenh_chua_dong_van_NOI_duoc_theo_id",
                  "test_council_evals.py::TestNoiTheoId::test_lenh_da_dong_thi_ghep_CHINH_XAC",
                  "test_council_evals.py::TestNoiTheoId::test_phieu_co_id_nhung_lenh_dung_id_KHAC_thi_khong_ban_noi"],
    },
    {
        "code": "B-046", "kind": "du-lieu", "seen": "09/11/2026",
        "title": "\"Test xanh\" KHONG co nghia la \"hanh vi khong doi\": thieu bo ca CO DINH co dap an ⇒ sua code lam doi quyet dinh ma khong ai biet",
        "symptom": "Truoc 09/11 repo co `tests/` (test tung ham, khang dinh dieu MINH viet ra) va `council_eval` (do theo KET QUA that) nhung KHONG co bo ca co dinh de tra loi \"ban moi co lam MAT hanh vi cu khong\". Do that ngay khi lam harness: chinh harness co 2 loi (gop `must`/`must_not` ⇒ `must_not` bi DAO NGHIA; `extract_features` co 2 tham so bat buoc ⇒ ca \"trung tinh\" nem `TypeError`) ma **khong** test nao bat duoc, chi ca FAIL bat duoc. Them nua: 4 tinh huong tai lieu neu (tam dung vao lenh / chan IP / kill-switch / doi sang LIVE) hoan toan khong duoc do hanh vi",
        "guard": "`tools/golden_build.py` sinh `golden/cases.jsonl` (40 ca: normal 15 / edge 13 / failure 12) phu **13 cong**, ca goi THANG ham that (`extract_features`, `OnlineLearner.edge`, `classify_strategy`, `gate_check`, `gate_list`, `can_add_risk`, `can_open`, `entries_gate.paused`, `parse_ban_until`, `KillSwitch.check`, `decide_go_live`, `council_eval.readiness`) + doc `feats` that trong journal; `tools/golden_set.py` so `sha1(output)` voi `golden/baseline.json` ⇒ `--check` exit 1 ca khi ca van \"xanh\" nhung HANH VI DOI (DRIFT) — thu `tests/` khong lam duoc",
        "files": ["tools/golden_set.py", "tools/golden_build.py", "golden/cases.jsonl",
                  "golden/baseline.json", "tests/test_golden_set.py"],
        "tests": ["test_golden_set.py::TestRuleEngine::test_must_va_must_not",
                  "test_golden_set.py::TestRunner::test_doi_dap_an_thi_ca_FAIL",
                  "test_golden_set.py::TestRunner::test_component_la_KHONG_bo_qua",
                  "test_golden_set.py::TestBaseline::test_drift_khi_output_doi",
                  "test_golden_set.py::TestBoCa::test_phu_het_cac_cong",
                  "test_golden_set.py::TestJournalThat::test_bat_feats_thieu_key_va_ngoai_dai"],
    },
    {
        "code": "B-047", "kind": "du-lieu", "seen": "09/11/2026",
        "title": "Tai lieu lech code (so lieu, ten tool, ma ly do) va digest DRIFT tinh ca so lieu tam thoi ⇒ bao dong gia, drift that bi chim",
        "symptom": "Trong 1 ngay lam viec, tai lieu lech code **3 lan** (31->38 ma ly do, 26->45 ca golden, 43->45 lop bug catalog) — moi lan chi do NGUOI tinh co phat hien; **6 tool** trong `tools/` khong duoc tai lieu nao nhac ten. DONG THOI golden set bao DRIFT gia moi ngay: ca `jrn-feats-integrity` doc journal THAT nen digest gom `n_checked`/`n_open_rows` (so nay TANG theo du lieu) ⇒ `--check` exit 1 du hanh vi khong doi",
        "guard": "`tools/drift_docs.py`: so khop tung 'loi khai' trong tai lieu (regex) voi gia tri TINH TU CODE (`len(reason_codes.CODES)`, so ca/cong golden, so lop/test bug catalog), kiem moi `tools/*.py` phai duoc nhac ten, bat ma ly do go sai bang khoang cach sua <= 2 (mien tru bien moi truong doc tu `config.py`); muc `warn` (ma lop loi lich su) khong chan commit. `tools/golden_set.py`: digest DRIFT chi tinh tren `_contract_view()` = cac key DA KHAI trong `expect.output` ⇒ so lieu tam thoi tang khong con lam bao dong gia",
        "files": ["tools/drift_docs.py", "tools/golden_set.py", "tests/test_selfops.py",
                  "tests/test_golden_set.py"],
        "tests": ["test_selfops.py::TestDriftDocs::test_so_lieu_lech_bi_bao",
                  "test_selfops.py::TestDriftDocs::test_tai_lieu_doi_cau_chu_lam_mat_dau_vet_cung_la_LECH",
                  "test_selfops.py::TestDriftDocs::test_bien_moi_truong_khong_bi_bao_nham",
                  "test_selfops.py::TestDriftDocs::test_report_that_tren_repo_phai_sach",
                  "test_golden_set.py::TestDigestHopDong::test_contract_view_bo_key_khong_khai",
                  "test_golden_set.py::TestDigestHopDong::test_so_lieu_khong_khai_TRONG_digest_thi_khong_bao_drift"],
    },
    {
        "code": "B-048", "kind": "van-hanh", "seen": "09/11/2026",
        "title": "Hoi dong KHONG tu biet minh thieu gi va khong tu van hanh duoc ⇒ moi buoc phai cho nguoi, hoac (neu cho tu do) se tu dong vao state cua tai khoan THAT",
        "symptom": "Do that 09/11: `brier 0.3467` (>0.25), ghep phieu->lenh **0% chinh xac** (chua co `decision_id`), 11 model chua du mau, 1 model `value_r <= 0` — nhung khong co ban danh sach nao noi 'dang thieu gi'. Neu cho he thong tu xu ly khong gioi han thi buoc tiep theo la tu restart / tu go kill-switch tren LIVE (tai khoan that) — rui ro lon hon loi no dinh sua",
        "guard": "`tools/council_gaps.py`: moi thieu hut sinh TU SO LIEU (khong phai y kien), bat buoc co `metric`/`value`/`target`/`needs`/`action`/`auto`; xuat `COUNCIL_GAPS.md` (ke hoach tu hoc) + `logs/council_gaps.json`. `tools/selfops.py`: `plan()` THUAN TUY tu state + gaps; `run()` mac dinh DRY-RUN, moi viec ghi `logs/autonomy.jsonl` (ly do + bang chung + rc); CHAN CUNG: viec dung vao state (`restart`, `kill_reset`) khong tu chay tren LIVE tru khi `--allow-live-state`, va tren TESTNET chi tu go kill-switch khi da sang ngay UTC + khong con vi the; refit learner chi khi du mau va da >= 12 gio (moc lay tu nhat ky, vi refit ket luan 'trung tinh' thi khong ghi file)",
        "files": ["tools/council_gaps.py", "tools/selfops.py", "tests/test_selfops.py"],
        "tests": ["test_selfops.py::TestGaps::test_so_lieu_tot_thi_KHONG_bao_thieu_hut",
                  "test_selfops.py::TestGaps::test_moi_thieu_hut_phai_co_needs_va_action",
                  "test_selfops.py::TestSelfOps::test_live_state_bi_chan_khi_chua_cho_phep",
                  "test_selfops.py::TestSelfOps::test_chi_tu_go_kill_switch_khi_flat_va_sang_ngay_moi",
                  "test_selfops.py::TestSelfOps::test_dry_run_khong_chay_gi",
                  "test_selfops.py::TestSelfOps::test_refit_chi_khi_du_mau_va_da_lau"],
    },
    {
        "code": "B-049", "kind": "rui-ro", "seen": "09/11/2026",
        "title": "Tran TONG risk tinh tren mau so KHAC goc von voi tu so (equity san vs size_base) ⇒ tran 1,6% cho phep 12-13 vi the; MAX_POSITIONS lai bi bypass o DEMO nen khong con chot nao",
        "symptom": "Do that TESTNET 09/11: journal co **13 lenh OPEN trong 45 giay** (09:27:41 → 09:28:07), tren san con **20 vi the** (12 bot quan ly + 8 mo tay/dust) va moi entry sau do bi `SKIP_RISK`: \"tran risk danh muc: dang 1,59% + moi 0,13% > 1,60%\". Vi sao lot: `position_size()` tinh risk tren `bot.balance = min(BALANCE_USDT, equity)` = **1000** (moi lenh 4 USDT = 0,4%) nhung `can_add_risk()` duoc goi voi `bot.equity` THAT cua vi demo (**~3000**) ⇒ moi lenh chi con **0,13%** ⇒ tran 1,6% cho phep ~12 vi the thay vi 4. Chot thu hai (`max_positions_block`) **co y bo qua o DEMO** nen khong co gi chan lai",
        "guard": "`portfolio.risk_cap_base(balance, equity)` = `min(balance, equity)` — dung CUNG goc von voi tu so; `turbo_demo` truyen `_cap_base` vao CA HAI cho goi `can_add_risk` (truoc va sau khi nang qty len minNotional) va ghi `cap_base` vao ket qua `SKIP_RISK` de doc duoc bang so. Test chot **SO VI THE TOI DA** (khong chi chot gia tri ham): mo phong mo lien tiep ⇒ **4** vi the voi `risk_cap_base`, va **12** neu dung mau so cu (giu lai lam bang chung loi)",
        "files": ["portfolio.py", "turbo_demo.py", "tests/test_risk_cap_base.py"],
        "tests": ["test_risk_cap_base.py::TestRiskCapBase::test_SO_VI_THE_TOI_DA_la_4_khong_phai_12",
                  "test_risk_cap_base.py::TestRiskCapBase::test_mau_so_bang_size_base_khi_equity_lon_hon",
                  "test_risk_cap_base.py::TestRiskCapBase::test_equity_nho_hon_balance_thi_lay_equity",
                  "test_risk_cap_base.py::TestRiskCapBase::test_thieu_du_lieu_thi_khong_chia_cho_0",
                  "test_risk_cap_base.py::TestRiskCapBase::test_risk_moi_lenh_dung_bang_risk_pct_cua_size_base"],
    },
    {
        "code": "B-050", "kind": "du-lieu", "seen": "09/11/2026",
        "title": "So sach noi LAI trong khi vi LO: journal khong tach duoc lenh do BOT mo khoi lenh do NGUOI dat tay ⇒ kill-switch trip bi hieu sai la \"chien luoc thua\"",
        "symptom": "LIVE 09/11: vi that **27,90 USDT** (dinh 38,44), kill-switch trip \"daily loss 28,31%\", nhung doc journal thi **675 dong CLOSE co tong pnl +124,50** (duong) — neu tin journal se ket luan nguoc han. Doi chieu **fill that tren san** (7 ngay, 720 fill): **102 vong lenh**, chi **3** khop `OPEN` trong journal, **99 vong KHONG co OPEN** = nguoi dat tay, PnL **-4,61 USDT**; bot **0** vong trong cua so. Dong thoi 1 `CLOSE` bi thieu (1000CAT 05/11) va 1 vi the ETH **mo tay** nam ngoai `managed_state` (bot khong dat SL/TP)",
        "guard": "`reconcile.py` (da co tu P0) duoc dung nhu BUOC BAT BUOC khi so sanh tien: `plan_backfill()` giu **2 ngan rieng** — `closes` (khop OPEN trong journal = bot) va `unmatched_episodes` (khong co OPEN = tay); `--apply` chi ghi bu `CLOSE` thieu (backup `journal.jsonl.bak-*`), KHONG sua `risk_state`, KHONG gui lenh. Quy trinh ghi vao `OPERATIONS.md`: doi soat `reconcile.py` + `positions.py` TRUOC khi ket luan ve chien luoc hay go kill-switch; phan biet ro `journal.pnl` (lich su ghi chep) vs `equity` (su that duy nhat)",
        "files": ["reconcile.py", "positions.py", "OPERATIONS.md", "tests/test_reconcile.py"],
        "tests": ["test_reconcile.py::TestTachLenTayVaBot::test_hai_ngan_rieng_bot_va_tay",
                  "test_reconcile.py::TestTachLenTayVaBot::test_pnl_tung_ngan_khop_fill_that",
                  "test_reconcile.py::TestTachLenTayVaBot::test_khong_co_fill_thi_khong_suy_dien"],
    },
]


def _strip_accents(s: str) -> str:
    """Bo dau tieng Viet de tim kiem khong phu thuoc cach go."""
    out = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                  if unicodedata.category(c) != "Mn")
    return out.replace("\u0111", "d").replace("\u0110", "D")


def norm(s: str) -> str:
    return _strip_accents(s).lower()


def graph(catalog=None, tests_dir=None) -> dict:
    """So do `hanh vi -> file -> test` (nodes/edges) — ban dich nho cua "honeycomb" (§15.3).

    Vi sao: REPO_IDEAS ghi "chua co graph hanh vi <-> ma". Du lieu DA CO ngay trong danh muc
    nay (bug -> file -> test) => sinh duoc so do ma KHONG phai khai bao tay (khong lech thuc te).
    """
    idx = test_index(tests_dir)
    nodes: dict = {}
    edges: list = []

    def nid(prefix: str, name: str) -> str:
        return prefix + re.sub(r"\W+", "_", str(name)).strip("_")

    for c in (CLASSES if catalog is None else catalog):
        b = nid("", c.get("code"))            # "B-021" -> "B_021"
        nodes[b] = {"id": b, "kind": "behavior", "label": "%s %s" % (c.get("code"), c.get("title"))}
        for f in (c.get("files") or []):
            fn = nid("F_", f)
            nodes[fn] = {"id": fn, "kind": "file", "label": f}
            edges.append([b, fn])
            for t in (c.get("tests") or []):
                tn = nid("T_", t)
                ok = t in idx["refs"] or t in idx["files"]
                nodes[tn] = {"id": tn, "kind": "test", "label": t, "exists": ok}
                edges.append([fn, tn])
    return {"nodes": sorted(nodes.values(), key=lambda x: x["id"]), "edges": edges,
            "n_behavior": sum(1 for n in nodes.values() if n["kind"] == "behavior"),
            "n_file": sum(1 for n in nodes.values() if n["kind"] == "file"),
            "n_test": sum(1 for n in nodes.values() if n["kind"] == "test")}


def graph_md(catalog=None, tests_dir=None) -> list:
    """So do dang Mermaid (dan duoc vao tai lieu/PR) + bang 'hanh vi -> test'."""
    g = graph(catalog, tests_dir)
    out = ["```mermaid", "graph LR"]
    for n in g["nodes"]:
        if n["kind"] == "behavior":
            out.append('  %s["%s"]' % (n["id"], str(n["label"])[:46]))
    for e in g["edges"]:
        a, b = e
        if a.startswith("B_"):
            out.append("  %s --> %s" % (a, b))
    out += ["```", "", "| Hanh vi (lop loi) | File | Test chot |", "|---|---|---|"]
    for c in (CLASSES if catalog is None else catalog):
        out.append("| %s %s | %s | %s |"
                   % (c.get("code"), str(c.get("title"))[:60],
                      ", ".join("`%s`" % f for f in (c.get("files") or [])),
                      "<br>".join("`%s`" % t for t in (c.get("tests") or []))))
    out += ["", "_Sinh tu `tools/bug_catalog.py --graph` (%d hanh vi / %d file / %d test)._"
            % (g["n_behavior"], g["n_file"], g["n_test"])]
    return out


def test_index(tests_dir=None) -> dict:
    """Doc `tests/` -> {'refs': {...}, 'files': {...}} (refs dang `file.py::Class::test`)."""
    d = Path(tests_dir or (ROOT / "tests"))
    files: set = set()
    refs: set = set()
    try:
        paths = sorted(d.glob("test_*.py"))
    except OSError:
        return {"refs": refs, "files": files}
    for p in paths:
        files.add(p.name)
        cls = ""
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ln in text.splitlines():
            m = re.match(r"class (\w+)", ln)
            if m:
                cls = m.group(1)
                refs.add("%s::%s" % (p.name, cls))
            m2 = re.match(r"\s+def (test_\w+)", ln)
            if m2 and cls:
                refs.add("%s::%s::%s" % (p.name, cls, m2.group(1)))
    return {"refs": refs, "files": files}


def check(catalog=None, tests_dir=None) -> dict:
    """Xac minh moi `tests` trong danh muc CO THAT. Tra {ok, n, pinned, missing, no_test}."""
    idx = test_index(tests_dir)
    missing: list = []
    no_test: list = []
    pinned = 0
    items = list(CLASSES if catalog is None else catalog)
    for c in items:
        refs = list(c.get("tests") or [])
        if not refs:
            no_test.append(str(c.get("code") or c.get("title")))
            continue
        for r in refs:
            if r in idx["refs"] or r in idx["files"]:
                pinned += 1
            else:
                missing.append("%s -> %s" % (c.get("code"), r))
    return {"ok": not missing and not no_test, "n": len(items), "pinned": pinned,
            "missing": missing, "no_test": no_test, "tests_scanned": len(idx["files"])}


def find(catalog=None, text: str = "") -> list:
    """Tim lop loi theo trieu chung/ten/cach chan (bo dau, khong phan biet hoa thuong)."""
    q = norm(text)
    items = list(CLASSES if catalog is None else catalog)
    if not q:
        return items
    out = []
    for c in items:
        hay = norm(" ".join([str(c.get("code")), str(c.get("title")), str(c.get("symptom")),
                             str(c.get("guard")), str(c.get("kind")),
                             " ".join(c.get("files") or [])]))
        if q in hay:
            out.append(c)
    return out



def table(items: list) -> list:
    """Bang tom tat (list dong) — gon de doc trong terminal/Telegram."""
    lines = ["%-6s %-9s %-5s %s" % ("MA", "LOAI", "TEST", "LOP LOI")]
    for c in items:
        lines.append("%-6s %-9s %-5d %s"
                     % (c.get("code"), c.get("kind"), len(c.get("tests") or []),
                        str(c.get("title"))[:78]))
    return lines


def detail(c: dict) -> list:
    """Chi tiet 1 lop loi (kem test chot + file lien quan)."""
    out = ["%s  [%s]  %s" % (c.get("code"), c.get("kind"), c.get("title")),
           "  Gap that : %s" % c.get("seen", "?"),
           "  Nhan ra  : %s" % c.get("symptom"),
           "  Chan bang: %s" % c.get("guard"),
           "  File     : %s" % ", ".join(c.get("files") or []),
           "  Test chot:"]
    out += ["    - %s" % t for t in (c.get("tests") or ["(CHUA CO TEST — phai bo sung)"])]
    return out


def main(argv: list | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Danh muc lop loi + test chot")
    ap.add_argument("--grep", default="", help="tim theo trieu chung / ten / cach chan")
    ap.add_argument("--kind", default="", help="loc theo loai: %s" % ", ".join(KINDS))
    ap.add_argument("--code", default="", help="chi tiet 1 ma (vd B-003)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--graph", action="store_true",
                    help="so do 'hanh vi -> file -> test' (mermaid + bang)")
    ap.add_argument("--check", action="store_true",
                    help="xac minh moi test duoc dan CO THAT (exit 1 neu thieu)")
    args = ap.parse_args(argv)

    if args.graph:
        if args.json:
            print(json.dumps(graph(), ensure_ascii=False, indent=1))
        else:
            print("\n".join(graph_md()))
        return 0

    if args.check:
        rep = check()
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print("=== KIEM TRA BUG CATALOG | %d lop | %d test chot | %d file test ==="
                  % (rep["n"], rep["pinned"], rep["tests_scanned"]))
            if rep["no_test"]:
                print("  LOP LOI CHUA CO TEST: %s" % ", ".join(rep["no_test"]))
            if rep["missing"]:
                print("  TEST BI THIEU (lop loi mat chot chan):")
                for m in rep["missing"]:
                    print("    - %s" % m)
            print("  KET LUAN: %s" % ("OK" if rep["ok"] else "CAN SUA"))
        return 0 if rep["ok"] else 1

    items = find(text=args.grep)
    if args.kind:
        items = [c for c in items if str(c.get("kind")) == args.kind]
    if args.code:
        items = [c for c in items if str(c.get("code")).upper() == args.code.upper()]
        if not items:
            print("khong co ma %s" % args.code)
            return 2
    if args.json:
        print(json.dumps({"n": len(items), "kinds": KINDS, "items": items},
                         ensure_ascii=False, indent=1))
        return 0
    print("=== DANH MUC LOP LOI | %d muc (grep=%r kind=%r) ==="
          % (len(items), args.grep, args.kind))
    if args.code:
        for c in items:
            print("\n".join(detail(c)))
    else:
        for ln in table(items):
            print(ln)
        print("\nLOAI: " + " · ".join("%s = %s" % (k, v) for k, v in KINDS.items()))
        print("Chi tiet: `python tools/bug_catalog.py --code B-00X` · "
              "kiem tra: `python tools/bug_catalog.py --check`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

