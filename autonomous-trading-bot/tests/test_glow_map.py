"""Regression test cho glow_map.html (dashboard 3D "star cluster" offline).

Giu dung cac loi da lam ban do trang truoc day (xem tests/test_map_html.py):
canvas khong duoc size, JS lech dau }, thieu </script>, du lieu nhung khong
escape '</'. Ngoai ra kiem tra template con giu cac thong so copy tu
graph-ui/src/lib (bloom, density scale, spectral palette) va co self-test
(window.__glow + document.title = GLOW_OK) de test headless bat duoc man hinh
trang.
"""
from __future__ import annotations

import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _brace_balance(js: str) -> int:
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


class TestGlowTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tpl = (ROOT / "glow_map_template.html").read_text(encoding="utf-8")
        cls.js = cls.tpl[cls.tpl.index("<script>"):]

    def test_canvas_is_sized(self):
        self.assertIn("#cv{display:block;width:100%;height:100%}", self.tpl)

    def test_js_braces_balanced(self):
        self.assertEqual(_brace_balance(self.js), 0)

    def test_html_tags_closed(self):
        self.assertTrue(self.tpl.rstrip().endswith("</html>"))
        self.assertEqual(self.tpl.count("</script>"), 1)

    def test_placeholder_present(self):
        self.assertEqual(self.tpl.count("__GLOW_PAYLOAD__"), 1)

    def test_graph_ui_constants_copied(self):
        for needle in ("EDGE_REF_COUNT = 2500", "GLOW_BASE = 1.35",
                       "GLOW_BLUE_GAIN = 2.4", "BLOOM_INTENSITY = 1.45",
                       "EDGE_SAME_CLUSTER = 0.25", "EDGE_CROSS_CLUSTER = 0.06",
                       "CAM_DIST = 3.2", "IDLE_MS = 60000"):
            self.assertIn(needle, self.js, needle)

    def test_self_test_hook(self):
        self.assertIn("GLOW_OK ", self.js)
        self.assertIn("window.__glow", self.js)

    def test_error_trap_visible(self):
        self.assertIn("window.addEventListener('error'", self.js)
        self.assertIn("id=\"err\"", self.tpl)

    def test_effects_present(self):
        """7 hieu ung + toggle trong sidebar."""
        for k in ("twinkle", "dof", "flow", "ripple", "sat", "nebula", "auto"):
            self.assertIn(k + ": true", self.js, k)
            self.assertIn('id="fx' + k[0].upper() + k[1:] + '"', self.tpl, k)

    def test_effect_renderers_present(self):
        for fn in ("function dofLevel", "function drawSatEdges", "function drawSatNodes",
                   "function drawFlow", "function drawRipples", "function drawPulse",
                   "function drawVignette", "function buildBackdrop", "function stepSpin"):
            self.assertIn(fn, self.js, fn)

    def test_tooltip_hover(self):
        self.assertIn('id="tip"', self.tpl)
        for fn in ("function showTip", "function showSatTip", "function hideTip",
                   "function pickSat", "function placeTip"):
            self.assertIn(fn, self.js, fn)

    def test_layout_modes_present(self):
        """3 kiểu khối cầu 3D + chip chọn + lưới kinh/vĩ tuyến cho kiểu vỏ cầu."""
        self.assertIn('id="layChips"', self.tpl)
        for needle in ("const LAYOUTS = [['cluster', 'Cụm sao'], ['shell', 'Vỏ cầu'],"
                       " ['ball', 'Cầu đặc']]",
                       "function setLayout", "function buildLayoutChips",
                       "function layoutName", "function updateGraphName",
                       "function camSetup", "function camPoint",
                       "function drawGlobe", "const GLOBE_RINGS",
                       "const LAY_SCALE", "function layScale",
                       "posSrc"):
            self.assertIn(needle, self.js, needle)
        for k in ("posShell", "posBall"):
            self.assertIn(k, self.js, k)

    def test_layout_switches_only_positions(self):
        """Đổi kiểu khối cầu không được đụng tới edge / cờ hiệu ứng."""
        body = self.js.split("function setLayout(key){", 1)[1].split("\n}", 1)[0]
        self.assertIn("P.pos = P.posSrc[key]", body)
        self.assertIn("P.sat.pos = P.sat.posSrc[key]", body)
        self.assertNotIn("E[", body)           # không dựng lại danh sách edge
        self.assertNotIn("effects.", body)     # không bật/tắt hiệu ứng
        self.assertIn("buildLayoutChips()", body)
        self.assertIn("needsRender = true", body)

    def test_layout_keyboard_shortcuts(self):
        self.assertIn("['1', '2', '3'].indexOf(e.key)", self.js)
        self.assertIn("if (i >= 0) setLayout(LAYOUTS[i][0]);", self.js)

    def test_globe_wireframe_only_in_shell_mode(self):
        """Lưới kinh/vĩ tuyến chỉ hiện ở kiểu 'Vỏ cầu'."""
        body = self.js.split("function drawGlobe(){", 1)[1].split("\n}", 1)[0]
        self.assertIn("if (layoutKey !== 'shell') return;", body)
        self.assertIn("GLOBE_RINGS", body)
        self.assertIn("camPoint(", body)
        self.assertIn("drawGlobe()", self.js)

    def test_satellite_cross_color_matches_builder(self):
        builder = (ROOT / "build_glow.py").read_text(encoding="utf-8")
        self.assertIn("CROSS_COLOR = \"#fb923c\"", builder)
        self.assertIn("SAT_CROSS_COLOR = '#fb923c'", self.js)
        self.assertIn("SAT_COLOR = \"#c084fc\"", builder)


class TestGlowWebglEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = (ROOT / "glow_map_webgl_engine.js").read_text(encoding="utf-8")
        cls.tpl = (ROOT / "glow_map_webgl_template.html").read_text(encoding="utf-8")

    def test_js_braces_balanced(self):
        self.assertEqual(_brace_balance(self.eng), 0)

    def test_uses_real_three_passes(self):
        for needle in ("UnrealBloomPass", "BokehPass", "EffectComposer", "RenderPass",
                       "OrbitControls", "InstancedMesh", "AdditiveBlending",
                       "setColorAt", "instanceColor"):
            self.assertIn(needle, self.eng, needle)

    def test_shares_payload_and_shell_with_canvas2d(self):
        self.assertIn("const DATA = __GLOW_PAYLOAD__;", self.tpl)
        self.assertIn("__GLOW_ENGINE__", self.tpl)
        self.assertIn("__GLOW_VENDOR__", self.tpl)
        for dom in ('id="nodeChips"', 'id="edgeChips"', 'id="fxTwinkle"', 'id="fxSat"',
                    'id="search"', 'id="detail"', 'id="tip"', 'id="sBloom"'):
            self.assertIn(dom, self.tpl, dom)

    def test_bloom_and_dof_params(self):
        self.assertIn("strength: 1.45", self.eng)
        self.assertIn("radius: 0.6", self.eng)
        self.assertIn("threshold: 0.3", self.eng)
        self.assertIn("W_DOF", self.eng)

    def test_fallback_when_no_webgl(self):
        self.assertIn("không có WebGL", self.eng)
        self.assertIn("glow_map.html", self.eng)

    def test_self_test_reads_pixels(self):
        self.assertIn("GLOW_WGL_OK", self.eng)
        self.assertIn("readPixels", self.eng)
        self.assertIn("window.__glow", self.eng)

    def test_layout_modes_present(self):
        """3 kiểu khối cầu: chip chọn + đổi ma trận instance + lưới kinh/vĩ tuyến."""
        self.assertIn('id="layChips"', self.tpl)
        for needle in ("W_LAYOUTS", "function wApplyLayout", "function wMakeGlobe",
                       "function wPlaceNodes", "function wBuildLayoutChips",
                       "function wUpdateStats", "function wUpdateName",
                       "posSrc", "posShell", "posBall"):
            self.assertIn(needle, self.eng, needle)

    def test_layout_switch_rebuilds_from_new_positions(self):
        """Đổi kiểu: thay WP.pos rồi dựng lại ma trận/edge - không đụng cờ hiệu ứng."""
        body = self.eng.split("function wApplyLayout(key){", 1)[1].split("\n}", 1)[0]
        self.assertIn("WP.pos = WP.posSrc[key]", body)
        self.assertIn("WP.sat.pos = WP.sat.posSrc[key]", body)
        self.assertIn("wPlaceNodes()", body)
        self.assertIn("wRebuildEdges(WGL)", body)
        self.assertIn("wRebuildCross(WGL)", body)
        self.assertNotIn("wfx.", body)

    def test_globe_lines_only_in_shell_mode(self):
        self.assertIn("wlayout === 'shell'", self.eng)
        body = self.eng.split("function wMakeGlobe(){", 1)[1].split("\n}", 1)[0]
        self.assertIn("THREE.LineSegments", body)
        self.assertIn("[-60, -30, 0, 30, 60].forEach", body)      # vĩ tuyến
        self.assertIn("for (let m = 0; m < 6; m++)", body)        # kinh tuyến
        self.assertIn("keepBg = true", body)


