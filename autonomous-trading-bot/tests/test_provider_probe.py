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

import sys
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


if __name__ == "__main__":
    unittest.main()
