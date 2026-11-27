"""Trade journal: nhat ky moi giao dich (muc 17 tai lieu) — luu JSONL de phan tich sau.

Ngoai viec GHI (`log_trade`), file nay con giu phan DO VET `void` (B-073):
mot so ban ghi OPEN bi ghi TRUNG (adopt chay lap sau restart, B-050) nen trong
journal co 2 OPEN nhung chi co 1 vi the that -> chi 1 CLOSE. Ban ghi thua duoc
danh dau `void: true` (KHONG xoa lich su) de moi bo dem bo qua no.
"""
from __future__ import annotations

import json
import os
import time

#: Gia vao phai TRUNG (cung mot con so trong journal) moi coi la CUNG vi the.
ENTRY_TOL_PCT = 0.0
#: Khoi luong phai khop (sai so tuong doi) — Binance tra cung 1 con so float.
QTY_REL_TOL = 1e-6
#: 2 OPEN cung nhom cach nhau < nguong nay = 1 su kien ghi (khong phai trung that).
MIN_GAP_SEC = 30.0
#: (27/11, B-076) So khop MEM cho ADOPT: journal ghi gia KE HOACH (`lv["entry"]`) con
#: `position_sync.adopt` doc `entryPrice` THAT tu san -> lech vai phan nghin la binh thuong.
#: `pending_keys`/`rec_key` so khop TUYET DOI nen truoc day chi can lech 1 chu so la
#: khong nhan ra "da co OPEN" => lai ghi OPEN lan 2 (B-073 tai phat o dang khac).
ADOPT_ENTRY_TOL_PCT = 0.005
#: CLOSE phai nam trong khoang nay sau OPEN moi duoc coi la cua vi the do.
CLOSE_MAX_LAG_SEC = 30 * 86400.0


def _load(path: str) -> tuple:
    """Doc journal -> (opens, closes), bo qua ban ghi `void` (nhe, khong phu thuoc module)."""
    opens: list = []
    closes: list = []
    if not os.path.exists(path):
        return opens, closes
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("void") is True:
                continue
            if rec.get("event") == "CLOSE" or ("won" in rec and rec.get("event") != "OPEN"):
                closes.append(rec)
            elif "entry" in rec:
                opens.append(rec)
    return opens, closes


def _unclosed_opens(opens: list, closes: list) -> list:
    """OPEN **chua co CLOSE** — ghep theo (cap, huong, gia vao), FIFO theo `ts`.

    Vi sao khong dem `so OPEN - so CLOSE` (B-078): bo dem THO theo cap+huong am khi
    lich su co nhieu CLOSE hon OPEN (CLOSE ghi bu cua `reconcile`, lenh dong tay, ban
    ghi OPEN bi void o B-073) ⇒ vi the DANG MO bi coi la "da dong" ⇒ `adopt` lai ghi
    `OPEN` lan nua (do that LIVE 27/11 11:12: ETH 1705.46 / XRP 0.9621 / SOL 70.11).
    O day moi CLOSE chi "an" MOT OPEN co cung cap + huong + gia vao lech
    <= `ADOPT_ENTRY_TOL_PCT` va `open.ts <= close.ts` (lech <= `CLOSE_MAX_LAG_SEC`);
    CLOSE thua (khong co OPEN tuong ung) bi bo qua, khong keo OPEN that xuong.
    """
    by_key: dict = {}
    for c in closes:
        by_key.setdefault((_pair(c), _dir(c)), []).append(c)
    for rows in by_key.values():
        rows.sort(key=lambda r: _f(r.get("ts")))
    used: dict = {}
    out: list = []
    for o in sorted(opens, key=lambda r: _f(r.get("ts"))):
        key = (_pair(o), _dir(o))
        ots, oen = _f(o.get("ts")), _f(o.get("entry"))
        hit = None
        for i, c in enumerate(by_key.get(key) or []):
            if i in used.get(key, ()):
                continue
            cts, cen = _f(c.get("ts")), _f(c.get("entry"))
            if cts < ots or (ots > 0 and cts - ots > CLOSE_MAX_LAG_SEC):
                continue
            if oen > 0 and cen > 0 and \
                    abs(cen - oen) > ADOPT_ENTRY_TOL_PCT * max(abs(cen), abs(oen)):
                continue
            hit = i
            break
        if hit is None:
            out.append(o)
        else:
            used.setdefault(key, set()).add(hit)
    return out


