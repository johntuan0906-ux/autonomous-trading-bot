"""Rut kinh nghiem tu journal: ghep OPEN (co feature) voi CLOSE (co ket qua) -> bai hoc.

    from lessons import build, gate_list, notes, write_files
    les = build("logs/journal.jsonl")
    print(notes(les["buckets"], gate_list(les["buckets"])))

Vi sao (13/10, yeu cau nguoi van hanh): "luon hoc hoi nang cao kien thuc qua nhung lan
vao lenh, ghi chu, rut kinh nghiem cho cac lan sau de PnL cao hon". He thong da co
`learner` (logistic online) va `strategy_gate` (bang chung tu backtest), nhung THIEU:
  1. **ghi chu doc duoc cho nguoi** (bai hoc cu the, co so lieu) â€” khong chi trong so;
  2. **rut kinh nghiem theo TO HOP dieu kien** (strategy x setup x regime x huong),
     khong chi theo 1 truc;
  3. **ky luat bo nho** (lay tu tigerless-labs/autoharness): HOP NHAT thay vi xep
     chong ban gan giong, dem **duoc dung** (applied) khac **chi doc** (viewed), co
     **tran so muc** + **truc xuat vao kho luu tru** (khong xoa), va **khong bao gio
     ghi de phan do NGUOI viet** trong `LESSONS.md`.

Tat ca ham o day THUAN TUY (doc file / tinh toan) -> test duoc, khong goi mang.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

# To hop dieu kien de rut kinh nghiem (co ca trong journal OPEN va luc vao lenh).
KEYS_DEFAULT = ("strategy", "setup_type", "market_regime", "direction")
HUMAN_BEGIN = "<!-- HUMAN -->"
HUMAN_END = "<!-- /HUMAN -->"
ARCHIVE_NAME = "lessons_archive.jsonl"
# (15/10) Bo dem TANG DAN: chi doc phan MOI cua journal (xem `update_state`).
CACHE_NAME = "lessons_cache.json"


def load_closed(journal_path, *, unpaired: str = "mark") -> list:
    """Doc journal -> danh sach lenh DA DONG kem feature cua lenh OPEN tuong ung.

    Ghep theo cap (pair) kieu FIFO: OPEN truoc, CLOSE sau.

    (15/10) `unpaired` â€” lenh CLOSE **khong co OPEN** tuong ung. Do duoc that:
    **91 lenh**, TAT CA deu `reason='DUST'` (don vi the nho / vi the ke thua), vi bot
    khong mo chung bang tin hieu nen khong co OPEN. Ban cu ghep chung voi `{}` => sinh
    to hop GIA `? | ? | ? | ?` (n=84, avgR +0.383): chiem cho trong tran `cap=60` va
    bi xep vao "NEN UU TIEN" â€” mot tin hieu KHONG CO THAT.
      "mark" (mac dinh): van tra ve, gan `origin="no_open"` de `bucket_stats` loai;
      "drop"           : bo han khoi ket qua;
      "ignore"         : giu hanh vi cu (ghep voi {}) â€” chi dung khi can doi chieu.
    """
    try:
        lines = Path(journal_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    pend: dict = {}
    out: list = []
    for ln in lines:
        try:
            d = json.loads(ln)
        except (TypeError, ValueError):
            continue
        ev = str(d.get("event") or "")
        pair = str(d.get("pair") or "")
        if not pair:
            continue
        if ev == "OPEN":
            pend.setdefault(pair, []).append(d)
        elif ev == "CLOSE":
            q = pend.get(pair) or []
            o = q.pop(0) if q else {}
            if not o and str(unpaired) == "drop":
                continue
            t = dict(o)
            t.update({k: d.get(k) for k in ("r", "pnl", "won", "reason",
                                            "mfe_r", "partial", "exit_price")})
            t["pair"] = pair
            t["ts_close"] = d.get("ts")
            if not o and str(unpaired) == "mark":
                t["origin"] = "no_open"
                t.setdefault("direction", d.get("direction"))
            out.append(t)
    return out


def key_of(trade: dict, keys=KEYS_DEFAULT) -> str:
    """Khoa to hop dieu kien -> chuoi (on dinh, de doc)."""
    parts = []
    for k in keys:
        v = (trade or {}).get(k)
        if v is None or v == "":
            v = "?"
        parts.append(str(v))
    return " | ".join(parts)


def bucket_stats(trades: list, keys=KEYS_DEFAULT, *,
                 exclude_origin=("no_open",)) -> dict:
    """Gom lenh theo to hop dieu kien -> {khoa: {n, wins, sum_r, sum_pnl, avg_r, wr, pf}}.

    HOP NHAT (merge) theo khoa: khong bao gio tao 2 muc gan giong nhau.
    (15/10) `exclude_origin`: bo cac lenh khong co OPEN (`origin="no_open"` â€” 91 lenh
    DUST). Khong the rut kinh nghiem tu lenh khong biet vi sao vao.
    """
    out: dict = {}
    skip = {str(x) for x in (exclude_origin or ()) if str(x)}
    for t in trades or []:
        if str((t or {}).get("origin") or "") in skip:
            continue
        k = key_of(t, keys)
        b = out.setdefault(k, _new_bucket())
        _add_to_bucket(b, t)
    for b in out.values():
        _finalize(b)
    return out


#: Dai R hop ly (28/10, B-031) — ngoai dai nay = ban ghi RAC, khong cong vao sum_r.
R_BAND = (-1.6, 5.0)

def _new_bucket() -> dict:
    """Bucket rong (chi chua TONG tich luy, cac truong dan xuat tinh bang `_finalize`)."""
    return {"n": 0, "n_bad_r": 0, "wins": 0, "sum_r": 0.0, "sum_pnl": 0.0,
            "gross_win": 0.0, "gross_loss": 0.0, "last_ts": 0.0}


def _add_to_bucket(b: dict, t: dict) -> dict:
    """Cong don 1 lenh vao bucket â€” MOT dinh nghia duy nhat.

    (15/10) Tach ra de bo dem TANG DAN (`update_cache`) cong don giong het
    `bucket_stats`: neu viet lai lan hai thi hai duong se lech nhau.
    """
    try:
        r = float((t or {}).get("r") or 0.0)
    except (TypeError, ValueError):
        r = 0.0
    # (28/10) B-031: R RAC (r_valid=False hoac ngoai dai) KHONG duoc cong vao sum_r —
    # neu khong `avg_r`/`pf` cua tung to hop dieu kien (va cong chien luoc/learner) la RAC.
    # Van giu `n` (so mau that) va dem rieng so ban ghi bi loai de minh bach.
    if (t or {}).get("r_valid") is False or not (R_BAND[0] <= r <= R_BAND[1]):
        b["n_bad_r"] = int(b.get("n_bad_r") or 0) + 1
        r = 0.0
    try:
        pnl = float((t or {}).get("pnl") or 0.0)
    except (TypeError, ValueError):
        pnl = 0.0
    b["n"] = int(b.get("n") or 0) + 1
    b["wins"] = int(b.get("wins") or 0) + (1 if (t or {}).get("won") else 0)
    b["sum_r"] = float(b.get("sum_r") or 0.0) + r
    b["sum_pnl"] = float(b.get("sum_pnl") or 0.0) + pnl
    if pnl >= 0:
        b["gross_win"] = float(b.get("gross_win") or 0.0) + pnl
    else:
        b["gross_loss"] = float(b.get("gross_loss") or 0.0) + (-pnl)
    b["last_ts"] = max(float(b.get("last_ts") or 0.0),
                       float((t or {}).get("ts_close") or 0.0))
    return b


def _finalize(b: dict) -> dict:
    """Tinh cac truong dan xuat (avg_r / wr / pnl / pf) tu tong tich luy."""
    n = max(1, int(b.get("n") or 0))
    b["avg_r"] = round(float(b.get("sum_r") or 0.0) / n, 4)
    b["wr"] = round(100.0 * float(b.get("wins") or 0) / n, 1)
    b["pnl"] = round(float(b.get("sum_pnl") or 0.0), 4)
    gl = float(b.get("gross_loss") or 0.0)
    b["pf"] = round(float(b.get("gross_win") or 0.0) / gl, 3) if gl > 0 else None
    b["sum_r"] = round(float(b.get("sum_r") or 0.0), 4)
    return b


def evidence_code(key: str) -> str:
    """Ma bang chung ON DINH cho 1 to hop dieu kien (vd `EV-3F2A9C`).

    (19/10, REPO_IDEAS §15.3 "knowledge warehouse chuan chi"): de tham chieu 1 ket luan
    (`B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG`) trong CONTEXT.md / tin nhan / phieu hoi
    dong bang 1 ma NGAN, tra cuu lai duoc — thay vi chep lai chuoi khoa (de go sai).
    """
    import hashlib
    return "EV-%s" % hashlib.sha1(str(key or "").encode("utf-8")).hexdigest()[:6].upper()


def evidence(journal_path, key: str, *, keys=KEYS_DEFAULT, limit: int = 3) -> dict:
    """BANG CHUNG that cho 1 to hop: n, thang/thua, avg_r, pnl, moc thoi gian, mau lenh.

    Doc lai tu JOURNAL (nguon su that) chu KHONG lay tu `lessons.json` — de moi con so trong
    `LESSONS.md` luon TRUY NGUOC duoc ve tung lenh cu the (yeu cau provenance, 19/10).
    Tra kem `worst`/`best`: ke ca lenh TOT NHAT cung am thi ket luan "nên chặn" mới vững.
    """
    rows = [t for t in load_closed(journal_path)
            if str((t or {}).get("origin") or "") != "no_open"
            and key_of(t, keys) == str(key)]

    def _f(x, k):
        try:
            return float((x or {}).get(k) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    n = len(rows)
    wins = sum(1 for t in rows if (t or {}).get("won"))
    sum_r = sum(_f(t, "r") for t in rows)
    pnl = sum(_f(t, "pnl") for t in rows)
    ts = [_f(t, "ts_close") or _f(t, "ts") for t in rows]
    samp = lambda xs: [{"ts": _f(t, "ts_close") or _f(t, "ts"), "r": round(_f(t, "r"), 4),  # noqa: E731
                        "pnl": round(_f(t, "pnl"), 4), "won": bool((t or {}).get("won")),
                        "reason": (t or {}).get("reason")}
                       for t in xs]
    by_r = sorted(rows, key=lambda t: _f(t, "r"))
    return {"key": str(key), "code": evidence_code(key), "n": n, "wins": wins,
            "losses": n - wins, "avg_r": round(sum_r / n, 4) if n else None,
            "pnl": round(pnl, 4), "first_ts": min(ts) if ts else 0.0,
            "last_ts": max(ts) if ts else 0.0,
            "span_days": round((max(ts) - min(ts)) / 86400.0, 2) if len(ts) > 1 else 0.0,
            "worst": samp(by_r[:limit]), "best": samp(list(reversed(by_r[-limit:])))}


def gate_list(buckets: dict, *, min_n: int = 20, max_avg_r: float = -0.30) -> list:
    """To hop CAN CHAN: du mau (n >= min_n) VA ky vong am (avg_r <= max_avg_r).

    Nguong phai TAT DINH va cong khai â€” khong de AI "cam nhan" roi chan lenh.
    Tra list [{key, n, avg_r, pnl, wr}] sap theo avg_r tang dan (te nhat truoc).
    """
    out = []
    for k, b in (buckets or {}).items():
        if int(b.get("n") or 0) < int(min_n):
            continue
        if float(b.get("avg_r") or 0.0) > float(max_avg_r):
            continue
        out.append({"key": k, "n": b["n"], "avg_r": b["avg_r"],
                    "pnl": b.get("pnl", 0.0), "wr": b.get("wr", 0.0),
                    "code": evidence_code(k)})
    return sorted(out, key=lambda x: x["avg_r"])


def notes(buckets: dict, gates: list, *, top: int = 8, min_n: int = 5) -> list:
    """Bai hoc doc duoc cho NGUOI: cau tieng Viet + so lieu (khong phai JSON).

    `min_n` nho hon nguong chan de van ghi chu duoc to hop "co dau hieu xau nhung
    chua du mau" (de lan sau theo doi tiep).
    """
    rows = [{"key": k, **{f: b.get(f) for f in ("n", "avg_r", "wr", "pnl", "pf")}}
            for k, b in (buckets or {}).items() if int(b.get("n") or 0) >= min_n]
    worst = sorted(rows, key=lambda x: float(x["avg_r"]))[:top]
    best = sorted(rows, key=lambda x: -float(x["avg_r"]))[:top]
    gk = {g["key"] for g in (gates or [])}
    out = []
    if worst:
        out.append("NEN TRANH (ky vong am):")
        for r in worst:
            tag = "  [DANG CHAN]" if r["key"] in gk else ""
            out.append("  - %s: n=%d avgR=%+.3f WR=%.0f%% PnL=%+.2f%s"
                       % (r["key"], r["n"], r["avg_r"], r["wr"], r["pnl"], tag))
    if best:
        out.append("NEN UU TIEN (ky vong duong):")
        for r in best:
            if float(r["avg_r"]) <= 0:
                continue
            out.append("  - %s: n=%d avgR=%+.3f WR=%.0f%% PnL=%+.2f"
                       % (r["key"], r["n"], r["avg_r"], r["wr"], r["pnl"]))
    if not out:
        out.append("chua du mau de rut kinh nghiem (can n >= %d cho 1 to hop)" % min_n)
    return out


def merge_capped(buckets: dict, *, cap: int = 60) -> tuple:
    """Giu `cap` to hop co nhieu mau nhat; phan con lai -> (giu, truc xuat).

    Ky luat autoharness: bo nho KHONG phinh vo han; muc bi bo **luu vao kho** (khong xoa).
    """
    items = sorted((buckets or {}).items(), key=lambda kv: -int(kv[1].get("n") or 0))
    keep = dict(items[:max(0, int(cap))])
    drop = dict(items[max(0, int(cap)):])
    return keep, drop


def human_section(md_text: str) -> str:
    """Trich nguyen van phan do NGUOI viet giua 2 marker (rong neu khong co).

    Quy tac autoharness: lop tu hoc KHONG bao gio sua muc do nguoi viet.
    """
    s = str(md_text or "")
    i = s.find(HUMAN_BEGIN)
    j = s.find(HUMAN_END)
    if i < 0 or j < 0 or j < i:
        return ""
    return s[i + len(HUMAN_BEGIN):j].strip("\n")


def impact(buckets: dict, *, min_n: int = 20, max_avg_r: float = -0.20,
           near: float = 0.10) -> dict:
    """Cong nay CHAN gi (tiet kiem) va BO LO gi (lenh thang bi chan nham)?

    Ham thuan -> test duoc. Tra:
      blocked : [{key, n, avg_r, pnl}]  â€” bi chan (avg_r <= max_avg_r); pnl AM = TIET KIEM
      missed  : tap con cua `blocked` co pnl DUONG = bi chan NHAM (mat lai that su)
      near    : avg_r trong (max_avg_r, max_avg_r+near] va pnl DUONG = SAP bi chan, theo doi
      saved_pnl, missed_pnl, net (net am = tranh duoc lo)

    âš ï¸ (13/10) Sua loi dinh nghia: ban dau `missed` tinh ca to hop KHONG bi chan
    (avg_r > max_avg_r) => con so "bo lo" phong dai, khuyen nghi nguong SAI.
    Chi to hop BI CHAN ma co lai moi la mat mat that su.
    """
    blocked, missed, near_list = [], [], []
    for k, b in (buckets or {}).items():
        n = int(b.get("n") or 0)
        if n < int(min_n):
            continue
        avg = float(b.get("avg_r") or 0.0)
        pnl = float(b.get("pnl") or 0.0)
        row = {"key": k, "n": n, "avg_r": avg, "pnl": pnl}
        if avg <= float(max_avg_r):
            blocked.append(row)
            if pnl > 0:
                missed.append(row)              # bi chan nhung co lai = mat that su
        elif avg <= float(max_avg_r) + float(near) and pnl > 0:
            near_list.append(row)               # sap bi chan -> theo doi
    saved = round(sum(r["pnl"] for r in blocked if r["pnl"] < 0), 2)
    lost = round(sum(r["pnl"] for r in missed), 2)
    return {"blocked": sorted(blocked, key=lambda x: x["avg_r"]),
            "missed": sorted(missed, key=lambda x: -x["pnl"]),
            "near": sorted(near_list, key=lambda x: -x["pnl"]),
            "saved_pnl": saved, "missed_pnl": lost, "net": round(saved - lost, 2)}


def sweep(buckets: dict, *, thresholds=(-0.05, -0.10, -0.15, -0.20, -0.25, -0.30),
          min_n: int = 20, near: float = 0.10) -> list:
    """Quet nguong `max_avg_r` -> moi nguong tiet kiem/bo lo bao nhieu (ham thuan).

    Vi sao (13/10): "siáº¿t lessons sau ~1 tuáº§n" can so lieu de quyet, khong phai cam tinh.
    Moi dong: {max_avg_r, n_blocked, saved_pnl, missed_pnl, net, keys}
    """
    out = []
    for t in thresholds:
        imp = impact(buckets, min_n=min_n, max_avg_r=float(t), near=near)
        out.append({"max_avg_r": float(t),
                    "n_blocked": len(imp["blocked"]),
                    "saved_pnl": imp["saved_pnl"],
                    "missed_pnl": imp["missed_pnl"],
                    "net": imp["net"],
                    "keys": [r["key"] for r in imp["blocked"]]})
    return out


def best_threshold(rows: list) -> dict:
    """Nguong co NET tot nhat (am nhat = tranh lo nhieu nhat). Tra {} neu rong."""
    if not rows:
        return {}
    return min(rows, key=lambda r: float(r.get("net") or 0.0))


def prune_stale(buckets: dict, *, stale_days: float = 30.0, now=None,
                min_n: int = 1) -> tuple:
    """Truc xuat to hop CU -> (giu, truc_xuat) â€” `/prune` (15/10).

    Vi sao: `turbo_demo.lessons_gate()` **tinh lai gate tu `buckets`** trong
    `logs/lessons.json` (bo qua truong `gates`), nen mot to hop xau tu thang 8 van
    chan lenh mai. Do duoc: `SKIP_LESSON` ban 11-13 lan/vong ma khong hoc them duoc gi.

    Quy tac: giu neu con lenh trong `stale_days`; truc xuat neu `last_ts` cu hon
    (hoac `n < min_n`). Muc truc xuat **luu vao kho**, khong xoa.
    """
    now = time.time() if now is None else float(now)
    cut = now - float(stale_days) * 86400.0
    keep, drop = {}, {}
    for k, b in (buckets or {}).items():
        ts = float((b or {}).get("last_ts") or 0.0)
        if int((b or {}).get("n") or 0) < int(min_n):
            drop[k] = dict(b, prune_reason="qua it mau (n<%d)" % min_n)
        elif ts and ts < cut:
            drop[k] = dict(b, prune_reason="khong con lenh trong %d ngay" % int(stale_days))
        else:
            keep[k] = b
    return keep, drop


def _skill_name(b: dict, kind: str) -> str:
    """Ten doc duoc cho 1 ky nang â€” lay tu KHOA to hop (bucket chi chua so lieu).

    (15/10) Loi that: ban dau doc `strategy/setup_type/...` tu bucket -> luon ra
    `"tranh: ?"` vi bucket KHONG co cac truong do; to hop nam trong **khoa** dang
    `"strategy | setup | regime | huong"` (xem `key_of`).
    """
    k = str((b or {}).get("key") or "")
    parts = [p.strip() for p in k.split("|")]
    parts = [p for p in parts if p and p not in ("?", "NONE")]
    return "%s: %s" % (kind, " / ".join(parts) if parts else (k or "?"))


def evolve(buckets: dict, *, min_n: int = 5, top: int = 6, keys=KEYS_DEFAULT) -> list:
    """Gom to hop thanh **KY NANG co ten** (`/evolve`, 15/10).

    Y tuong: thay vi 1 danh sach 60 to hop roi rac, rut ra vai ky nang doc duoc:
      - `tranh`    : avgR < 0, du mau  -> quy tac "dung vao"
      - `uu_tien`  : avgR > 0, du mau  -> quy tac "nen vao"
    Xep hang theo "tac dong" = |avgR| * n (to hop vua xau vua nhieu lenh len truoc).
    Ham THUAN TUY -> test duoc.
    """
    out = []
    for k, b in (buckets or {}).items():
        n = int((b or {}).get("n") or 0)
        if n < int(min_n):
            continue
        r = float((b or {}).get("avg_r") or 0.0)
        if r == 0.0:
            continue
        t = dict(b)
        t["key"] = k
        t["kind"] = "uu_tien" if r > 0 else "tranh"
        t["name"] = _skill_name(t, t["kind"])
        t["impact"] = round(abs(r) * n, 4)
        out.append(t)
    out.sort(key=lambda x: -float(x["impact"]))
    return out[:max(0, int(top))]


def skills_md(skills: list) -> list:
    """Dong markdown cho phan KY NANG trong `LESSONS.md`."""
    if not skills:
        return ["(chua du mau de rut ra ky nang nao)"]
    lines = ["| Ky nang | loai | n | avgR | WR | PnL |", "|---|---|---|---|---|---|"]
    for s in skills:
        lines.append("| %s | %s | %d | %+.3f | %.0f%% | %+.2f |"
                     % (s["name"], s["kind"], s["n"], s["avg_r"], s["wr"], s["pnl"]))
    return lines


def tree(buckets: dict, keys=KEYS_DEFAULT) -> dict:
    """Cay tri thuc: strategy -> setup_type -> market_regime -> direction.

    (15/10) Y tuong `volcengine/OpenViking` (tri thuc dang CAY, truy hoi theo PHAM VI
    thay vi nhieu het vao prompt) + `rohitg00/agentmemory` (nho phan cap).

    So lieu vao **NUT LA**, roi cong nguoc len cac nut cha (`_finalize_tree`) â€” nho vay
    nut cha luon = tong cac con, khong bi dem hai lan. Ham THUAN TUY -> test duoc.
    """
    root = {**_new_bucket(), "children": {}}
    for k, b in (buckets or {}).items():
        parts = [p.strip() for p in str(k).split("|") if p.strip()]
        node = root
        for p in parts:
            node = node["children"].setdefault(p, {**_new_bucket(), "children": {}})
        _merge_bucket(node, b)
    _finalize_tree(root)
    return root


def _merge_bucket(dst: dict, src: dict) -> dict:
    """Cong don so lieu cua 1 bucket (n/wins/tong/last_ts) vao nut hoac bucket khac."""
    for f in ("n", "wins"):
        dst[f] = int(dst.get(f) or 0) + int((src or {}).get(f) or 0)
    for f in ("sum_r", "sum_pnl", "gross_win", "gross_loss"):
        dst[f] = float(dst.get(f) or 0.0) + float((src or {}).get(f) or 0.0)
    dst["last_ts"] = max(float(dst.get("last_ts") or 0.0),
                         float((src or {}).get("last_ts") or 0.0))
    return dst


def _finalize_tree(node: dict) -> None:
    """Tinh lai cac truong dan xuat tu DUOI LEN: nut cha = tong cac con."""
    kids = node.get("children") or {}
    if kids:
        agg = _new_bucket()
        for c in kids.values():
            _finalize_tree(c)
            _merge_bucket(agg, c)
        node.update(agg)
    _finalize(node)


def relevant(buckets: dict, *, strategy="", setup="", regime="", direction="",
             max_nodes: int = 5, min_n: int = 5) -> list:
    """To hop LIEN QUAN NHAT voi ngu canh hien tai (thay vi nhieu ca 60 to hop).

    Xep hang: so chieu khop (strategy/setup/regime/huong) TRUOC, roi tac dong |avgR|*n.
    `blocked` = dang bi cong lessons chan (avgR <= nguong am thong dung).
    """
    want = [str(strategy or "").strip().upper(), str(setup or "").strip().upper(),
            str(regime or "").strip().upper(), str(direction or "").strip().upper()]
    out = []
    for k, b in (buckets or {}).items():
        n = int((b or {}).get("n") or 0)
        if n < int(min_n):
            continue
        parts = [p.strip().upper() for p in str(k).split("|")]
        hits = sum(1 for i, w in enumerate(want)
                   if w and w not in ("?", "NONE") and i < len(parts) and parts[i] == w)
        r = float((b or {}).get("avg_r") or 0.0)
        out.append({"key": k, "n": n, "avg_r": r,
                    "wr": float((b or {}).get("wr") or 0.0),
                    "pnl": float((b or {}).get("pnl") or 0.0),
                    "hits": hits, "blocked": r <= -0.05, "impact": abs(r) * n})
    out.sort(key=lambda x: (-x["hits"], -x["impact"]))
    return out[:max(0, int(max_nodes))]


def hint(buckets: dict, *, strategy="", setup="", regime="", direction="",
         max_nodes: int = 5, max_chars: int = 110) -> list:
    """Chuoi NGAN ve cac to hop lien quan -> nhoi vao prompt hoi dong.

    (15/10) Truoc day hoi dong quyet dinh **MU**: `setup_payload` khong co truong nao ve
    lessons, nen no khong bao gio thay bang chung tich luy (giai thich phan nao vi sao
    gia tri do duoc ~0).

    TRAN TOKEN: toi da `max_nodes` muc, moi muc <= `max_chars` ky tu.
    Vi sao la LIST chuoi ngan (khong phai 1 chuoi dai): `prompt_guard.MAX_TEXT = 120` cat
    TUNG truong chuoi â€” chuoi dai se bi cat cut, con list thi giu duoc day du.
    """
    out = []
    for r in relevant(buckets, strategy=strategy, setup=setup, regime=regime,
                      direction=direction, max_nodes=max_nodes):
        s = "%s n=%d avgR=%+.3f WR=%.0f%%" % (r["key"], r["n"], r["avg_r"], r["wr"])
        if r["blocked"]:
            s += " [DANG CHAN]"
        out.append(s[:max(20, int(max_chars))])
    return out


def read_state(path) -> dict:
    """Doc trang thai bo dem tang dan (rong neu chua co / hong)."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path, state: dict) -> str:
    """Ghi trang thai bo dem (nguyen tu: ghi file tam roi thay the)."""
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)
        return str(p)
    except OSError:
        return ""


