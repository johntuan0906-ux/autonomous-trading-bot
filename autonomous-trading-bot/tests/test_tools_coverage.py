"""Test phu cho cac TOOL trong `tools/` ma `python tools/capabilities.py --check` bao
"khong duoc test" (19/10).

Vi sao: manifest nang luc (y tuong tu HKUDS/CLI-Anything) chi co gia tri neu moi tool co
harness rieng. Cac tool o day la loai de "im lang": chan doan (diag/probe), doi cau hinh
(switch_local_model/setup_parallel_env), watcher (wait_btw_isolate) — dung lop loi da lam
he thong chay sai ma khong ai biet.

Tat ca deu chay OFFLINE (khong goi mang): dung stub provider / thu muc tam / monkeypatch.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _silent(fn, *a, **kw):
    """Chay `fn` va tra (ket qua, stdout) — test khong lam ban output."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a, **kw)
    return rc, buf.getvalue()


class TestInstanceEnv(unittest.TestCase):
    """`tools/instance_env.py` — chan doan `.env` file vs OS env vs `Settings()`."""

    def test_che_key_khong_lo_bi_mat(self):
        import instance_env as IE
        self.assertEqual(IE._mask("ngan"), "ngan")
        m = IE._mask("abcdefghijklmnopqrst")
        self.assertTrue(m.startswith("abcdef"))
        self.assertTrue(m.endswith("qrst"))
        self.assertIn("...", m)

    def test_doc_env_bo_comment_va_thieu_file(self):
        import instance_env as IE
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("# ghi chu\nA=1\n\nB=2\n", encoding="utf-8")
            env = IE.read_env_file(p)
            self.assertEqual(env.get("A"), "1")
            self.assertEqual(env.get("B"), "2")
            self.assertNotIn("# ghi chu", env)
            self.assertEqual(IE.read_env_file(Path(d) / "khong-ton-tai"), {})

    def test_report_tra_ve_bien_thuc_te(self):
        """`report()` doc THAT repo: phai co BINANCE_TESTNET/LIVE_CONFIRM + khong crash."""
        import instance_env as IE
        rep = IE.report(ROOT)
        keys = {str(r.get("key")) for r in (rep.get("rows") or [])}
        self.assertIn("BINANCE_TESTNET", keys)
        self.assertIn("LIVE_CONFIRM", keys)
        self.assertEqual(Path(str(rep.get("root") or "")).resolve(), ROOT.resolve(),
                         "report() phai doc dung goc repo (ten thu muc co the la atb-live)")
        self.assertTrue(all("overridden_by_os" in r for r in rep["rows"]))


