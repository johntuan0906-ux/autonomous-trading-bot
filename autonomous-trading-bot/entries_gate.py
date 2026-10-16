"""Cong TAM DUNG vao lenh (entry gate) — dieu khien bang FILE TRANG THAI, khong can restart.

    from entries_gate import paused, pause, resume
    paused(cfg)            -> (bool, ly do)
    pause("ly do", cfg)    # bot KHONG mo lenh moi, van quan ly vi the dang mo
    resume(cfg)            # mo lai

Vi sao (16/10): nguoi van hanh yeu cau *"cho den khi vi the BTW dong, chuyen sang Isolated
roi moi vao lenh khac"*. Tripping kill-switch la SAI ngu nghia (do la bao ve VON) va phai
reset tay; con sua `.env` thi phai restart bot => khong the mo lai ngay luc vi the dong.
File trang thai duoc doc LAI MOI VONG (khong cache) => watcher mo duoc ngay, va cac viec
khac (quan ly vi the, bao ve SL/TP, hoc bai) van chay binh thuong.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

DEFAULT_PATH = "logs/entries_pause.json"


def path_for(cfg=None, path=None) -> Path:
    """Duong dan file trang thai (cfg.entries_pause_path, mac dinh logs/entries_pause.json)."""
    if path:
        return Path(str(path))
    return Path(str(getattr(cfg, "entries_pause_path", DEFAULT_PATH) or DEFAULT_PATH))


def read(cfg=None, path=None) -> dict:
    """Doc file trang thai; loi/thieu -> {} (coi nhu KHONG tam dung = fail-open)."""
    p = path_for(cfg, path)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def paused(cfg=None, path=None) -> tuple:
    """(True, ly do) neu dang TAM DUNG vao lenh moi."""
    d = read(cfg, path)
    if not bool(d.get("paused")):
        return False, ""
    return True, str(d.get("reason") or "tam dung vao lenh moi")


def _write(p: Path, rec: dict) -> dict:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "path": str(p), **rec}
    except OSError as e:
        return {"ok": False, "err": str(e)[:160], **rec}


def pause(reason: str, cfg=None, path=None, now=None, by: str = "ops") -> dict:
    """Bat dau tam dung vao lenh moi (bot VAN quan ly vi the dang mo)."""
    rec = {"paused": True, "reason": str(reason)[:300],
           "since": float(now() if callable(now) else time.time()), "by": str(by)[:40]}
    return _write(path_for(cfg, path), rec)


def resume(cfg=None, path=None, now=None, why: str = "") -> dict:
    """Mo lai vao lenh."""
    rec = {"paused": False, "reason": str(why)[:300],
           "since": float(now() if callable(now) else time.time()), "by": "ops"}
    return _write(path_for(cfg, path), rec)
