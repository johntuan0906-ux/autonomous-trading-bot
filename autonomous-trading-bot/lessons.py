"""Rut kinh nghiem tu journal: ghep OPEN (co feature) voi CLOSE (co ket qua) -> bai hoc.

    from lessons import build, gate_list, notes, write_files
    les = build("logs/journal.jsonl")
    print(notes(les["buckets"], gate_list(les["buckets"])))

Vi sao (13/10, yeu cau nguoi van hanh): "luon hoc hoi nang cao kien thuc qua nhung lan
vao lenh, ghi chu, rut kinh nghiem cho cac lan sau de PnL cao hon". He thong da co
`learner` (logistic online) va `strategy_gate` (bang chung tu backtest), nhung THIEU:
  1. **ghi chu doc duoc cho nguoi** (bai hoc cu the, co so lieu) — khong chi trong so;
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


def load_closed(journal_path) -> list:
    """Doc journal -> danh sach lenh DA DONG kem feature cua lenh OPEN tuong ung.

    Ghep theo cap (pair) kieu FIFO: OPEN truoc, CLOSE sau. OPEN khong co CLOSE (vi the
    dang mo / journal thieu) bi bo qua — khong suy dien ket qua.
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
            t = dict(o)
            t.update({k: d.get(k) for k in ("r", "pnl", "won", "reason",
                                            "mfe_r", "partial", "exit_price")})
            t["pair"] = pair
            t["ts_close"] = d.get("ts")
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


def bucket_stats(trades: list, keys=KEYS_DEFAULT) -> dict:
    """Gom lenh theo to hop dieu kien -> {khoa: {n, wins, sum_r, sum_pnl, avg_r, wr, pf}}.

    HOP NHAT (merge) theo khoa: khong bao gio tao 2 muc gan giong nhau.
    """
    out: dict = {}
    for t in trades or []:
        k = key_of(t, keys)
        b = out.setdefault(k, {"n": 0, "wins": 0, "sum_r": 0.0, "sum_pnl": 0.0,
                               "gross_win": 0.0, "gross_loss": 0.0, "last_ts": 0.0})
        try:
            r = float((t or {}).get("r") or 0.0)
        except (TypeError, ValueError):
            r = 0.0
        try:
            pnl = float((t or {}).get("pnl") or 0.0)
        except (TypeError, ValueError):
            pnl = 0.0
        b["n"] += 1
        b["wins"] += 1 if (t or {}).get("won") else 0
        b["sum_r"] += r
        b["sum_pnl"] += pnl
        if pnl >= 0:
            b["gross_win"] += pnl
        else:
            b["gross_loss"] += -pnl
        b["last_ts"] = max(float(b["last_ts"]), float((t or {}).get("ts_close") or 0.0))
    for b in out.values():
        n = max(1, b["n"])
        b["avg_r"] = round(b["sum_r"] / n, 4)
        b["wr"] = round(100.0 * b["wins"] / n, 1)
        b["pnl"] = round(b["sum_pnl"], 4)
        b["pf"] = round(b["gross_win"] / b["gross_loss"], 3) if b["gross_loss"] > 0 else None
        b["sum_r"] = round(b["sum_r"], 4)
    return out


def gate_list(buckets: dict, *, min_n: int = 20, max_avg_r: float = -0.30) -> list:
    """To hop CAN CHAN: du mau (n >= min_n) VA ky vong am (avg_r <= max_avg_r).

    Nguong phai TAT DINH va cong khai — khong de AI "cam nhan" roi chan lenh.
    Tra list [{key, n, avg_r, pnl, wr}] sap theo avg_r tang dan (te nhat truoc).
    """
    out = []
    for k, b in (buckets or {}).items():
        if int(b.get("n") or 0) < int(min_n):
            continue
        if float(b.get("avg_r") or 0.0) > float(max_avg_r):
            continue
        out.append({"key": k, "n": b["n"], "avg_r": b["avg_r"],
                    "pnl": b.get("pnl", 0.0), "wr": b.get("wr", 0.0)})
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
      blocked : [{key, n, avg_r, pnl}]  — bi chan (avg_r <= max_avg_r); pnl AM = TIET KIEM
      missed  : tap con cua `blocked` co pnl DUONG = bi chan NHAM (mat lai that su)
      near    : avg_r trong (max_avg_r, max_avg_r+near] va pnl DUONG = SAP bi chan, theo doi
      saved_pnl, missed_pnl, net (net am = tranh duoc lo)

    ⚠️ (13/10) Sua loi dinh nghia: ban dau `missed` tinh ca to hop KHONG bi chan
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

    Vi sao (13/10): "siết lessons sau ~1 tuần" can so lieu de quyet, khong phai cam tinh.
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
    """Truc xuat to hop CU -> (giu, truc_xuat) — `/prune` (15/10).

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
    """Ten doc duoc cho 1 ky nang — lay tu KHOA to hop (bucket chi chua so lieu).

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


def build(journal_path, *, keys=KEYS_DEFAULT, cap: int = 60,
          min_n: int = 20, max_avg_r: float = -0.30, stale_days: float = 0.0,
          now=None) -> dict:
    """Doc journal -> {trades, buckets, gates, notes, skills, stale, pruned, ts}.

    `stale_days > 0` -> `/prune`: truc xuat to hop khong con lenh trong N ngay.
    """
    trades = load_closed(journal_path)
    buckets = bucket_stats(trades, keys)
    keep, drop = merge_capped(buckets, cap=cap)
    stale = {}
    if float(stale_days or 0.0) > 0:
        keep, stale = prune_stale(keep, stale_days=stale_days, now=now)
    gates = gate_list(keep, min_n=min_n, max_avg_r=max_avg_r)
    return {"trades": len(trades), "keys": list(keys), "buckets": keep,
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
             "- To hop dieu kien dang theo doi: **%d**" % len(les.get("buckets") or {}),
             "- To hop DANG CHAN (du mau + ky vong am): **%d**" % len(les.get("gates") or []),
             "", "## Rut kinh nghiem", ""]
    lines += ["- %s" % s if not s.startswith(("NEN", "chua")) else "**%s**" % s
              for s in (les.get("notes") or [])]
    lines += ["", "## Ky nang da rut ra (`/evolve`)", ""]
    lines += skills_md(les.get("skills") or [])
    lines += ["", "## To hop dang chan", ""]
    if les.get("gates"):
        lines += ["| To hop | n | avgR | WR | PnL |", "|---|---|---|---|---|"]
        for g in les["gates"]:
            lines.append("| %s | %d | %+.3f | %.0f%% | %+.2f |"
                         % (g["key"], g["n"], g["avg_r"], g["wr"], g["pnl"]))
    else:
        lines.append("(chua co to hop nao du mau + ky vong am)")
    if les.get("pruned"):
        lines += ["", "_Da truc xuat %d to hop it mau (xem `logs/%s`)._"
                  % (len(les["pruned"]), ARCHIVE_NAME)]
    if les.get("stale"):
        lines += ["", "_`/prune`: da truc xuat %d to hop CU (khong con lenh trong N ngay) "
                  "— xem `logs/%s`._" % (len(les["stale"]), ARCHIVE_NAME)]
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
