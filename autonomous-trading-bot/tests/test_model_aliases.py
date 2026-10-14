"""Test `model_aliases` + `ClineProvider` (map id gateway) — loi that 13/10.

Do that: gateway `api.cline.bot` doi id sang dang `<vendor>/<ten>`; gui ten cu
`cline-pass/glm-5.3` tra **HTTP 500 {"error":"empty response content"}** ⇒ 12/14 model
hoi dong chet (48h: 328 ban ghi AGENT, 0 VETO/0 ALLOW) du gateway van song (462 model).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import model_aliases as MA      # noqa: E402


class TestMapGateway(unittest.TestCase):
    def test_map_dung_cho_cac_model_hoi_dong(self):
        cases = {
            "cline-pass/glm-5.3": "z-ai/glm-5.3",
            "cline-pass/deepseek-v4-pro": "deepseek/deepseek-v4-pro",
            "cline-pass/deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
            "cline-pass/qwen3.8-max": "qwen/qwen3.8-max-prime",
            "cline-pass/qwen3.7-plus": "qwen/qwen3.7-plus",
            "cline-pass/kimi-k3": "moonshotai/kimi-k3",
            "cline-pass/minimax-m3": "minimax/minimax-m3",
            "cline-pass/mimo-v2.6-pro": "xiaomi/mimo-v2.6-pro",
            "cline-pass/mimo-v2.5": "xiaomi/mimo-v2.5",
        }
        for alias, want in cases.items():
            self.assertEqual(MA.to_gateway(alias), want, alias)

    def test_id_gateway_san_thi_giu_nguyen(self):
        self.assertEqual(MA.to_gateway("anthropic/claude-haiku-5.5"),
                         "anthropic/claude-haiku-5.5")

    def test_khong_map_duoc_thi_bo_tien_to(self):
        """Ten la -> tra ve ten da bo tien to (gateway se tu choi, health se hien)."""
        self.assertEqual(MA.to_gateway("cline-pass/khong-co-that"), "khong-co-that")

    def test_rong_va_khong_co_tien_to(self):
        self.assertEqual(MA.to_gateway(""), "")
        self.assertEqual(MA.to_gateway("glm-5.3"), "z-ai/glm-5.3",
                         "khong co tien to van map duoc")

    def test_is_mapped(self):
        self.assertTrue(MA.is_mapped("cline-pass/glm-5.3"))
        self.assertTrue(MA.is_mapped("anthropic/claude-haiku-5.5"))
        self.assertFalse(MA.is_mapped("cline-pass/khong-co-that"))
        self.assertFalse(MA.is_mapped(""))

    def test_moi_alias_trong_catalog_deu_map_duoc(self):
        """Khong de sot model nao trong catalog -> moi alias phai co id that."""
        import json
        p = ROOT / "Multi_AI_Agent" / "models.clinepass.json"
        if not p.exists():
            self.skipTest("khong co catalog")
        d = json.loads(p.read_text(encoding="utf-8"))
        models = [a["model"] for a in d.get("agents", [])] + [d.get("finalizer_model")]
        missing = [m for m in models if m and not MA.is_mapped(m)]
        self.assertEqual(missing, [], "thieu map cho: %s" % missing)


class TestClineProviderDungIdGateway(unittest.TestCase):
    """Provider phai GUI id gateway (khong phai alias) + co max_tokens."""

    def _prov(self, alias: str):
        import agents as AG
        return AG.ClineProvider(model=alias, api_key="k")

    def test_giu_alias_de_log_nhung_gui_id_gateway(self):
        p = self._prov("cline-pass/glm-5.3")
        self.assertEqual(p.model, "cline-pass/glm-5.3", "alias giu de log/journal")
        self.assertEqual(p.api_model, "z-ai/glm-5.3", "id GUI DI phai la id gateway")

    def test_luon_co_max_tokens(self):
        self.assertGreaterEqual(self._prov("cline-pass/qwen3.7-plus").max_tokens, 32)

    def test_goi_that_dung_id_va_max_tokens(self):
        from unittest import mock
        p = self._prov("cline-pass/mimo-v2.6-pro")
        seen: dict = {}

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": {"choices": [{"message": {"content": "{\"action\":\"ALLOW\"}"}}],
                                 "usage": {"prompt_tokens": 10, "completion_tokens": 5}}}

        def fake_post(url, timeout=None, headers=None, json=None):  # noqa: A002
            seen.update(json or {})
            return R()

        import requests
        with mock.patch.object(requests, "post", fake_post):
            out = p.complete("sys", "user")
        self.assertEqual(seen.get("model"), "xiaomi/mimo-v2.6-pro")
        self.assertIn("max_tokens", seen, "phai gui max_tokens (neu khong model tra rong)")
        self.assertIn("ALLOW", out["text"])


if __name__ == "__main__":
    unittest.main()
