"""Dung lai learner bang FIT OFFLINE + KIEM DINH holdout — co LUOI AN TOAN "trung tinh".

    python tools/learner_refit.py --target both            # fit + bao cao (khong ghi)
    python tools/learner_refit.py --target both --write     # ghi logs/learner.json (backup .bak-refit)
    python tools/learner_refit.py --target testnet --json

Vi sao co (28/10 — hoi dong quyet, xem REPO_IDEAS §23.7):
- Learner online (SGD trong `learner.OnlineLearner.update`) **dung cong thuc** nhung chay tren
  chuoi KHONG DUNG (thi truong doi, tham so bot doi) ⇒ trong so cuoi bi chi phoi boi ~100 lenh gan
  nhat. Do that 28/10 (200 lenh ghep cap gan nhat): **TESTNET WIN thuc te 58% nhung learner du doan
  p = 23%** (edge -0.53, `b` = -0.479) ⇒ chan 64% setup ⇒ `BLOCKED_LEARN` ⇒ bot dung yen;
  LIVE 60% vs 48% (chan 13%). Learner MOI (chua hoc) cho edge +0.33 tren cung bo feats ⇒ loi nam o
  TRONG SO da hoc, khong phai o features.
- Nguyen tac: model dung de CHAN tien that thi phai **kiem dinh duoc**. File nay:
  1. fit **logistic chinh quy (L2)** bang gradient batch tren **train** (80% cu nhat);
  2. **kiem dinh tren holdout** (20% moi nhat): base-rate, log-loss model vs log-loss cua
     "luon doan base-rate", % setup bi chan o nguong `LEARN_MIN_EDGE`;
  3. **LUOI AN TOAN**: neu model KHONG thang duoc base-rate tren holdout ⇒ ghi learner **TRUNG TINH**
     (`w = 0`, `b = logit(base_rate)`) ⇒ `edge ~ 0` ⇒ **khong bao gio chan oan**; co du lieu moi thi
     fit lai moi danh gia duoc edge.

Chi dung stdlib (hoi dong da quyet "khong them phu thuoc ngoai").
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import learner as L          # noqa: E402

FEATURES = tuple(L.FEATURES)
#: Nguong chan cua turbo_demo (phai khop `turbo_demo.LEARN_MIN_EDGE`).
LEARN_MIN_EDGE = -0.30
DEFAULT_HOLDOUT = 0.2
DEFAULT_L2 = 0.01
DEFAULT_ITERS = 600
DEFAULT_LR = 0.5
#: Duoi so lenh nay thi KHONG fit (khong du du lieu ⇒ giu trung tinh).
MIN_TRAIN = 80


def logit(p: float) -> float:
    p = min(max(float(p), 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))


def load_pairs(journal: Path) -> list:
    """Ghep OPEN→CLOSE theo (pair, direction); tra [(feats, direction, pnl)] theo thoi gian."""
    try:
        text = Path(journal).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict):
            rows.append(d)
    opens = [r for r in rows if r.get("event") == "OPEN"]
    closes = [r for r in rows if r.get("event") == "CLOSE"]
    by: dict = {}
    for o in sorted(opens, key=lambda r: float(r.get("ts") or 0.0)):
        by.setdefault((str(o.get("pair")), str(o.get("direction"))), []).append(o)
    used: set = set()
    out = []
    for c in sorted(closes, key=lambda r: float(r.get("ts") or 0.0)):
        k = (str(c.get("pair")), str(c.get("direction")))
        try:
            ts = float(c.get("ts"))
        except (TypeError, ValueError):
            continue
        cand = by.get(k) or []
        for i in range(len(cand) - 1, -1, -1):
            if float(cand[i].get("ts") or 0.0) <= ts and (k, i) not in used:
                used.add((k, i))
                o = cand[i]
                feats = o.get("feats")
                if isinstance(feats, dict) and feats:
                    out.append((feats, str(o.get("direction") or "LONG"),
                                float(c.get("pnl") or 0.0)))
                break
    return out


def vector(feats: dict, direction: str) -> dict:
    """Doi dau features theo HUONG LENH (cung quy uoc voi `learner.update`/`edge`)."""
    if str(direction).upper() == "LONG":
        return {k: float(feats.get(k, 0.0) or 0.0) for k in FEATURES}
    return {k: -float(feats.get(k, 0.0) or 0.0) for k in FEATURES}



def fit(rows: list, *, l2: float = DEFAULT_L2, iters: int = DEFAULT_ITERS,
        lr: float = DEFAULT_LR) -> dict:
    """Logistic regression (L2) bang gradient batch. Tra {w, b, loss}.

    Dung `.get(k, 0.0)` khi doc feature ⇒ chiu duoc vector THIEU khoa (test/du lieu cu).
    """
    w = {k: 0.0 for k in FEATURES}
    b = 0.0
    n = max(len(rows), 1)
    for _ in range(int(iters)):
        gw = {k: 0.0 for k in FEATURES}
        gb = 0.0
        for f, y in rows:
            p = sigmoid(b + sum(w[k] * f.get(k, 0.0) for k in FEATURES))
            err = y - p
            for k in FEATURES:
                gw[k] += err * f.get(k, 0.0)
            gb += err
        for k in FEATURES:
            w[k] += lr * (gw[k] / n - l2 * w[k])
        b += lr * (gb / n)
    return {"w": w, "b": b, "loss": logloss(rows, w, b)}


def logloss(rows: list, w: dict, b: float) -> float:
    """Log-loss trung binh (thap hon = doan tot hon)."""
    if not rows:
        return 0.0
    tot = 0.0
    for f, y in rows:
        p = sigmoid(b + sum(w.get(k, 0.0) * f.get(k, 0.0) for k in FEATURES))
        tot -= y * math.log(max(p, 1e-9)) + (1 - y) * math.log(max(1 - p, 1e-9))
    return tot / len(rows)


def edge_of(f: dict, w: dict, b: float) -> float:
    """Giong `learner.OnlineLearner.edge`: (p - 0.5) * 2, khoang (-1, +1)."""
    return (sigmoid(b + sum(w.get(k, 0.0) * f.get(k, 0.0) for k in FEATURES)) - 0.5) * 2.0



def refit_one(name: str, base: Path, *, holdout: float = DEFAULT_HOLDOUT,
              l2: float = DEFAULT_L2, iters: int = DEFAULT_ITERS, lr: float = DEFAULT_LR,
              min_train: int = MIN_TRAIN, write: bool = False) -> dict:
    """Fit + kiem dinh 1 instance. Tra bao cao (chi ghi khi `write=True`)."""
    prs = load_pairs(Path(base) / "logs" / "journal.jsonl")
    rows = [(vector(f, d), 1.0 if pnl > 0 else 0.0) for f, d, pnl in prs]
    n = len(rows)
    cut = int(n * (1.0 - float(holdout)))
    train, test = rows[:cut], rows[cut:]
    rep = {"name": name, "n": n, "n_train": len(train), "n_test": len(test),
           "base_rate_train": 0.0, "base_rate_test": 0.0, "neutral": False, "written": ""}
    if n < int(min_train) or not test:
        rep["reason"] = "chi co %d lenh (< %d) ⇒ KHONG fit, giu trung tinh" % (n, min_train)
        w, b = {k: 0.0 for k in FEATURES}, 0.0
        rep["neutral"] = True
    else:
        base_tr = sum(y for _f, y in train) / len(train)
        base_te = sum(y for _f, y in test) / len(test)
        rep["base_rate_train"], rep["base_rate_test"] = round(base_tr, 4), round(base_te, 4)
        m = fit(train, l2=l2, iters=iters, lr=lr)
        w, b = m["w"], m["b"]
        ll_model, ll_base = logloss(test, w, b), logloss(test, {}, logit(base_tr))
        if ll_model >= ll_base:
            # LUOI AN TOAN: khong thang duoc "luon doan base-rate" ⇒ TRUNG TINH, khong chan ai.
            w, b = {k: 0.0 for k in FEATURES}, logit(base_tr)
            rep["neutral"] = True
            rep["reason"] = ("model KHONG thang base-rate tren holdout (%.4f >= %.4f) ⇒ "
                             "learner TRUNG TINH (khong chan)" % (ll_model, ll_base))
        # (28/10) Bao cao PHAI mo ta model SE DUOC GHI (sau khi da ap luoi an toan) — neu khong
        # thi bao "chan 4%" trong khi thuc te ghi learner trung tinh (khong chan gi) ⇒ sai lech.
        edges = sorted(edge_of(f, w, b) for f, _y in test)
        rep.update({"logloss_model": round(ll_model, 4), "logloss_base": round(ll_base, 4),
                    "edge_median_test": round(edges[len(edges) // 2], 3),
                    "blocked_pct_test": round(
                        100.0 * sum(1 for x in edges if x < LEARN_MIN_EDGE) / len(edges), 1)})
    if write:
        lp = Path(base) / "logs" / "learner.json"
        if lp.exists():
            shutil.copy2(lp, str(lp) + ".bak-refit")
        data = {"w": {k: round(float(v), 6) for k, v in w.items()},
                "b": round(float(b), 6), "n": int(rep.get("n_train") or 0),
                "ts": time.time(),
                "refit": {"neutral": bool(rep["neutral"]), "holdout": float(holdout),
                          "logloss_model": rep.get("logloss_model"),
                          "logloss_base": rep.get("logloss_base")}}
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        rep["written"] = str(lp)
    return rep


def live_dir() -> Path:
    """Thu muc instance LIVE (giong cac tool khac trong repo)."""
    try:
        import backup as BK
        return Path(BK.LIVE_DIR)
    except Exception:  # noqa: BLE001
        return ROOT.parent / "atb-live"


def print_report(reps: list) -> None:
    print("=== DUNG LAI LEARNER (fit offline + kiem dinh holdout) | %s ==="
          % time.strftime("%Y-%m-%d %H:%M:%S"))
    for r in reps:
        print("  %s: %d lenh (train %d / test %d)"
              % (r["name"], r["n"], r["n_train"], r["n_test"]))
        if r.get("base_rate_train"):
            print("     WIN thuc te: train %.0f%% | holdout %.0f%%"
                  % (100 * r["base_rate_train"], 100 * r["base_rate_test"]))
        if r.get("logloss_model") is not None:
            print("     log-loss holdout: model %.4f vs base-rate %.4f ⇒ %s"
                  % (r["logloss_model"], r["logloss_base"],
                     "model THANG" if not r["neutral"] else "KHONG thang ⇒ TRUNG TINH"))
            print("     edge trung vi holdout %.3f | %s%% setup bi chan o nguong %.2f"
                  % (r["edge_median_test"], r["blocked_pct_test"], LEARN_MIN_EDGE))
        if r.get("reason"):
            print("     => %s" % r["reason"])
        if r["written"]:
            print("     da ghi: %s (backup .bak-refit)" % r["written"])
    if not any(r["written"] for r in reps):
        print("  (chua ghi gi — them `--write` de ap dung)")


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Dung lai learner: fit offline + kiem dinh holdout")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--holdout", type=float, default=DEFAULT_HOLDOUT)
    ap.add_argument("--l2", type=float, default=DEFAULT_L2)
    ap.add_argument("--iters", type=int, default=DEFAULT_ITERS)
    ap.add_argument("--lr", type=float, default=DEFAULT_LR)
    ap.add_argument("--min-train", type=int, default=MIN_TRAIN)
    ap.add_argument("--write", action="store_true", help="ghi logs/learner.json (co backup)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    dirs = {"TESTNET": ROOT, "LIVE": live_dir()}
    if args.target == "testnet":
        dirs = {"TESTNET": ROOT}
    elif args.target == "live":
        dirs = {"LIVE": live_dir()}
    reps = [refit_one(n, b, holdout=args.holdout, l2=args.l2, iters=args.iters, lr=args.lr,
                      min_train=args.min_train, write=args.write) for n, b in dirs.items()]
    if args.json:
        print(json.dumps(reps, ensure_ascii=False, indent=1))
    else:
        print_report(reps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