def update_state(state: dict, journal_path, *, keys=KEYS_DEFAULT,
                 unpaired: str = "mark") -> dict:
    """Doc **chi phan MOI** cua journal va cong don vao `state` -> state moi.

    (15/10) Y tuong `Egonex-AI/Understand-Anything` + `abhigyanpatwari/GitNexus`:
    cap nhat TANG DAN theo fingerprint thay vi parse lai toan bo. Journal chi them o
    cuoi (append-only), nen chi can doc tu byte cuoi da doc.

    Fingerprint = (size, offset): neu file NHO hon offset (bi xoay vong / ghi de) thi
    **reset** va doc lai tu dau — khong bao gio tin offset cu mot cach mu quang.
    Chi tieu thu toi dau dong CUOI CUNG (dong dang ghi do khong duoc tinh).

    Tra state: {offset, size, buckets, pend, n_closed, n_unpaired, keys, resets}
    """
    p = Path(journal_path)
    try:
        size = p.stat().st_size
    except OSError:
        return state
    st = dict(state or {})
    if not st.get("buckets"):
        st = {"offset": 0, "size": 0, "buckets": {}, "pend": {},
              "n_closed": 0, "n_unpaired": 0, "keys": list(keys), "resets": 0}
    offset = int(st.get("offset") or 0)
    if size < offset:                      # journal bi xoay vong/ghi de -> doc lai tu dau
        st.update({"offset": 0, "buckets": {}, "pend": {}, "n_closed": 0,
                   "n_unpaired": 0, "resets": int(st.get("resets") or 0) + 1})
        offset = 0
    if size == offset and int(st.get("size") or -1) == size:
        return st                          # khong co gi moi
    try:
        with open(p, "rb") as f:
            f.seek(offset)
            chunk = f.read()
    except OSError:
        return st
    cut = chunk.rfind(b"\n")
    if cut < 0:                            # chua co dong nao hoan chinh
        st["size"] = size
        return st
    body, new_off = chunk[:cut + 1], offset + cut + 1
    pend = {k: list(v) for k, v in (st.get("pend") or {}).items()}
    buckets = st.get("buckets") or {}
    n_closed = int(st.get("n_closed") or 0)
    n_unpaired = int(st.get("n_unpaired") or 0)
    for ln in body.decode("utf-8", errors="replace").splitlines():
        try:
            d = json.loads(ln)
        except (TypeError, ValueError):
            continue
        ev = str(d.get("event") or "")
        pair = str(d.get("pair") or "")
        if not pair:
            continue
        if ev == "OPEN":
            pend.setdefault(pair, []).append(d)
        elif ev == "CLOSE":
            q = pend.get(pair) or []
            o = q.pop(0) if q else {}
            n_closed += 1
            t = dict(o)
            t.update({k: d.get(k) for k in ("r", "pnl", "won", "reason",
                                            "mfe_r", "partial", "exit_price")})
            t["pair"] = pair
            t["ts_close"] = d.get("ts")
            if not o:                      # CLOSE khong co OPEN -> KHONG vao thong ke
                n_unpaired += 1
                if str(unpaired) == "ignore":       # chi khi doi chieu hanh vi cu
                    _add_to_bucket(buckets.setdefault(key_of(t, keys), _new_bucket()), t)
                continue
            k = key_of(t, keys)
            _add_to_bucket(buckets.setdefault(k, _new_bucket()), t)
    st.update({"offset": new_off, "size": size, "buckets": buckets, "pend": pend,
               "n_closed": n_closed, "n_unpaired": n_unpaired, "keys": list(keys)})
    return st


