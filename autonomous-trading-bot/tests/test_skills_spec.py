# -*- coding: utf-8 -*-
"""Chốt hợp lệ `skills/` theo Agent Skills spec (12/11, B-052).

Vì sao cần: 4 runbook dưới `skills/` là bản duy nhất encode 4 lỗi đã tái diễn (hội đồng im lặng,
dust, journal ≠ equity, tài liệu lệch code). Một `SKILL.md` hỏng frontmatter sẽ **không được agent nào
nạp** mà không ai biết — đúng lớp lỗi "im lặng" của repo. Test này rẻ và chặn đúng lỗi đó:

1. mỗi thư mục con phải có `SKILL.md`;
2. frontmatter phải có `name` + `description`, `name` khớp tên thư mục (dạng kebab-case);
3. `description` phải nói ĐƯỢC KHI NÀO dùng (dài ≥ 30 ký tự);
4. thân skill phải nhắc ít nhất một tool THẬT (tên file trong `tools/` hoặc file `.py` ở gốc repo) —
   skill chỉ toàn lời khuyên chung là skill vô dụng.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
TOOLS = {p.stem for p in (ROOT / "tools").glob("*.py")} | {p.stem for p in ROOT.glob("*.py")}


def _dirs() -> list:
    if not SKILLS.is_dir():
        return []
    return sorted(d for d in SKILLS.iterdir() if d.is_dir())


def _front(text: str) -> dict:
    """Doc frontmatter YAML đơn giản (không cần PyYAML): `key: value` ở đầu file."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class TestSkillsSpec(unittest.TestCase):
    def test_co_it_nhat_mot_skill(self):
        self.assertTrue(_dirs(), "skills/ phai co it nhat 1 skill")

    def test_moi_skill_co_SKILL_md(self):
        for d in _dirs():
            with self.subTest(skill=d.name):
                self.assertTrue((d / "SKILL.md").is_file(), f"{d.name}: thieu SKILL.md")

    def test_frontmatter_hop_le(self):
        for d in _dirs():
            with self.subTest(skill=d.name):
                fm = _front((d / "SKILL.md").read_text(encoding="utf-8"))
                self.assertEqual(fm.get("name"), d.name, "name phai khop ten thu muc")
                self.assertRegex(d.name, r"^[a-z0-9]+(-[a-z0-9]+)*$", "kebab-case")
                desc = fm.get("description", "")
                self.assertGreaterEqual(len(desc), 30, "description phai noi DUOC KHI NAO dung")

    def test_than_skill_goi_tool_that(self):
        for d in _dirs():
            with self.subTest(skill=d.name):
                body = (d / "SKILL.md").read_text(encoding="utf-8")
                hits = {t for t in TOOLS if re.search(rf"\b{re.escape(t)}\b", body)}
                self.assertTrue(hits, f"{d.name}: khong nhac tool that nao ({sorted(TOOLS)[:3]}...)")

    def test_readme_index_lieu_du_skill(self):
        readme = SKILLS / "README.md"
        if not readme.is_file():
            self.skipTest("chua co README")
        txt = readme.read_text(encoding="utf-8")
        for d in _dirs():
            with self.subTest(skill=d.name):
                self.assertIn(f"`{d.name}/`", txt, f"{d.name} chua co trong bang README")


if __name__ == "__main__":
    unittest.main()
