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