def build_from_state(state: dict, *, cap: int = 60, min_n: int = 20,
                     max_avg_r: float = -0.30, stale_days: float = 0.0,
                     now=None) -> dict:
    """Ket qua GIONG `build()` nhung tu bo dem tang dan (khong doc lai journal)."""
    import copy
    buckets = copy.deepcopy(state.get("buckets") or {})
    for b in buckets.values():
        _finalize(b)
    keep, drop = merge_capped(buckets, cap=cap)
    stale = {}
    if float(stale_days or 0.0) > 0:
        keep, stale = prune_stale(keep, stale_days=stale_days, now=now)
    gates = gate_list(keep, min_n=min_n, max_avg_r=max_avg_r)
    return {"trades": int(state.get("n_closed") or 0) - int(state.get("n_unpaired") or 0),
            "unpaired": int(state.get("n_unpaired") or 0),
            "keys": list(state.get("keys") or KEYS_DEFAULT), "buckets": keep,
            "gates": gates, "notes": notes(keep, gates), "skills": evolve(keep),
            "stale": {k: v.get("prune_reason") for k, v in (stale or {}).items()},
            "pruned": list(drop.keys()), "ts": time.time(),
            "incremental": {"offset": state.get("offset"), "resets": state.get("resets", 0)}}


def build(journal_path, *, keys=KEYS_DEFAULT, cap: int = 60,
          min_n: int = 20, max_avg_r: float = -0.30, stale_days: float = 0.0,
          now=None, include_unpaired: bool = False) -> dict:
    """Doc journal -> {trades, unpaired, buckets, gates, notes, skills, stale, pruned, ts}.

    `stale_days > 0` -> `/prune`: truc xuat to hop khong con lenh trong N ngay.
    (15/10) Lenh CLOSE khong co OPEN (91 lenh DUST) bi LOAI khoi thong ke nhung van
    duoc DEM RIENG o `unpaired` â€” khong am tham bo qua.
    """
    trades = load_closed(journal_path,
                         unpaired=("ignore" if include_unpaired else "mark"))
    unpaired = sum(1 for t in (trades or []) if t.get("origin") == "no_open")
    buckets = bucket_stats(trades, keys)
    keep, drop = merge_capped(buckets, cap=cap)
    stale = {}
    if float(stale_days or 0.0) > 0:
        keep, stale = prune_stale(keep, stale_days=stale_days, now=now)
    gates = gate_list(keep, min_n=min_n, max_avg_r=max_avg_r)
    return {"trades": len(trades or []) - unpaired, "unpaired": unpaired,
            "keys": list(keys), "buckets": keep,
            "gates": gates, "notes": notes(keep, gates),
            "skills": evolve(keep),
            "stale": {k: v.get("prune_reason") for k, v in (stale or {}).items()},
            "pruned": list(drop.keys()), "ts": time.time()}


