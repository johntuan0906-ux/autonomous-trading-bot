"""TỰ LOẠI BỎ VĨNH VIỄN các cặp thua lỗ dài hạn và gỡ khỏi `.env`.

    python pair_audit.py                  # kiem tra + ban (ghi logs/banned_pairs.json + .env)
    python pair_audit.py --dry-run        # chi bao, khong ghi
    python pair_audit.py --target live    # chi instance LIVE
    python pair_audit.py --days 30 --min-n 30 --max-avgr 0.0 --max-pf 1.0

Quy tắc BAN (tất định, kèm bằng chứng):
    `n >= MIN_N`  AND  `avg_r <= MAX_AVGR`  AND  `pf_r < MAX_PF`   → **BAN vĩnh viễn**
(đã đủ mẫu + trung bình R không dương + PF < 1 = thua ròng dài hạn)

Kết quả: cặp được ghi vào `logs/banned_pairs.json` (kèm số liệu làm bằng chứng) và bị
**gỡ khỏi `SYMBOLS`/`EXTRA_SYMBOLS` trong `.env`**. `tools/apply_symbols.py` luôn đọc file
ban này ⇒ cặp đã bị loại **không thể quay lại** dù nạp lại danh sách đầy đủ.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE_DIR = ROOT.parent / "atb-live"
DEFAULT_MIN_N = 30
DEFAULT_MAX_AVGR = 0.0
DEFAULT_MAX_PF = 1.0


def load_closes(journal: Path, days: float = 0.0) -> list:
    """Các bản ghi CLOSE (có `r`) của journal; `days>0` thì chỉ lấy N ngày gần nhất."""
    out: list = []
    if not journal.exists():
        return out
    since = (time.time() - days * 86400.0) if days else 0.0
    with open(journal, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("event") != "CLOSE" and "r" not in rec:
                continue
            if rec.get("r") is None:
                continue
            if since and float(rec.get("ts") or 0.0) < since:
                continue
            out.append(rec)
    return out


def pair_stats(closes: list) -> dict:
    """`{pair: {n, wins, wr, avg_r, pf_r, total_r}}` — thuần túy, test được."""
    acc: dict = {}
    for c in closes:
        key = c.get("pair") or c.get("symbol") or "?"
        if c.get("r") is None:            # ban ghi khong co R -> bo qua (khong tinh la hoa)
            continue
        try:
            r = float(c.get("r") or 0.0)
        except (TypeError, ValueError):
            continue
        a = acc.setdefault(key, {"n": 0, "wins": 0, "gain": 0.0, "loss": 0.0, "total": 0.0})
        a["n"] += 1
        a["total"] += r
        if r > 0:
            a["wins"] += 1
            a["gain"] += r
        elif r < 0:
            a["loss"] += abs(r)
    out: dict = {}
    for k, a in acc.items():
        out[k] = {"n": a["n"], "wins": a["wins"],
                  "wr": round(100.0 * a["wins"] / a["n"], 1),
                  "avg_r": round(a["total"] / a["n"], 4),
                  "pf_r": round(a["gain"] / a["loss"], 3) if a["loss"] > 1e-9
                          else (999.0 if a["gain"] > 0 else 0.0),
                  "total_r": round(a["total"], 3)}
    return out


def decide_bans(stats: dict, *, min_n: int = DEFAULT_MIN_N,
                max_avgr: float = DEFAULT_MAX_AVGR, max_pf: float = DEFAULT_MAX_PF) -> list:
    """Danh sách `(pair, reason, stats)` cần BAN — tất định, có bằng chứng."""
    out: list = []
    for pair, st in sorted(stats.items()):
        if pair in ("?", ""):
            continue
        if (int(st["n"]) >= int(min_n) and float(st["avg_r"]) <= float(max_avgr)
                and float(st["pf_r"]) < float(max_pf)):
            out.append((pair, ("n=%d >= %d, avgR=%+.3f <= %.2f, PF(R)=%.3f < %.2f"
                               % (st["n"], min_n, st["avg_r"], max_avgr,
                                  st["pf_r"], max_pf)), st))
    return out


def load_banned(target: Path) -> dict:
    p = target / "logs" / "banned_pairs.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def save_banned(target: Path, banned: dict) -> Path:
    p = target / "logs" / "banned_pairs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(banned, ensure_ascii=False, indent=1, sort_keys=True),
                 encoding="utf-8")
    return p


def strip_from_env(target: Path, banned: set) -> dict:
    """Gỡ các cặp bị ban khỏi `SYMBOLS`/`EXTRA_SYMBOLS` trong `.env` của instance."""
    import state_sync as SS
    envp = target / ".env"
    if not envp.exists() or not banned:
        return {"ok": False, "err": "khong co .env hoac khong co cap bi ban"}
    txt = envp.read_text(encoding="utf-8")
    cur: list = []
    for key in ("SYMBOLS", "EXTRA_SYMBOLS"):
        m = None
        for line in txt.splitlines():
            if line.startswith(key + "="):
                m = line.split("=", 1)[1]
                break
        if m:
            cur += [s.strip() for s in m.split(",") if s.strip()]
    keep = [s for s in dict.fromkeys(cur) if s not in banned]
    envp.write_text(SS.set_env_values(txt, {"SYMBOLS": ",".join(keep), "EXTRA_SYMBOLS": ""}),
                    encoding="utf-8")
    return {"ok": True, "before": len(cur), "after": len(keep),
            "removed": sorted(set(cur) & set(banned))}


def audit_one(name: str, target: Path, *, days: float, min_n: int, max_avgr: float,
              max_pf: float, dry_run: bool) -> dict:
    closes = load_closes(target / "logs" / "journal.jsonl", days)
    st = pair_stats(closes)
    bans = decide_bans(st, min_n=min_n, max_avgr=max_avgr, max_pf=max_pf)
    old = load_banned(target)
    new = dict(old)
    for pair, reason, s in bans:
        new[pair] = {"reason": reason, "n": s["n"], "avg_r": s["avg_r"], "pf_r": s["pf_r"],
                     "total_r": s["total_r"], "ts": round(time.time(), 1),
                     "banned_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    res = {"mode": name, "n_close": len(closes), "n_pair": len(st),
           "ban_moi": [p for p, _r, _s in bans], "da_ban_truoc": sorted(old)}
    if bans and not dry_run:
        save_banned(target, new)
        res["env"] = strip_from_env(target, set(new))
    return res


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ban vinh vien cap thua dai han")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--days", type=float, default=0.0, help="0 = ca lich su")
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--max-avgr", type=float, default=DEFAULT_MAX_AVGR)
    ap.add_argument("--max-pf", type=float, default=DEFAULT_MAX_PF)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    sys.path.insert(0, str(ROOT))
    targets = []
    if args.target in ("both", "testnet"):
        targets.append(("TESTNET", ROOT))
    if args.target in ("both", "live"):
        targets.append(("LIVE", LIVE_DIR))
    for name, d in targets:
        r = audit_one(name, d, days=args.days, min_n=args.min_n, max_avgr=args.max_avgr,
                      max_pf=args.max_pf, dry_run=args.dry_run)
        print("%-8s close=%d cap=%d | ban moi=%s | da ban truoc=%d%s"
              % (name, r["n_close"], r["n_pair"], r["ban_moi"] or "khong",
                 len(r["da_ban_truoc"]), "  (DRY-RUN)" if args.dry_run else ""))
        if r.get("env"):
            print("         go khoi .env: %s" % r["env"].get("removed"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