def pending_keys(path: str = "logs/journal.jsonl") -> set:
    """Key (cap, huong, qty, gia vao) con OPEN **chua co CLOSE** — B-073/B-078.

    Dung de chan ghi OPEN lan 2 cho CUNG mot vi the: `position_sync.adopt` chay
    lai sau moi lan restart (hoac vong ADOPT dinh ky). Chi DOC journal.
    """
    opens, closes = _load(path)
    return {_group_key(o) for o in _unclosed_opens(opens, closes)}


def rec_key(*, pair: str = "", direction: str = "", qty=0.0, entry=0.0) -> tuple:
    """Key dung y het `_group_key` — de so voi `pending_keys()`."""
    return (str(pair or "?"), str(direction or "").upper(),
            round(_f(qty), 10), round(_f(entry), 10))


def pending_positions(path: str = "logs/journal.jsonl") -> list:
    """[(cap, huong, gia vao)] cua OPEN con **chua co CLOSE** — de so khop MEM (B-076).

    Khac `pending_keys()` (khop TUYET DOI ca qty + gia): o day **bo qty** vi qty tren
    san da giam sau partial trong khi OPEN giu qty ban dau, va gia vao chi can lech
    <= `ADOPT_ENTRY_TOL_PCT` vi journal ghi gia KE HOACH con san tra `entryPrice` THAT.
    Chi DOC journal.
    """
    opens, closes = _load(path)
    return [(_pair(o), _dir(o), _f(o.get("entry")))
            for o in _unclosed_opens(opens, closes)]


def matches_pending(rows, *, pair: str = "", direction: str = "", qty=0.0,
                    entry=0.0, entry_pct: float = ADOPT_ENTRY_TOL_PCT) -> bool:
    """True neu `rows` (tu `pending_positions`) da co vi the nay chua CLOSE.

    So khop: cap + huong, roi gia vao lech <= `entry_pct` (tuong doi). Gia vao khong
    doc duoc (<=0) o MOT trong hai ben ⇒ coi la khop (tranh ghi lap khi thieu du lieu).
    `qty` chi de tuong thich chu ky goi `rec_key` — KHONG dung (xem `pending_positions`).
    """
    want_dir = str(direction or "").upper()
    want_pair = str(pair or "?").strip().upper()
    try:
        want_entry = _f(entry)
    except Exception:  # noqa: BLE001
        want_entry = 0.0
    tol = max(0.0, float(entry_pct))
    for row in rows or ():
        try:
            p, d, e = row
        except (TypeError, ValueError):
            continue
        if str(p or "").strip().upper() != want_pair:
            continue
        if str(d or "").upper() != want_dir:
            continue
        have = _f(e)
        if have <= 0 or want_entry <= 0:
            return True
        if abs(have - want_entry) <= tol * max(abs(have), abs(want_entry)):
            return True
    return False


def log_trade(path: str = "logs/journal.jsonl", **fields) -> dict:
    rec = {"ts": time.time(), **fields}
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _pair(rec: dict) -> str:
    return str(rec.get("pair") or rec.get("symbol") or "?")


def _dir(rec: dict) -> str:
    return str(rec.get("direction") or "").upper()


def _group_key(rec: dict) -> tuple:
    """Nhom OPEN theo (cap, huong, khoi luong, gia vao) — 1 vi the that = 1 bo so."""
    return (_pair(rec), _dir(rec), round(_f(rec.get("qty")), 10),
            round(_f(rec.get("entry")), 10))


def _same_entry(a: float, b: float) -> bool:
    if a <= 0 or b <= 0:
        return a == b
    return abs(a - b) <= max(1e-12, ENTRY_TOL_PCT * max(abs(a), abs(b)))