def write_files(les: dict, *, json_path="logs/lessons.json",
                md_path="LESSONS.md", archive_path=None) -> dict:
    """Ghi `logs/lessons.json` (may doc) + `LESSONS.md` (nguoi doc). Tra bao cao.

    Phan giua 2 marker `<!-- HUMAN -->` trong LESSONS.md duoc GIU NGUYEN.
    """
    json_path, md_path = Path(json_path), Path(md_path)
    try:
        old = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        old = ""
    human = human_section(old)
    lines = ["# BAI HOC TU JOURNAL (tu dong)", "",
             "> Sinh boi `python tools/learn_review.py`. Nguong chan: xem `logs/lessons.json`.",
             "> Muc do NGUOI viet nam trong 2 marker `<!-- HUMAN -->` se KHONG bi ghi de.",
             "", "## So lieu", "",
             "- So lenh da dong doc duoc: **%d**" % int(les.get("trades") or 0),
             "- To hop DIEU KIEN dang theo doi: **%d**" % len(les.get("buckets") or {}),
             "- Lenh CLOSE khong co OPEN (DUST / ke thua) â€” DA LOAI khoi thong ke: **%d**"
             % int(les.get("unpaired") or 0),
             "- To hop DANG CHAN (du mau + ky vong am): **%d**" % len(les.get("gates") or []),
             "", "## Rut kinh nghiem", ""]
    lines += ["- %s" % s if not s.startswith(("NEN", "chua")) else "**%s**" % s
              for s in (les.get("notes") or [])]
    lines += ["", "## Ky nang da rut ra (`/evolve`)", ""]
    lines += skills_md(les.get("skills") or [])
    lines += ["", "## To hop dang chan", ""]
    if les.get("gates"):
        lines += ["| Mã | To hop | n | avgR | WR | PnL |", "|---|---|---|---|---|---|"]
        for g in les["gates"]:
            lines.append("| %s | %s | %d | %+.3f | %.0f%% | %+.2f |"
                         % (g.get("code") or evidence_code(g.get("key", "")),
                            g["key"], g["n"], g["avg_r"], g["wr"], g["pnl"]))
        lines += ["", "_Truy nguoc bang chung cua 1 ma (vd `%s`):_"
                  " `python tools/trace_trade.py --key \"<to hop>\"`"
                  % (les["gates"][0].get("code") or evidence_code(les["gates"][0]["key"]))]
    else:
        lines.append("(chua co to hop nao du mau + ky vong am)")
    if les.get("pruned"):
        lines += ["", "_Da truc xuat %d to hop it mau (xem `logs/%s`)._"
                  % (len(les["pruned"]), ARCHIVE_NAME)]
    if les.get("stale"):
        lines += ["", "_`/prune`: da truc xuat %d to hop CU (khong con lenh trong N ngay) "
                  "â€” xem `logs/%s`._" % (len(les["stale"]), ARCHIVE_NAME)]
    lines += ["", "## Ghi chu cua nguoi van hanh", "", HUMAN_BEGIN, human, HUMAN_END, ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(les, ensure_ascii=False, indent=2), encoding="utf-8")
    n_arch = 0
    if archive_path and (les.get("pruned") or les.get("stale")):
        with open(Path(archive_path), "a", encoding="utf-8") as f:
            for k in les["pruned"]:
                f.write(json.dumps({"ts": les.get("ts"), "key": k,
                                    "reason": "it mau"}, ensure_ascii=False) + "\n")
                n_arch += 1
            for k, why in (les.get("stale") or {}).items():
                f.write(json.dumps({"ts": les.get("ts"), "key": k,
                                    "reason": why}, ensure_ascii=False) + "\n")
                n_arch += 1
    return {"json": str(json_path), "md": str(md_path), "archived": n_arch,
            "human_kept": bool(human)}
