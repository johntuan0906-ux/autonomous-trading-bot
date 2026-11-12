# -*- coding: utf-8 -*-
"""B-051 — hội đồng abstain 100% vì TÊN MODEL KHÔNG CÓ TRONG GÓI (lỗi cấu hình, không phải mạng).

Đo thật 09/11 trên LIVE: log chỉ ghi `critic loi (...) -> NO_OPINION`, đọc kỹ mới thấy
`Error: Model "gemini-3.8-flash" from --model flag is not available.` — cả **15/15** tên
model trong tài liệu CLI đều bị chặn theo gói; chỉ `--model auto` chạy được (rc=0, 24 s).
Sau khi đổi `.env` sang `auto`: TESTNET `hoi dong 5 model: 0A/4V`, LIVE `5 model: 1A/4V`.

Khoá bằng test: bộ PHÂN LOẠI (để "im lặng" thành mã đọc được) + cách GHÉP LỆNH
(`{prompt}` phải là MỘT đối số — tách theo khoảng trắng thì CLI báo
"Invalid command format. It looks like your prompt was not quoted").
"""
from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import agents as A          # noqa: E402
import probe_cline as PC    # noqa: E402


class TestClassifyProviderError(unittest.TestCase):
    def test_model_bi_chan_theo_goi(self):
        msg = 'Error: Model "gemini-3.8-flash" from --model flag is not available.'
        self.assertEqual(A.classify_provider_error(1, msg), "MODEL_GATED")
        self.assertEqual(A.classify_provider_error(0, msg), "MODEL_GATED")

    def test_chua_dang_nhap(self):
        msg = "Error: No authentication information found."
        self.assertEqual(A.classify_provider_error(1, msg), "AUTH")

    def test_het_quota_thang_va_rate_limit(self):
        self.assertEqual(A.classify_provider_error(1, "You have exceeded your monthly quota"),
                         "QUOTA")
        self.assertEqual(A.classify_provider_error(1, "HTTP 429 Too Many Requests"), "RATE")

    def test_thanh_cong_va_loi_la(self):
        self.assertEqual(A.classify_provider_error(0, "OK"), "OK")
        self.assertEqual(A.classify_provider_error(0, ""), "OK")
        self.assertEqual(A.classify_provider_error(1, "some random failure"), "ERR")


class TestCopilotCmd(unittest.TestCase):
    ENV = {"AGENT_COPILOT_BIN": "node loader.js",
           "AGENT_COPILOT_ARGS": "-p {prompt} -s --no-color --output-format text"}

    def test_prompt_la_MOT_doi_so(self):
        cmd = PC.copilot_cmd("auto", "Tra loi dung mot tu: OK", self.ENV)
        self.assertIn("Tra loi dung mot tu: OK", cmd)       # nguyên văn, 1 phần tử
        self.assertEqual(cmd[:2], ["node", "loader.js"])
        self.assertEqual(cmd[-2:], ["--model", "auto"])

    def test_khong_chen_model_neu_da_co(self):
        env = dict(self.ENV, AGENT_COPILOT_ARGS="-p {prompt} --model gpt-x")
        cmd = PC.copilot_cmd("auto", "hi", env)
        self.assertEqual(cmd.count("--model"), 1)
        self.assertIn("gpt-x", cmd)

    def test_model_duoc_chen_sau_cung(self):
        cmd = PC.copilot_cmd("claude-sonnet-5.5", "hi", self.ENV)
        self.assertEqual(cmd[-2:], ["--model", "claude-sonnet-5.5"])


class TestProbeCopilot(unittest.TestCase):
    def _run(self, rc: int, out: str = "", err: str = ""):
        fake = mock.Mock(returncode=rc, stdout=out, stderr=err)
        with mock.patch("subprocess.run", return_value=fake):
            return PC.probe_copilot("auto", prompt="hi", timeout=5)

    def test_rc0_la_OK(self):
        model, code, _secs, _info = self._run(0, out="OK")
        self.assertEqual((model, code), ("auto", "OK"))

    def test_model_gated_duoc_bao_dung_ma(self):
        _m, code, _s, info = self._run(1, err='Error: Model "x" from --model flag '
                                              'is not available.')
        self.assertEqual(code, "MODEL_GATED")
        self.assertIn("not available", info)

    def test_ngoai_le_khong_lam_chet_probe(self):
        with mock.patch("subprocess.run", side_effect=TimeoutError("qua lau")):
            _m, code, _s, info = PC.probe_copilot("auto", timeout=1)
        self.assertEqual(code, "ERR")
        self.assertIn("qua lau", info)