class TestSwitchLocalModel(unittest.TestCase):
    """`tools/switch_local_model.py` — doi 3 dong cau hinh model local, phai IDEMPOTENT."""

    def _run(self, p, which):
        import switch_local_model as SLM
        old = sys.argv
        try:
            sys.argv = ["switch_local_model", str(p), which]
            return _silent(SLM.main)
        finally:
            sys.argv = old

    def test_doi_sang_llamafile_va_chay_lai_khong_sinh_dong_trung(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("A=1\nAGENT_LOCAL_BASE_URL=http://127.0.0.1:11434/v1\n"
                         "AGENT_LOCAL_BASE_URL=http://trung-lap/v1\n", encoding="utf-8")
            rc, _ = self._run(p, "llamafile")
            rc2, _ = self._run(p, "llamafile")
            txt = p.read_text(encoding="utf-8")
        self.assertEqual((rc, rc2), (0, 0))
        self.assertEqual(txt.count("AGENT_LOCAL_BASE_URL="), 1)     # bo dong trung lap
        self.assertIn("AGENT_LOCAL_BASE_URL=http://127.0.0.1:8080/v1", txt)
        self.assertIn("AGENT_COUNCIL_LOCAL=llama3.2-3b-local", txt)
        self.assertIn("A=1", txt)                                   # giu nguyen phan khac

    def test_doi_sang_ollama(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("A=1\n", encoding="utf-8")
            rc, _ = self._run(p, "ollama")
            txt = p.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertIn("AGENT_LOCAL_BASE_URL=http://127.0.0.1:11434/v1", txt)
        self.assertIn("AGENT_COUNCIL_LOCAL=llama3.2:3b", txt)


class TestSetupParallelEnv(unittest.TestCase):
    """`tools/setup_parallel_env.py` — tao `.env` cho 2 instance; `--dry-run` KHONG duoc ghi."""

    def test_mask_che_api_key(self):
        import setup_parallel_env as SPE
        self.assertIn("...", SPE.mask("BINANCE_API_KEY=abcdefghijklmno"))
        self.assertIn("(rong)", SPE.mask("BINANCE_API_SECRET="))
        self.assertEqual(SPE.mask("MAX_POSITIONS=2"), "MAX_POSITIONS=2")

    def test_dry_run_khong_sua_env_that(self):
        import setup_parallel_env as SPE
        envf = Path(SPE.ROOT) / ".env"
        before = envf.read_bytes()
        rc, out = _silent(SPE.main, ["--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("dry-run", out)
        self.assertEqual(envf.read_bytes(), before, "dry-run phai KHONG ghi file")



class TestLlamafileSetup(unittest.TestCase):
    """`tools/llamafile_setup.py` — ham thuan: doc /v1/models, chon runner, sinh dong `.env`."""

    def test_doc_danh_sach_model_va_chon_id(self):
        import llamafile_setup as LS
        self.assertEqual(LS.parse_models_response(
            '{"data":[{"id":"m1"},{"id":"default"}]}'), ["m1", "default"])
        self.assertEqual(LS.parse_models_response("{hong"), [])
        self.assertEqual(LS.pick_model_id(["default", "llama3.2-3b.gguf"]),
                         "llama3.2-3b.gguf")
        self.assertEqual(LS.pick_model_id([], fallback="x"), "x")

    def test_chon_runner_uu_tien_thin_khi_co_gguf(self):
        """Loi that 13/10: chon nham llamafile 0.8B tu chua trong khi da co GGUF 3B."""
        import llamafile_setup as LS
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            (dd / "model-3b.gguf").write_bytes(b"0" * 2048)
            (dd / "llamafile-thin.exe").write_bytes(b"0" * 512)
            b, g = LS.pick_runner(dd)
            self.assertEqual(g.name, "model-3b.gguf")
            self.assertIn("thin", b.name)
        with tempfile.TemporaryDirectory() as d2:
            (Path(d2) / "model-3b.llamafile").write_bytes(b"0" * 1024)
            b2, g2 = LS.pick_runner(Path(d2))
            self.assertIsNone(g2)
            self.assertEqual(b2.name, "model-3b.llamafile")
        self.assertEqual(LS.pick_runner(Path(tempfile.mkdtemp())), (None, None))
        self.assertEqual(LS.size_gb(Path(d2) / "khong-co"), 0.0)

    def test_env_lines_dung_port_va_model(self):
        import llamafile_setup as LS
        lines = LS.env_lines(port=8080, model="m-3b")
        self.assertIn("AGENT_COUNCIL_LOCAL=m-3b", lines)
        self.assertIn("AGENT_LOCAL_BASE_URL=http://127.0.0.1:8080/v1", lines)


class TestProbeClineStub(unittest.TestCase):
    """`tools/probe_cline.py` — probe phai phan biet OK / LOI va KHONG crash khi 1 model loi."""

    def test_probe_ok_va_loi(self):
        import agents as AG
        import probe_cline as PC

        class Stub:
            def __init__(self, model=""):
                self.api_model = "gui/" + str(model)

            def complete(self, *a, **k):
                return {"text": '{"action":"ALLOW","confidence":0.9,"reasons":["ok"]}'}

        class Bad(Stub):
            def complete(self, *a, **k):
                raise RuntimeError("500 boom")

        old = AG.ClineProvider
        try:
            AG.ClineProvider = Stub
            mid, api, good, secs, info = PC.probe("m1", timeout=1)
            self.assertEqual(mid, "m1")
            self.assertTrue(good)
            self.assertIn("ALLOW", info)
            self.assertEqual(api, "gui/m1")
            AG.ClineProvider = Bad
            mid2, _, good2, _, info2 = PC.probe("m2", timeout=1)
            self.assertFalse(good2)
            self.assertIn("500", info2)
        finally:
            AG.ClineProvider = old

    def test_danh_sach_model_mac_dinh_khong_rong(self):
        import probe_cline as PC
        self.assertTrue(PC.DEFAULT)
        self.assertTrue(all("/" not in str(m) or "-" in str(m) for m in PC.DEFAULT))


class TestProbeLocalJsonStub(unittest.TestCase):
    """`tools/probe_local_json.py` — goi model local that bai thi phai BAO RO, khong crash."""

    def test_loi_ket_noi_thi_tra_1_va_in_loi(self):
        import agents as AG
        import probe_local_json as PLJ

        class Boom:
            json_mode_used = "off"

            def __init__(self, **kw):
                pass

            def complete(self, *a, **k):
                raise RuntimeError("khong ket noi duoc")

        old = AG.OpenAICompatProvider
        try:
            AG.OpenAICompatProvider = Boom
            rc, out = _silent(PLJ.main, [])
        finally:
            AG.OpenAICompatProvider = old
        self.assertEqual(rc, 1)
        self.assertIn("LOI", out)

    def test_doc_duoc_json_thi_in_che_do_va_phieu(self):
        import agents as AG
        import probe_local_json as PLJ

        class Ok:
            json_mode_used = "schema"

            def __init__(self, **kw):
                pass

            def complete(self, *a, **k):
                return {"text": '{"action":"ALLOW","confidence":1.0,"reasons":[],'
                                '"risk_flags":[]}', "tokens_in": 105, "tokens_out": 38}

        old = AG.OpenAICompatProvider
        try:
            AG.OpenAICompatProvider = Ok
            rc, out = _silent(PLJ.main, ["--json"])
        finally:
            AG.OpenAICompatProvider = old
        self.assertEqual(rc, 0)
        idx = out.index("{")
        rep, _ = json.JSONDecoder().raw_decode(out[idx:])
        self.assertEqual(rep["json_mode_used"], "schema")
        self.assertEqual(rep["action"], "ALLOW")



class TestWaitBtwIsolate(unittest.TestCase):
    """`tools/wait_btw_isolate.py` — watcher: doc vi the (fail-safe), dat ISOLATED, ghi vet.

    Lop loi B-015: vi the do NGUOI mo khong duoc coi la cua bot; doc loi thi KHONG duoc
    ket luan "da phang" (neu khong watcher se mo lai cong sai luc).
    """

    class _Ex:
        def __init__(self, rows=None, err=None, mode_err=None):
            self.rows = rows or []
            self.err = err
            self.mode_err = mode_err
            self.calls = []

        def fetch_positions(self, syms=None):
            if self.err:
                raise RuntimeError(self.err)
            return self.rows

        def set_margin_mode(self, mode, symbol):
            self.calls.append((mode, symbol))
            if self.mode_err:
                raise RuntimeError(self.mode_err)
            return {}

    def test_position_qty_fail_safe(self):
        import wait_btw_isolate as W
        ex = self._Ex([{"symbol": "BTW/USDT:USDT", "contracts": 3.0}])
        self.assertEqual(W.position_qty(ex, "BTW/USDT:USDT"), 3.0)
        self.assertEqual(W.position_qty(ex, "btw/usdt:usdt"), 3.0)      # khong phan biet hoa
        self.assertEqual(W.position_qty(ex, "KHONG/USDT:USDT"), 0.0)    # khong co = phang
        self.assertIsNone(W.position_qty(self._Ex(err="mang loi"), "BTW/USDT:USDT"))
        self.assertIsNone(W.position_qty(self._Ex([{"symbol": "B", "contracts": "x"}]),
                                        "B"))

    def test_set_isolated_chiu_loi_da_dung_margin(self):
        import wait_btw_isolate as W
        ok = self._Ex()
        self.assertTrue(W.set_isolated(ok, "BTW/USDT:USDT"))
        self.assertEqual(ok.calls, [("isolated", "BTW/USDT:USDT")])
        self.assertTrue(W.set_isolated(
            self._Ex(mode_err="-4046 No need to change margin type"), "BTW/USDT:USDT"))
        self.assertFalse(W.set_isolated(self._Ex(mode_err="boom khac"), "BTW/USDT:USDT"))

    def test_ghi_vet_journal_va_log_theo_instance(self):
        import wait_btw_isolate as W
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            W.journal_append(dd, {"status": "PAUSE", "why": "vi du"})
            W.log(dd, "dong log thu")
            jl = (dd / "logs" / "journal.jsonl").read_text(encoding="utf-8").strip()
            lg = (dd / "logs" / "wait_btw_isolate.log").read_text(encoding="utf-8")
        rec = json.loads(jl)
        self.assertEqual(rec["event"], "OPS")          # KHONG lan voi AGENT/OPEN/CLOSE
        self.assertEqual(rec["status"], "PAUSE")
        self.assertIn("dong log thu", lg)


class TestDiagReview(unittest.TestCase):
    """`tools/diag_review.py` — chan doan 'vi sao review van goi provider da chet'."""

    def test_chay_duoc_va_in_ket_qua_guard(self):
        import diag_review as DR
        rc, out = _silent(DR.main)
        self.assertIn(rc, (0, 1))
        self.assertIn("CHAN DOAN REVIEW AGENT", out)
        self.assertIn("_provider_blocked(", out)       # phai kiem tra CA ten co/khong _cli


class TestLearnReviewCLI(unittest.TestCase):
    """`tools/learn_review.py` — CLI rut kinh nghiem; `--dry` KHONG duoc ghi file."""

    def test_dry_run_doc_duoc_journal(self):
        import learn_review as LR
        les = ROOT / "logs" / "lessons.json"
        before = les.read_bytes() if les.exists() else None
        rc, out = _silent(LR.main, ["--dry", "--target", "testnet"])
        self.assertEqual(rc, 0)
        self.assertIn("to hop", out)
        after = les.read_bytes() if les.exists() else None
        self.assertEqual(before, after, "--dry khong duoc ghi lessons.json")

    def test_target_live_doc_dung_instance(self):
        """(15/10) `--target live` phai doc journal cua `../atb-live`, khong phai repo chinh."""
        import learn_review as LR
        self.assertEqual(LR.LIVE_DIR.name, "atb-live")
        rc, out = _silent(LR.main, ["--dry", "--target", "live"])
        self.assertEqual(rc, 0)
        self.assertIn("to hop", out)



