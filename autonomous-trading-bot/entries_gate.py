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
import os
import time
from pathlib import Path

import atomic

DEFAULT_PATH = "logs/entries_pause.json"

#: File trang thai hong (JSON khong doc duoc) ⇒ coi nhu DANG tam dung bao nhieu gio.
#: Du dai de nguoi van hanh kip nhin thay, du ngan de khong bi khoa vinh vien.
CORRUPT_GRACE_H = 6.0

#: (15/11, B-057) Cooldown THEO CAP sau 1 lenh THUA — khac `COOLDOWN_SEC` (trong RAM, doi xung,
#: mat khi restart) va khac `strategy.gate_check` (theo nhom setup). Mac dinh 60 phut; 0 = tat.
DEFAULT_COOLDOWN_MIN = 60.0
DEFAULT_JOURNAL = "logs/journal.jsonl"




def path_for(cfg=None, path=None) -> Path:
    """Duong dan file trang thai (cfg.entries_pause_path, mac dinh logs/entries_pause.json)."""
    if path:
        return Path(str(path))
    return Path(str(getattr(cfg, "entries_pause_path", DEFAULT_PATH) or DEFAULT_PATH))


def read(cfg=None, path=None) -> dict:
    """Doc file trang thai.

    - Khong co file          -> `{}` (binh thuong: khong tam dung).
    - Doc loi (quyen/khoa)   -> `{}` (khong phai loi noi dung).
    - Co file nhung JSON hong -> **FAIL-SAFE**: tra ban ghi "dang tam dung" voi
      `until = mtime + 6h`.

    Vi sao doi (21/10): truoc day file hong cung tra `{}` ⇒ bot **tu mo lai vao lenh**
    trong khi nguoi van hanh tuong dang tam dung (file bi cat ngang khi mat dien dung
    luc ghi — da va bang `atomic`, nhung van phai fail-safe). Tu dong het han sau
    `CORRUPT_GRACE_H` gio (lan `paused()` sau do goi `resume()` ghi file moi) nen khong
    bao gio bi khoa vinh vien.
    """
    p = path_for(cfg, path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError:
        return {}
    try:
        d = json.loads(text)
    except Exception:  # noqa: BLE001
        d = None
    if isinstance(d, dict):
        return d
    try:
        mtime = p.stat().st_mtime
    except OSError:
        mtime = time.time()
    return {"paused": True, "corrupt": True,
            "reason": "file trang thai hong (JSON khong doc duoc) — tam dung an toan",
            "until": mtime + CORRUPT_GRACE_H * 3600.0}


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
        atomic.write_json_atomic(p, rec, indent=1)
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


# --------------------------------------------------------------------------------------
# (15/11, B-057) Cooldown THEO CAP sau lenh THUA — doc tu journal nen song qua restart.
# Vi sao can (do tren journal that): `COOLDOWN_SEC` chi la RAM + doi xung (thang cung nghi),
# con `strategy.gate_check` chan theo NHOM setup ⇒ mot cap "nong" van vao lai ngay sau khi SL.
# Freqtrade goi cai nay la `CooldownPeriod`/`StoplossGuard`; o day lam dung 1 viec: cap vua
# THUA thi khong vao lai trong N phut. Lenh THANG khong bi chan (khong tu trung phat).
# --------------------------------------------------------------------------------------
def cooldown_minutes(cfg=None) -> float:
    """So phut cooldown theo cap (`cfg.pair_cooldown_min`, khong co thi doc `PAIR_COOLDOWN_MIN`)."""
    v = getattr(cfg, "pair_cooldown_min", None)
    if v is None:
        try:
            v = float(os.getenv("PAIR_COOLDOWN_MIN", DEFAULT_COOLDOWN_MIN))
        except (TypeError, ValueError):
            v = DEFAULT_COOLDOWN_MIN
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return DEFAULT_COOLDOWN_MIN


def journal_path(cfg=None, journal=None) -> Path:
    """File journal cua INSTANCE dang chay (khong hard-code `logs/journal.jsonl` cua root)."""
    if journal:
        return Path(str(journal))
    p = getattr(cfg, "journal_path", None)
    if p:
        return Path(str(p))
    base = getattr(cfg, "base_dir", None)
    if base:
        return Path(str(base)) / DEFAULT_JOURNAL
    return Path(DEFAULT_JOURNAL)


def _loss_of(rec: dict) -> bool:
    """True neu ban ghi CLOSE nay la THUA (r<0 hoac won=False)."""
    try:
        if float(rec.get("r")) < 0:
            return True
    except (TypeError, ValueError):
        pass
    return rec.get("won") is False


def _parse_loss(ln: str):
    """(pair, rec) neu dong journal la CLOSE THUA, nguoc lai None."""
    if not ln.startswith("{"):
        return None
    try:
        rec = json.loads(ln)
    except ValueError:
        return None
    if str(rec.get("event") or "") != "CLOSE":
        return None
    if not _loss_of(rec):
        return None
    pair = str(rec.get("pair") or rec.get("symbol") or "")
    if not pair:
        return None
    try:
        float(rec.get("ts") or 0.0)
    except (TypeError, ValueError):
        return None
    return pair, rec


#: Cache `pair -> CLOSE THUA gan nhat`, khoa = (duong dan, mtime_ns, size).
#: Vi sao phai cache: `in_cooldown()` duoc goi cho TUNG cap moi vong (~460 cap), journal that
#: 7.000+ dong ⇒ doc lai 460 lan/vong la qua dat. Journal doi (ghi them) thi khoa doi ⇒ doc lai 1 lan.
_LOSS_CACHE: dict = {"key": None, "idx": {}}


def _loss_index(p: Path) -> dict:
    try:
        st = p.stat()
    except OSError:
        return {}
    key = (str(p), st.st_mtime_ns, st.st_size)
    if _LOSS_CACHE.get("key") == key:
        return _LOSS_CACHE.get("idx") or {}
    idx: dict = {}
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    for ln in lines:
        got = _parse_loss(ln.strip())
        if not got:
            continue
        pair, rec = got
        ts = float(rec.get("ts") or 0.0)
        old = idx.get(pair)
        if old is None or ts > float(old.get("ts") or 0.0):
            idx[pair] = rec
    _LOSS_CACHE["key"] = key
    _LOSS_CACHE["idx"] = idx
    return idx


def last_loss(pair: str, cfg=None, journal=None, now=None,
              lookback_h: float = 48.0) -> dict | None:
    """Ban ghi CLOSE THUA gan nhat cua `pair` trong `lookback_h` gio (None neu khong co)."""
    t_now = float(now() if callable(now) else (now if now is not None else time.time()))
    rec = _loss_index(journal_path(cfg, journal)).get(str(pair or ""))
    if not rec:
        return None
    ts = float(rec.get("ts") or 0.0)
    if ts > t_now or ts < t_now - float(lookback_h) * 3600.0:
        return None
    return dict(rec)


def in_cooldown(pair: str, cfg=None, journal=None, now=None,
                minutes=None) -> tuple:
    """(True, ly do) neu cap nay VUA THUA va con trong thoi gian nguoi.

    `minutes` = None ⇒ lay `cfg.pair_cooldown_min` / `PAIR_COOLDOWN_MIN`; 0 ⇒ tat (luon False).
    """
    mins = cooldown_minutes(cfg) if minutes is None else max(0.0, float(minutes))
    if mins <= 0:
        return False, ""
    rec = last_loss(pair, cfg=cfg, journal=journal, now=now)
    if not rec:
        return False, ""
    t_now = float(now() if callable(now) else (now if now is not None else time.time()))
    ts = float(rec.get("ts") or 0.0)
    due = ts + mins * 60.0
    if t_now >= due:
        return False, ""
    left = (due - t_now) / 60.0
    try:
        r = float(rec.get("r"))
    except (TypeError, ValueError):
        r = 0.0
    return True, ("cap vua THUA %.2fR (PAIR_COOLDOWN_MIN=%.0f) — con %.0f phut; "
                  "thang khong bi chan" % (r, mins, max(1.0, left)))