class TestPaymentVaModelFormat(unittest.TestCase):
    """B-052 — 2 mã lỗi MỚI đo được 12/11 (trước đây đều rơi vào `ERR`/im lặng)."""

    def test_402_het_credit_la_PAYMENT(self):
        # nguyên văn lỗi gateway Cline khi hết credit (5/5 model, 12/11)
        msg = ("402 Client Error: Payment Required for url: "
               "https://api.cline.bot/api/v1/chat/completions")
        self.assertEqual(A.classify_provider_error(1, msg), "PAYMENT")
        self.assertEqual(A.classify_provider_error(0, msg), "PAYMENT")

    def test_cac_cach_noi_het_credit_khac(self):
        for msg in ("insufficient credits", "billing error", "You are out of credits"):
            self.assertEqual(A.classify_provider_error(1, msg), "PAYMENT", msg)

    def test_qwen_sai_dinh_dang_model(self):
        msg = '[API Error: 400 "invalid model format. Expected format: modelType/model"]'
        self.assertEqual(A.classify_provider_error(1, msg), "MODEL_FORMAT")

    def test_payment_khac_quota(self):
        # QUOTA tự reset theo tháng; PAYMENT phải NẠP tiền -> không được gộp làm một
        self.assertNotEqual(A.classify_provider_error(1, "402 Payment Required"), "QUOTA")
        self.assertEqual(A.classify_provider_error(1, "exceeded your monthly quota"),
                         "QUOTA")


class TestProbeCacheVaCandidate(unittest.TestCase):
    """B-052 — cache `logs/model_probe.json`: hội đồng TỰ thêm model sau khi nâng gói."""

    def _cfg(self, cands, models="auto", ttl=7.0):
        return A._CfgOverride(None, agent_council_models=models,
                              agent_council_models_candidates=cands,
                              agent_council_probe_ttl_days=ttl)

    def test_ghi_roi_doc_lai(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = str(Path(td) / "model_probe.json")
            PC.write_probe_cache([("auto", "OK", "20s"), ("grok-4.7", "MODEL_GATED", "16s")],
                                 path=p, now=1000.0)
            cache = A.read_probe_cache(p, now=1000.0)
            self.assertEqual(cache, {"auto": "OK", "grok-4.7": "MODEL_GATED"})
            self.assertFalse((Path(p).parent / "model_probe.json.tmp").exists())

    def test_file_thieu_hong_qua_han_deu_fail_open(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = str(Path(td) / "khong-co.json")
            self.assertEqual(A.read_probe_cache(p), {})
            bad = Path(td) / "hong.json"
            bad.write_text("{khong phai json", encoding="utf-8")
            self.assertEqual(A.read_probe_cache(str(bad)), {})
            ok = Path(td) / "ok.json"
            ok.write_text(json.dumps({"probed_at": 0, "results": {"auto": {"code": "OK"}}}),
                          encoding="utf-8")
            self.assertEqual(A.read_probe_cache(str(ok), ttl_days=7, now=8 * 86400), {})

    def test_chi_them_model_DA_DO_OK(self):
        cache = {"claude-sonnet-5.5": "OK", "grok-4.7": "MODEL_GATED",
                 "auto": "OK", "gpt-6.1-sol": "PAYMENT"}
        got = A.promote_copilot_candidates(
            self._cfg("claude-sonnet-5.5,grok-4.7,auto,gpt-6.1-sol"), cache=cache)
        self.assertEqual(got, ["claude-sonnet-5.5"])   # gated/payment/đã-có -> không thêm

    def test_khong_co_candidate_thi_khong_lam_gi(self):
        self.assertEqual(A.promote_copilot_candidates(self._cfg(""), cache={"a": "OK"}), [])

    def test_hoi_dong_tu_mo_rong_khi_cache_bao_OK(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "model_probe.json"
            p.write_text(json.dumps({"probed_at": time.time(),
                                     "results": {"claude-sonnet-5.5": {"code": "OK"},
                                                 "grok-4.7": {"code": "MODEL_GATED"}}}),
                         encoding="utf-8")
            cfg = self._cfg("claude-sonnet-5.5,grok-4.7")
            with mock.patch.object(A, "PROBE_CACHE_PATH", str(p)):
                self.assertEqual(A.promote_copilot_candidates(cfg), ["claude-sonnet-5.5"])

    def test_qwen_cmd_ghep_dung(self):
        env = {"AGENT_QWEN_BIN": "node cli-entry.js",
               "AGENT_QWEN_ARGS": "-p {prompt} -o text --auth-type openai"}
        cmd = PC.qwen_cmd("Tra loi OK", "openai/qwen3-max", env)
        self.assertEqual(cmd[:2], ["node", "cli-entry.js"])
        self.assertIn("Tra loi OK", cmd)
        self.assertEqual(cmd[-2:], ["-m", "openai/qwen3-max"])
        # đã có -m trong args -> không chèn thêm
        env2 = dict(env, AGENT_QWEN_ARGS="-p {prompt} -m openai/x")
        self.assertEqual(PC.qwen_cmd("p", "openai/y", env2).count("-m"), 1)


if __name__ == "__main__":
    unittest.main()
