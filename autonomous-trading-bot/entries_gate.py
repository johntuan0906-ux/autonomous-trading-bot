"""Cong TAM DUNG vao lenh (entry gate) — dieu khien bang FILE TRANG THAI, khong can restart.

    from entries_gate import paused, pause, resume
    paused(cfg)            -> (bool, ly do)
    pause("ly do", cfg)    # bot KHONG mo lenh moi, van quan ly vi the dang mo
    pause("ly do", hours=24)   # tam dung CO HAN -> het han TU MO LAI (19/10)
    resume(cfg)            # mo lai

Vi sao (16/10): nguoi van hanh yeu cau *"cho den khi vi the BTW dong, chuyen sang Isolated
roi moi vao lenh khac"*. Tripping kill-switch la SAI ngu nghia (do la bao ve VON) va phai
reset tay; con sua `.env` thi phai restart bot => khong the mo lai ngay luc vi the dong.
File trang thai duoc doc LAI MOI VONG (khong cache) => watcher mo duoc ngay, va cac viec
khac (quan ly vi the, bao ve SL/TP, hoc bai) van chay binh thuong.

Vi sao co HAN (19/10, phieu hoi dong 4-0 VETO): "tam dung roi quen mo lai" la lop loi da
gap that (BTW 16-18/10 phai co watcher rieng; TESTNET ket pause 3.6 ngay vi `tripped`
khong tu xoa). `pause(..., hours=N)` ghi `until`; qua han thi `paused()` TU MO LAI va ghi
vet vao file. Fail-safe: file hong / thieu `until` => VAN tam dung.
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


def paused(cfg=None, path=None, now=None) -> tuple:
    """(True, ly do) neu dang TAM DUNG vao lenh moi.

    (19/10) Ho tro HET HAN: `pause(..., hours=N)` ghi `until`; khi da qua han thi
    **tu mo lai** (ghi vet vao chinh file) va tra `False`. Fail-safe: file hong, thieu
    `until`, hoac `until` khong phai so => VAN coi nhu dang tam dung.
    """
    d = read(cfg, path)
    if not bool(d.get("paused")):
        return False, ""
    until = d.get("until")
    if until:
        try:
            due = float(until)
        except (TypeError, ValueError):
            due = 0.0                     # `until` hong -> KHONG het han
        if due > 0 and float(now() if callable(now) else time.time()) >= due:
            resume(cfg, path, now=now, why="het han tam dung", by="entries_gate")
            return False, "het han tam dung"
    return True, str(d.get("reason") or "tam dung vao lenh moi")


def _write(p: Path, rec: dict) -> dict:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "path": str(p), **rec}
    except OSError as e:
        return {"ok": False, "err": str(e)[:160], **rec}


def pause(reason: str, cfg=None, path=None, now=None, by: str = "ops",
          hours=None) -> dict:
    """Bat dau tam dung vao lenh moi (bot VAN quan ly vi the dang mo).

    `hours` > 0 => tam dung CO HAN (`until` = now + hours*3600); qua han tu mo lai.
    """
    t = float(now() if callable(now) else time.time())
    rec = {"paused": True, "reason": str(reason)[:300], "since": t, "by": str(by)[:40]}
    if hours:
        try:
            h = float(hours)
            if h > 0:
                rec["until"] = t + h * 3600.0
        except (TypeError, ValueError):
            pass
    return _write(path_for(cfg, path), rec)


def resume(cfg=None, path=None, now=None, why: str = "", by: str = "ops") -> dict:
    """Mo lai vao lenh. `by` = AI mo lai (ghi vet: 'ops' hoac 'entries_gate' khi het han)."""
    rec = {"paused": False, "reason": str(why)[:300],
           "since": float(now() if callable(now) else time.time()), "by": str(by)[:40]}
    return _write(path_for(cfg, path), rec)