def find_duplicate_opens(opens: list, closes: list) -> dict:
    """Tim OPEN bi ghi TRUNG (B-073) — thuan tinh toan, khong doc/ghi file.

    Cach lam (KHONG dung FIFO cua monitor_report vi FIFO ghep lech khi thieu
    ban ghi):
      1. Nhom OPEN theo (cap, huong, khoi luong, gia vao).
      2. Trong nhom, gan moi CLOSE cho OPEN GAN NHAT phia truoc (gia vao lech
         <= ENTRY_TOL_PCT, thoi gian <= CLOSE_MAX_LAG_SEC) -> OPEN "da co CLOSE".
      3. OPEN con lai trong nhom:
         - nhom DA co CLOSE ⇒ la ban ghi LAP (bi void);
         - nhom CHUA co CLOSE ⇒ giu ban ghi CU nhat, cac ban ghi sau la LAP.
         Nhom chi co 1 OPEN va khong co CLOSE -> giu nguyen (vi the con mo).
    """
    by_key: dict = {}
    for o in opens:
        by_key.setdefault(_group_key(o), []).append(o)
    cl_by_key: dict = {}
    for c in closes:
        cl_by_key.setdefault(_group_key(c), []).append(c)

    dupes: list = []
    review: list = []
    for key, ops in by_key.items():
        ops = sorted(ops, key=lambda x: _f(x.get("ts")))
        cls = sorted(cl_by_key.get(key) or [], key=lambda x: _f(x.get("ts")))
        free = list(ops)
        bound: list = []
        for c in cls:
            cts = _f(c.get("ts"))
            cen = _f(c.get("entry"))
            pick, best = None, -1.0
            for o in free:
                ots, oen = _f(o.get("ts")), _f(o.get("entry"))
                if ots > cts or cts - ots > CLOSE_MAX_LAG_SEC:
                    continue
                if not _same_entry(oen, cen):
                    continue
                if ots >= best:            # OPEN gan CLOSE nhat (phia truoc)
                    pick, best = o, ots
            if pick is not None:
                free.remove(pick)
                bound.append(pick)
        if bound:
            # Nhom DA co vi the duoc ghi CLOSE ⇒ moi OPEN con lai deu la ban ghi LAP.
            for o in free:
                dupes.append({"open": o, "twin": bound[0]})
        else:
            # Nhom CHUA co CLOSE nao (vi the con mo hoac thieu du lieu): giu ban ghi
            # CU nhat lam dai dien, cac ban ghi sau cung key la LAP. Ban giu lai van
            # bi bao "OPEN chua CLOSE" — dung, vi chua co CLOSE that.
            keep = None
            for o in sorted(free, key=lambda x: _f(x.get("ts"))):
                if keep is None:
                    keep = o
                    continue
                if abs(_f(o.get("ts")) - _f(keep.get("ts"))) < MIN_GAP_SEC:
                    continue
                dupes.append({"open": o, "twin": keep})
    dupes.sort(key=lambda d: _f(d["open"].get("ts")))
    review.sort(key=lambda d: _f(d["open"].get("ts")))
    return {"dupes": dupes, "review": review}



def _rec_id(rec: dict) -> tuple:
    return (_f(rec.get("ts")), _pair(rec), _dir(rec),
            round(_f(rec.get("qty")), 10), round(_f(rec.get("entry")), 12))


def void_records(path: str, targets: list, reason: str = "DUP_OPEN",
                 apply: bool = False) -> dict:
    """Danh dau `void: true` cho cac ban ghi OPEN trung (giu nguyen lich su).

    `targets` = list ban ghi OPEN (lay tu find_duplicate_opens) — so khop theo
    (ts, cap, huong, khoi luong, gia vao). `apply=False` chi dem, khong ghi file.
    """
    want = {_rec_id(t): t for t in targets or []}
    if not want or not os.path.exists(path):
        return {"matched": 0, "unmatched": len(want), "backup": None, "applied": False}
    lines, matched, hit = [], 0, set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except Exception:  # noqa: BLE001
                lines.append(s)
                continue
            rid = _rec_id(rec)
            if rid in want and rid not in hit and rec.get("event") != "CLOSE":
                hit.add(rid)
                matched += 1
                if apply:
                    rec["void"] = True
                    rec["void_reason"] = reason
                    rec["void_at"] = time.time()
                s = json.dumps(rec, ensure_ascii=False)
            lines.append(s)
    bak = None
    if apply and matched:
        bak = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        try:
            with open(path, "r", encoding="utf-8") as src, \
                    open(bak, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        except Exception:  # noqa: BLE001
            bak = None
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for s in lines:
                f.write(s + "\n")
        os.replace(tmp, path)
    return {"matched": matched, "unmatched": len(want) - matched,
            "backup": bak, "applied": bool(apply and matched)}

