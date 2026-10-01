"""test_clinepass_integration.py — tích hợp Multi_AI_Agent vào dự án bot.

Kiểm tra (KHÔNG gọi API, không tốn quota):
  1) build_bundle() gom dữ liệu thật của bot + KHÔNG lộ secret (API key .env);
  2) build_cmd() dựng đúng lệnh cho harness (clinepass + lab);
  3) preflight() chặn khi thiếu CLINE_API_KEY (provider=clinepass);
  4) chạy THẬT end-to-end với --provider mock (offline) → rc=0 + report.md.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import clinepass_review as CR                                                   # noqa: E402

sys.path.insert(0, str(ROOT / "Multi_AI_Agent"))
from agent_lab.clinepass import unwrap_envelope                               # noqa: E402


class TestEnvelope(unittest.TestCase):
    """Gateway Cline boc ket qua trong {"data": ...} (01/10) — client phai nhan ca 2 dang."""

    def test_boc_data(self):
        inner = {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
                 "usage": {"prompt_tokens": 5, "completion_tokens": 1}}
        got = unwrap_envelope({"data": inner, "success": True})
        self.assertIs(got, inner)

    def test_dang_phang_giu_nguyen(self):
        flat = {"choices": [{"message": {"content": "OK"}}]}
        self.assertIs(unwrap_envelope(flat), flat)

    def test_dang_la_giu_nguyen_de_bao_loi_sai_dinh_dang(self):
        self.assertEqual(unwrap_envelope({"error": "model not found"}), {"error": "model not found"})
        self.assertEqual(unwrap_envelope(None), {})


def _env_secret_values() -> list:
    """Các giá trị bí mật (khác rỗng) trong .env — dùng để chắc chắn không lọt vào bundle."""
    out = []
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            key, val = line.split("=", 1)
            k = key.strip().upper()
            val = val.strip().strip('"').strip("'")
            if any(s in k for s in ("KEY", "SECRET", "TOKEN")) and len(val) >= 12:
                out.append(val)
    except OSError:
        pass
    return out


class TestTaskFile(unittest.TestCase):
    """Nhiệm vụ gửi harness phải kèm ràng buộc độ dài (tránh finish_reason=length)."""

    def test_them_ràng_buoc_do_dai(self):
        p = CR.build_task_file(ROOT / "tasks" / "safety_audit.txt")
        body = p.read_text(encoding="utf-8")
        self.assertIn("GIỚI HẠN ĐỘ DÀI", body)
        self.assertIn("450 từ", body)
        self.assertLessEqual(len(body), 6000, "harness chi nhan task <= 6000 ky tu")

    def test_khong_nhan_doi_neu_da_co(self):
        p1 = CR.build_task_file(ROOT / "tasks" / "safety_audit.txt")
        p2 = CR.build_task_file(p1)
        self.assertEqual(p1, p2, "task da co rang buoc thi giu nguyen")


class TestBundle(unittest.TestCase):
    def test_bundle_safety_co_du_lieu_va_khong_lo_secret(self):
        p = CR.build_bundle("safety")
        self.assertIsNotNone(p)
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        for marker in ("DU LIEU BOT", "Phieu agent", "risk_state", "THAM SO AN TOAN DANG CHAY THAT"):
            self.assertIn(marker, text)
        self.assertLessEqual(len(text), CR.MAX_BUNDLE_CHARS + 40)
        leaks = [v for v in _env_secret_values() if v in text]
        self.assertEqual(leaks, [], "bundle KHONG duoc chua API key/token tu .env")
        # Tham so dang chay THAT phai co (tranh hoi dong doc nham gia tri mau)
        self.assertIn("max_total_risk_pct", text)

    def test_bundle_none_tra_ve_none(self):
        self.assertIsNone(CR.build_bundle("none"))

    def test_bundle_strategy_co_journal(self):
        p = CR.build_bundle("strategy")
        self.assertIsNotNone(p)
        self.assertIn("Journal", p.read_text(encoding="utf-8"))


class TestCommand(unittest.TestCase):
    def _args(self, **kw):
        base = dict(engine="clinepass", provider="mock", group="core", mode="consensus",
                    concurrency=None, model=None, file=None, output_dir=Path("out"))
        base.update(kw)
        return SimpleNamespace(**base)

    def test_lenh_clinepass_dung_tham_so(self):
        tf = Path("tasks/code_review.txt")
        cmd = CR.build_cmd(self._args(file=["turbo_demo.py"], model=["cline-pass/glm-5.3"],
                                      concurrency=6), Path("b.md"), tf)
        self.assertEqual(cmd[1], str(CR.MAA / "cline_multi.py"))
        self.assertIn("run", cmd)
        self.assertIn("--provider", cmd)
        self.assertIn("mock", cmd)
        self.assertEqual(cmd.count("--context"), 2)          # file + bundle
        self.assertIn("cline-pass/glm-5.3", cmd)
        self.assertEqual(cmd[cmd.index("--concurrency") + 1], "6")

    def test_lenh_lab_dung_mode(self):
        cmd = CR.build_cmd(self._args(engine="lab", provider="openai", mode="consensus"),
                           None, Path("tasks/live_readiness.txt"))
        self.assertEqual(cmd[1], str(CR.MAA / "main.py"))
        self.assertEqual(cmd[cmd.index("--mode") + 1], "consensus")
        self.assertNotIn("--group", cmd)


class TestPreflight(unittest.TestCase):
    def test_thieu_key_thi_chan_clinepass(self):
        old = os.environ.pop("CLINE_API_KEY", None)
        try:
            err = CR.preflight(SimpleNamespace(engine="clinepass", provider="clinepass"),
                               ROOT / "tasks" / "code_review.txt")
            self.assertIn("CLINE_API_KEY", err)
        finally:
            if old is not None:
                os.environ["CLINE_API_KEY"] = old

    def test_thieu_file_task_thi_bao_loi(self):
        err = CR.preflight(SimpleNamespace(engine="clinepass", provider="mock"),
                           ROOT / "tasks" / "khong-ton-tai.txt")
        self.assertIn("Khong thay file nhiem vu", err)


class TestMockRunEndToEnd(unittest.TestCase):
    def test_chay_mock_that_tao_report(self):
        """Chạy chính wrapper với provider mock (offline) → rc=0 + report.md tồn tại."""
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "clinepass_review.py"),
                 "--task", "code_review", "--bundle", "safety", "--provider", "mock",
                 "--group", "core", "--output-dir", d],
                cwd=str(ROOT), capture_output=True, text=True, timeout=180)
            self.assertEqual(proc.returncode, 0, proc.stdout[-800:] + proc.stderr[-800:])
            runs = [p for p in Path(d).iterdir() if p.is_dir()]
            self.assertEqual(len(runs), 1, "phai co dung 1 thu muc ket qua")
            rep = runs[0] / "report.md"
            self.assertTrue(rep.is_file(), "harness phai ghi report.md")
            body = rep.read_text(encoding="utf-8")
            self.assertIn("MÔ PHỎNG", body)          # mock phai duoc danh dau ro
            self.assertIn("Kết quả ClinePass", body)
            self.assertIn("## Trạng thái từng lượt", body)


if __name__ == "__main__":
    unittest.main()
