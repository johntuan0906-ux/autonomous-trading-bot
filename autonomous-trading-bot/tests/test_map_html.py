"""Regression test cho template HTML cua 2 ban do (graph_memory / memory_map).

Bat dung cac loi da gap lam ban do trang:
  - canvas khong duoc size (thieu CSS width/height) -> chi 300x150, bi panel che
  - JS thieu dau } (brace imbalance) -> browser khong chay script nao
  - thieu the </script> dong -> HTML parse sai
  - du lieu nhung khong escape '</' -> the <script> dong som
  - memory_map fetch JSON tren file:// -> bi CORS chan (can ban nhung memory_map_data.js)
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _brace_balance(js: str) -> int:
    """Depth {} co bo qua chuoi/comment-ngoai-lenh don gian (du cho template nay)."""
    depth = 0
    in_s: str | None = None
    esc = False
    for ch in js:
        if in_s:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_s:
                in_s = None
        elif ch in "\"'`":
            in_s = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    return depth


class TestGraphMemoryTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / "graph_memory.py").read_text(encoding="utf-8")
        tpl = re.search(r'HTML_TEMPLATE = r"""(.*?)"""', cls.src, re.S).group(1)
        cls.tpl = tpl
        cls.js = tpl[tpl.index("const G = __GRAPH__;"):tpl.index("</script>")]

    def test_canvas_is_sized(self):
        self.assertIn("#graph canvas{display:block;width:100%;height:100%}", self.tpl)
        self.assertIn("cv.style.cssText='display:block;width:100%;height:100%'", self.tpl)

    def test_js_braces_balanced(self):
        self.assertEqual(_brace_balance(self.js), 0)

    def test_html_tags_closed(self):
        self.assertIn("</script></body></html>", self.tpl)

    def test_inline_json_escapes_closing_tag(self):
        self.assertIn('.replace("</", "<\\\\/")', self.src)


class TestMemoryMapTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / "memory_map.py").read_text(encoding="utf-8")

        def raw(name: str) -> str:
            return re.search(name + r' = r"""(.*?)"""', cls.src, re.S).group(1)

        cls.head = raw("HTML_HEAD")
        cls.js = raw("HTML_JS_A") + raw("HTML_JS_B")

    def test_canvas_is_sized(self):
        self.assertIn("#canvas-wrap canvas{display:block;width:100%;height:100%}", self.head)

    def test_js_braces_balanced(self):
        self.assertEqual(_brace_balance(self.js), 0)

    def test_html_tags_closed(self):
        self.assertIn("</script></body></html>", self.head + self.js)

    def test_file_protocol_fallback(self):
        self.assertIn('FILE_MODE = location.protocol === "file:"', self.js)
        self.assertIn("window.MAP_DATA", self.js)
        self.assertIn('<script src="memory_map_data.js"></script>', self.head)
        self.assertIn("MAP_DATA_JS", self.src)

    def test_live_interval_skips_file_mode(self):
        self.assertIn("if(live && !FILE_MODE) load();", self.js)


class TestGeneratedMapsOnDisk(unittest.TestCase):
    """Neu 2 file da duoc generate thi kiem tra luon tren san pham that."""

    def _skip_if_missing(self, name: str) -> str:
        p = ROOT / name
        if not p.exists():
            self.skipTest(f"{name} chua duoc generate")
        return p.read_text(encoding="utf-8")

    def test_graph_html_generated_ok(self):
        html = self._skip_if_missing("graph_memory.html")
        self.assertEqual(html.count("<script"), 1, "chi duoc co 1 the <script> that")
        self.assertEqual(html.count("</script>"), 1)
        self.assertIn("cv.style.cssText", html)
        self.assertTrue(html.rstrip().endswith("</html>"), "phai dong </html> cuoi file")

    def test_memory_map_generated_ok(self):
        html = self._skip_if_missing("memory_map.html")
        self.assertIn('<script src="memory_map_data.js"></script>', html)
        self.assertIn("#canvas-wrap canvas{display:block;width:100%;height:100%}", html)
        self.assertTrue(html.rstrip().endswith("</html>"), "phai dong </html> cuoi file")

    def test_memory_map_data_js_embeds_payload(self):
        js = self._skip_if_missing("memory_map_data.js")
        self.assertTrue(js.startswith("window.MAP_DATA = "))
        self.assertIn('"nodes"', js)


if __name__ == "__main__":
    unittest.main()