class TestGlowWebglOnDisk(unittest.TestCase):
    def _html(self) -> str:
        p = ROOT / "glow_map_webgl.html"
        if not p.exists():
            self.skipTest("glow_map_webgl.html chua duoc generate")
        return p.read_text(encoding="utf-8")

    def test_vendor_inlined_no_placeholders(self):
        html = self._html()
        self.assertNotIn("__GLOW_", html)
        for needle in ("UnrealBloomPass", "BokehPass", "OrbitControls",
                       "EffectComposer", "THREE"):
            self.assertIn(needle, html, needle)
        self.assertTrue(html.rstrip().endswith("</html>"))

    def test_payload_matches_canvas2d(self):
        """Cùng payload: số node/edge/ve tinh phải khớp giữa 2 bản render."""
        def payload_of(name: str):
            html = (ROOT / name).read_text(encoding="utf-8")
            line = html.split("const DATA = ", 1)[1].split("\n", 1)[0]
            return json.loads(line.rstrip(";").replace("<\\/", "</"))

        a = payload_of("glow_map.html")["datasets"]
        b = payload_of("glow_map_webgl.html")["datasets"]
        self.assertEqual(len(a), len(b))
        for da, db in zip(a, b):
            self.assertEqual(da["id"], db["id"])
            self.assertEqual(da["edges"], db["edges"])
            self.assertEqual(len(da["pos"]), len(db["pos"]))
            self.assertEqual((da["sat"] or {}).get("id"), (db["sat"] or {}).get("id"))

    def test_layout_payload_matches_canvas2d(self):
        """3 kiểu khối cầu (và toạ độ vệ tinh) phải giống tuyệt đối giữa 2 bản render."""
        def payload_of(name: str):
            html = (ROOT / name).read_text(encoding="utf-8")
            line = html.split("const DATA = ", 1)[1].split("\n", 1)[0]
            return json.loads(line.rstrip(";").replace("<\\/", "</"))

        a = payload_of("glow_map.html")["datasets"]
        b = payload_of("glow_map_webgl.html")["datasets"]
        self.assertEqual(len(a), len(b))
        for da, db in zip(a, b):
            for k in ("layouts", "pos", "posShell", "posBall"):
                self.assertEqual(da[k], db[k], k)
            sa, sb = da["sat"], db["sat"]
            self.assertEqual(bool(sa), bool(sb))
            if sa:
                for k in ("pos", "posShell", "posBall"):
                    self.assertEqual(sa[k], sb[k], k)

    def test_regenerate_script(self):
        builder = (ROOT / "build_glow.py").read_text(encoding="utf-8")
        self.assertIn('WEBGL_TEMPLATE = ROOT / "glow_map_webgl_template.html"', builder)
        self.assertIn('WEBGL_ENGINE = ROOT / "glow_map_webgl_engine.js"', builder)
        self.assertIn('WEBGL_OUT = ROOT / "glow_map_webgl.html"', builder)


class TestGlowBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / "build_glow.py").read_text(encoding="utf-8")

    def test_escapes_closing_tag(self):
        self.assertIn('.replace("</", "<\\\\/")', self.src)

    def test_layout_is_precomputed(self):
        self.assertIn("def force_layout(", self.src)
        self.assertIn("import numpy as np", self.src)

    def test_sphere_layout_builders(self):
        """Builder phải sinh sẵn 2 kiểu khối cầu (vỏ cầu + cầu đặc) cho cả main + vệ tinh."""
        for needle in ("def sphere_shell(", "def solid_ball(",
                       'LAYOUTS = ["cluster", "shell", "ball"]',
                       '"posShell": [round(float(v), 4)',
                       '"posBall": [round(float(v), 4)',
                       '"layouts": list(LAYOUTS),',
                       'sat["posShell"] = variants["shell"]["pos"]',
                       'sat["posBall"] = variants["ball"]["pos"]',
                       'for key, arr in (("cluster", pos), ("shell", pos_shell),'
                       ' ("ball", pos_ball)):'):
            self.assertIn(needle, self.src, needle)

    def test_cluster_index_matches_node_refs(self):
        """clusters phai giu thu tu goc, khong duoc sort/tron (index dung cho node)."""
        self.assertIn('"cluster": cluster_idx', self.src)
        self.assertNotIn('sorted([[c, ccount[c]] for c in clusters]', self.src)


