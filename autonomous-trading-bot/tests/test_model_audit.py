"""Test `tools/model_audit.py` — checklist model truoc khi vao hoi dong AI.

Thuan tuy, khong goi mang. Vi sao can: hoi dong doc du lieu ngoai (tin tuc) nen
them model "uncensored/abliterated/crack" = bo lop tu choi ma khong co bang chung
chat luong; kich thuoc lon thi may ca nhan khong chay noi.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import model_audit as MA      # noqa: E402


class TestParseModels(unittest.TestCase):
    ENV = (
        "# comment\n"
        "AGENT_COUNCIL_MODELS=claude-sonnet-5.5,grok-4.6\n"
        "AGENT_COUNCIL_CLINE=all\n"
        "AGENT_COUNCIL_QWEN=cline-pass/qwen3.8-max\n"
        "AGENT_COUNCIL_LOCAL=llama3.2:3b\n"
        "AGENT_COUNCIL_MUSE_CLI=\n"
        "LOCAL_SKIP_MODELS=\n"
        "OTHER_KEY=khong-phai-model\n"
    )

    def test_lay_dung_model_va_bo_trung(self):
        got = MA.parse_models(self.ENV)
        models = [m for _, m in got]
        self.assertIn("claude-sonnet-5.5", models)
        self.assertIn("all(cline-pass)", models)
        self.assertIn("cline-pass/qwen3.8-max", models)
        self.assertIn("llama3.2:3b", models)
        self.assertNotIn("khong-phai-model", models)
        self.assertEqual(len(models), len(set(models)), "khong duoc lap model")

    def test_bo_qua_dong_rong_va_comment(self):
        self.assertEqual(MA.parse_models("AGENT_COUNCIL_MUSE_CLI=\n"), [])


class TestPhanLoai(unittest.TestCase):
    def test_provider_tu_tien_to(self):
        self.assertEqual(MA.provider_of("cline-pass/qwen3.8-max"), "cline-pass")
        self.assertEqual(MA.provider_of("llama3.2:3b"), "ollama")
        self.assertEqual(MA.provider_of("claude-sonnet-5.5"), "claude")
        self.assertEqual(MA.provider_of("model-la-hoac"), "khong ro")

    def test_co_do_trong_ten(self):
        self.assertEqual(MA.red_flags("dealignai/DeepSeek-V4.1-Flash-UNCENSORED-FP8"),
                         ["uncensored", "dealign"])
        self.assertEqual(MA.red_flags("llama3.2:3b"), [])
        self.assertEqual(MA.red_flags("x/Abliterated-Crack"), ["abliterated", "crack"])


class TestVramVaKetLuan(unittest.TestCase):
    def test_uoc_vram_theo_tham_so_va_bit(self):
        # 763B tham so, 8 bit -> ~763 GB trong so (+20% overhead)
        self.assertGreater(MA.vram_needed_gb(763, 8), 700)
        # 3B, 4 bit -> ~1.8 GB
        self.assertLess(MA.vram_needed_gb(3, 4), 3)
        self.assertEqual(MA.vram_needed_gb(0, 8), 0.0)

    def test_model_uncensored_khong_nen_dung(self):
        lvl, why = MA.verdict("dealignai/DeepSeek-V4.1-Flash-UNCENSORED-FP8",
                              params_b=763, bits=8, vram_gb=8, has_eval=False)
        self.assertEqual(lvl, "KHONG NEN DUNG")
        self.assertIn("uncensored", why)

    def test_model_lon_khong_chay_duoc_o_may_nho(self):
        lvl, why = MA.verdict("some/Model-70B", params_b=70, bits=16, vram_gb=8,
                              has_eval=True)
        self.assertEqual(lvl, "KHONG NEN DUNG")
        self.assertIn("VRAM", why)

    def test_thieu_eval_thi_xem_lai(self):
        lvl, why = MA.verdict("some/Model-7B", params_b=7, bits=4, vram_gb=8,
                              has_eval=False)
        self.assertEqual(lvl, "XEM LAI")
        self.assertIn("eval", why)

    def test_model_nho_co_eval_thi_ok(self):
        lvl, why = MA.verdict("llama3.2:3b", params_b=3, bits=4, vram_gb=8,
                              has_eval=True)
        self.assertEqual(lvl, "OK")

    def test_audit_env_hoi_dong_hien_tai_khong_co_co_do(self):
        rows = MA.audit_env(TestParseModels.ENV, vram_gb=8)
        levels = [r[2] for r in rows]
        self.assertNotIn("KHONG NEN DUNG", levels,
                         "hoi dong mau khong duoc co model co do")


if __name__ == "__main__":
    unittest.main()
