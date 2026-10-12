"""Chon danh sach cap cho 1 instance theo THANH KHOAN + bang chung tu journal.

    python tools/pick_symbols.py --target live --top 40 --dry-run   # xem truoc
    python tools/pick_symbols.py --target live --top 40             # ghi whitelist
    python tools/pick_symbols.py --target live --clear              # bo whitelist

Ket qua: `logs/<target>_whitelist.txt` (moi dong 1 cap). `tools/apply_symbols.py`
tu dong ton trong file nay khi nap SYMBOLS (bo qua bang `--no-whitelist`).

Tieu chi (tat dinh, de giai thich duoc):
 1. Bo cap da bi ban vinh vien (`logs/banned_pairs.json` — do `pair_audit.py`).
 2. Bo cap ma journal da chung minh THUA (n >= 5 lenh va avgR <= -0.10).
 3. Giu lai cap DANG co vi the mo (khong bo roi vi the dang chay).
 4. Xep hang theo khoi luong 24h (quoteVolume) giam dan — thanh khoan tot =
    spread thap, it truot gia, de dat notional toi thieu cua san.
 5. Lay top N; in bang de nguoi van hanh doc lai truoc khi ap.

Vi sao can thu hep (12/10): 458 cap tren tai khoan nho (19.7 USDT) vua lam
vong quet nang (de treo may), vua khien bot mo nhieu lenh nho kho kiem soat
rui ro. LIVE chi can nhom thanh khoan cao nhat la du de hoc/kiem chung.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
TARGETS = {"testnet": ROOT, "live": LIVE_DIR}


def instance_dir(target: str) -> Path:
    return TARGETS[str(target).lower()]


def whitelist_path(target: str) -> Path:
    return instance_dir(target) / "logs" / ("%s_whitelist.txt" % str(target).lower())


def load_journal_stats(path: Path, min_n: int = 5) -> dict:
    """{cap: {'n': so lenh, 'avgR': trung binh R}} tu journal.jsonl (chi doc)."""
    stats: dict = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return stats
    for ln in lines:
        try:
            rec = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if rec.get("event") != "CLOSE":
            continue
        sym = rec.get("pair")
        if not sym or rec.get("r") is None:
            continue
        s = stats.setdefault(sym, {"n": 0, "sum": 0.0})
        s["n"] += 1
        try:
            s["sum"] += float(rec["r"])
        except (TypeError, ValueError):
            continue
    out = {}
    for sym, s in stats.items():
        if s["n"] >= min_n:
            out[sym] = {"n": s["n"], "avgR": round(s["sum"] / max(1, s["n"]), 4)}
    return out


def rank_pairs(volumes: dict, banned: set, stats: dict, held: set, top: int,
               min_n: int = 5, min_avg_r: float = -0.10) -> list:
    """Tra [(cap, ly do)] da xep hang — THUAN TUY (khong goi mang, test duoc).

    - `volumes`: {cap: khoi luong 24h}
    - `banned` : cap bi ban vinh vien
    - `stats`  : {cap: {'n','avgR'}} tu journal
    - `held`   : cap dang co vi the mo (luon duoc giu)
    """
    keep: list = []
    for sym, vol in volumes.items():
        if sym in banned:
            continue
        st = stats.get(sym) or {}
        if st and st.get("n", 0) >= min_n and float(st.get("avgR", 0.0)) <= min_avg_r:
            continue                        # da chung minh thua -> bo
        keep.append((sym, float(vol or 0.0)))
    keep.sort(key=lambda kv: kv[1], reverse=True)
    out: list = []
    seen: set = set()
    for sym in sorted(held):                # vi the dang mo luon duoc giu
        if sym in banned or sym in seen:
            continue
        seen.add(sym)
        out.append((sym, "dang giu vi the"))
    for sym, vol in keep:
        if sym in seen:
            continue
        seen.add(sym)
        out.append((sym, "vol24h=%.0f" % vol))
        if len(out) >= top:
            break
    return out[:max(top, len(held))]

def load_banned(d: Path) -> set:
    try:
        data = json.loads((d / "logs" / "banned_pairs.json").read_text(encoding="utf-8"))
        return set(data.keys()) if isinstance(data, dict) else set(data)
    except Exception:  # noqa: BLE001
        return set()


def held_pairs(d: Path) -> set:
    """Cap dang co vi the mo (theo journal: OPEN chua CLOSE)."""
    opened: dict = {}
    try:
        lines = (d / "logs" / "journal.jsonl").read_text(
            encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return set()
    for ln in lines[-20000:]:
        try:
            rec = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        sym = rec.get("pair")
        if not sym:
            continue
        if rec.get("event") == "OPEN":
            opened[sym] = opened.get(sym, 0) + 1
        elif rec.get("event") == "CLOSE":
            opened[sym] = opened.get(sym, 0) - 1
    return {s for s, n in opened.items() if n > 0}


def fetch_quote_volumes(symbols: list) -> dict:
    """Khoi luong 24h (quoteVolume) tu ccxt cho tung cap. Loi -> {}."""
    try:
        import ccxt
    except Exception as e:  # noqa: BLE001
        print("CANH BAO: khong import duoc ccxt (%s)" % str(e)[:80])
        return {}
    ex = ccxt.binanceusdm({"enableRateLimit": True, "timeout": 30000})
    try:
        tk = ex.fetch_tickers(symbols)
    except Exception as e:  # noqa: BLE001
        print("CANH BAO: fetch_tickers loi (%s)" % str(e)[:120])
        return {}
    out = {}
    for sym, t in (tk or {}).items():
        try:
            out[sym] = float(t.get("quoteVolume") or 0.0)
        except (TypeError, ValueError):
            out[sym] = 0.0
    return out


def write_whitelist(target: str, rows: list, top: int) -> Path:
    p = whitelist_path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = ["# Whitelist %s — sinh boi tools/pick_symbols.py (top %d)" % (target.upper(), top),
            "# Xoa file nay (hoac `--clear`) de quay lai danh sach day du."]
    body += [s for s, _ in rows]
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p


def read_whitelist(target: str) -> list:
    """Doc whitelist cua instance (bo comment/dong trong). Rong neu khong co."""
    p = whitelist_path(target)
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [ln.strip() for ln in txt.splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chon top N cap theo thanh khoan + journal")
    ap.add_argument("--target", choices=("testnet", "live"), default="live")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--clear", action="store_true", help="xoa whitelist (quay lai day du)")
    ap.add_argument("--dry-run", action="store_true", help="chi in, khong ghi file")
    ap.add_argument("--min-avg-r", type=float, default=-0.10,
                    help="bo cap co avgR <= nguong nay khi n>=5 lenh")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    d = instance_dir(args.target)
    if args.clear:
        try:
            whitelist_path(args.target).unlink()
            print("da xoa whitelist cua %s" % args.target.upper())
        except FileNotFoundError:
            print("khong co whitelist de xoa")
        return 0
    sys.path.insert(0, str(ROOT))
    try:
        from config import Settings
        from turbo_demo import active_symbols
        syms = active_symbols(Settings())
    except Exception as e:  # noqa: BLE001
        print("LOI: khong doc duoc SYMBOLS tu .env (%s)" % str(e)[:120])
        return 2
    banned = load_banned(d)
    held = held_pairs(d)
    stats = load_journal_stats(d / "logs" / "journal.jsonl")
    print("ung vien: %d cap | ban=%d | dang giu vi the=%d | co thong ke journal=%d"
          % (len(syms), len(banned), len(held), len(stats)))
    vols = fetch_quote_volumes(syms)
    if not vols:
        return 2
    rows = rank_pairs(vols, banned, stats, held, args.top, min_avg_r=args.min_avg_r)
    print("--- TOP %d cho %s ---" % (len(rows), args.target.upper()))
    for i, (sym, why) in enumerate(rows, 1):
        print("%3d. %-22s %s" % (i, sym, why))
    if args.dry_run:
        print("(dry-run: khong ghi file)")
        return 0
    p = write_whitelist(args.target, rows, args.top)
    print("da ghi %s (%d cap)" % (p, len(rows)))
    print("Ap dung: python tools/apply_symbols.py --target %s" % args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