class TestGlowMapOnDisk(unittest.TestCase):
    def _html(self) -> str:
        p = ROOT / "glow_map.html"
        if not p.exists():
            self.skipTest("glow_map.html chua duoc generate")
        return p.read_text(encoding="utf-8")

    def test_single_script_and_closed(self):
        html = self._html()
        self.assertEqual(html.count("<script"), 1)
        self.assertEqual(html.count("</script>"), 1)
        self.assertTrue(html.rstrip().endswith("</html>"))

    def _payload(self) -> dict:
        html = self._html()
        line = html.split("const DATA = ", 1)[1].split("\n", 1)[0]
        if line.endswith(";"):
            line = line[:-1]
        return json.loads(line.replace("<\\/", "</"))

    def test_payload_is_valid_json(self):
        data = self._payload()
        self.assertGreaterEqual(len(data["datasets"]), 1)
        for ds in data["datasets"]:
            n = len(ds["id"])
            self.assertEqual(len(ds["pos"]), n * 3, "pos phai la x,y,z cho moi node")
            self.assertEqual(len(ds["deg"]), n)
            self.assertEqual(len(ds["spec"]), n)
            self.assertEqual(len(ds["kind"]), n)
            self.assertEqual(len(ds["cluster"]), n)
            self.assertEqual(len(ds["edges"]) % 4, 0)
            self.assertEqual(len(ds["clusters"]), len(ds["clusterCount"]))
            self.assertLessEqual(max(ds["cluster"]), len(ds["clusters"]) - 1)
            self.assertLessEqual(max(ds["kind"]), len(ds["kinds"]) - 1)
            self.assertTrue(all(abs(v) <= 1.0001 for v in ds["pos"]),
                            "toa do phai nam trong qua cau ban kinh 1 (co the am)")

    @staticmethod
    def _radii(pos):
        return [math.sqrt(sum(v * v for v in pos[k:k + 3])) for k in range(0, len(pos), 3)]

    def test_layout_sphere_geometry(self):
        """pos = cụm sao (force layout), posShell = vỏ cầu r=1, posBall = khối cầu đặc."""
        for ds in self._payload()["datasets"]:
            n = len(ds["id"])
            self.assertEqual(ds["layouts"], ["cluster", "shell", "ball"])
            for k in ("pos", "posShell", "posBall"):
                self.assertEqual(len(ds[k]), n * 3, k)
            shell = self._radii(ds["posShell"])
            self.assertTrue(all(abs(r - 1.0) < 1e-3 for r in shell),
                            "vỏ cầu: mọi node phải đúng bán kính 1 (rải đều Fibonacci)")
            ball = self._radii(ds["posBall"])
            self.assertLess(max(ball), 1.0002)
            self.assertGreater(min(ball), 0.05, "khối cầu đặc: không có node nằm đúng tâm")
            self.assertTrue(0.65 < sum(ball) / n < 0.9,
                            "khối cầu đặc: bán kính trung bình ~0.78 (mật độ đều theo thể tích)")
            cluster = self._radii(ds["pos"])
            self.assertLess(max(cluster), 1.0002)
            self.assertLess(sum(cluster) / n, 0.6,
                            "cụm sao: bám gần tâm hơn hẳn vỏ cầu/khối cầu đặc")

    def test_layouts_share_single_edge_list(self):
        """Đổi kiểu khối cầu KHÔNG đổi edge: mọi kiểu dùng chung đúng 1 danh sách edge."""
        for ds in self._payload()["datasets"]:
            self.assertEqual(len(ds["edges"]) % 4, 0)
            self.assertEqual(ds["stats"]["edges"], len(ds["edges"]) // 4)
            for absent in ("edgesShell", "edgesBall", "edgesCluster"):
                self.assertNotIn(absent, ds, absent)

    def test_satellite_layout_shells(self):
        """Vệ tinh cũng có 3 kiểu toạ độ và luôn nằm ngoài khối cầu chính."""
        for ds in self._payload()["datasets"]:
            sat = ds["sat"]
            if not sat:
                continue
            sn = len(sat["id"])
            for k in ("pos", "posShell", "posBall"):
                self.assertEqual(len(sat[k]), sn * 3, k)
                r = self._radii(sat[k])
                self.assertGreater(sum(r) / sn, 1.4, k + ": vệ tinh phải ở vỏ ngoài")
                self.assertLess(max(r), 3.0, k + ": vệ tinh không được văng quá xa")

    def test_layout_edges_reference_valid_nodes(self):
        for ds in self._payload()["datasets"]:
            n = len(ds["id"])
            for e in range(0, len(ds["edges"]), 4):
                s, t = ds["edges"][e], ds["edges"][e + 1]
                self.assertLess(s, n)
                self.assertLess(t, n)

    def test_satellite_galaxy_payload(self):
        """Galaxy ve tinh (mem records) + cross link phai nhat quan."""
        for ds in self._payload()["datasets"]:
            sat = ds["sat"]
            if not sat:
                continue
            n = len(ds["id"])
            sn = len(sat["id"])
            self.assertGreater(sn, 0)
            self.assertEqual(len(sat["pos"]), sn * 3)
            self.assertEqual(len(sat["deg"]), sn)
            self.assertEqual(len(sat["label"]), sn)
            self.assertEqual(len(sat["edges"]) % 4, 0)
            self.assertEqual(len(sat["cross"]) % 2, 0)
            for i in range(0, len(sat["cross"]), 2):
                self.assertLess(sat["cross"][i], n)
                self.assertLess(sat["cross"][i + 1], sn)
            for i in range(0, len(sat["edges"]), 4):
                self.assertLess(sat["edges"][i], sn)
                self.assertLess(sat["edges"][i + 1], sn)
            # ve tinh nam ngoai qua cau chinh (ban kinh 1)
            r2 = [sum(v * v for v in sat["pos"][k:k + 3]) for k in range(0, sn * 3, 3)]
            self.assertGreater(sum(r2) / sn, 1.4, "ve tinh phai o vo ngoai")

    def test_regenerate_script(self):
        builder = (ROOT / "build_glow.py").read_text(encoding="utf-8")
        self.assertIn('TEMPLATE = ROOT / "glow_map_template.html"', builder)
        self.assertIn('OUT = ROOT / "glow_map.html"', builder)


if __name__ == "__main__":
    unittest.main()
