"""Phân tích LỖ: lệnh nào / lúc nào / kiểu gì đang làm mất tiền → đề xuất cụ thể.

Chạy:
    python loss_report.py                 # toan bo journal
    python loss_report.py --days 30       # chi N ngay gan nhat
    python loss_report.py --min-n 15      # nguong mau toi thieu cho 1 nhom
    python loss_report.py --json logs/loss_report.json

Tất định 100%, chỉ ĐỌC `logs/journal.jsonl` (không LLM, không gọi sàn). Gom nhóm theo:
**cặp · hướng · chiến lược · regime · lý do thoát · giờ UTC · thời gian giữ lệnh**;
mỗi nhóm in `n · WR · avgR · tổng R · % đóng góp vào TỔNG LỖ`.

Đề xuất (rule tất định — chỉ để XEM XÉT, KHÔNG tự đổi config):
  - cặp       n≥min_n & avgR ≤ −0.10  → bỏ khỏi `SYMBOLS`/`EXTRA_SYMBOLS` (như đã làm với ETH)
  - chiến lược n≥min_n & avgR ≤ −0.10 → thêm vào `STRATEGY_BLOCK` (hoặc tin runtime auto-gate)
  - regime    n≥min_n & avgR ≤ −0.10  → cân nhắc `REGIME_BLOCK` (⚠️ CHƯA có cơ chế, cần thêm code)
  - hướng     n≥min_n & avgR ≤ −0.05  → cân nhắc lọc hướng (cần thêm bằng chứng)
  - lý do thoát: SL chiếm >55% số lần thoát → SL đang bị quét nhiều (xem lại độ rộng SL)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from monitor_report import load_journal, match_pairs


def load_pairs(journal: str, days: float = 0.0, now: float | None = None) -> tuple:
    """(pairs, still) — chỉ lấy các cặp có CLOSE trong `days` ngày gần nhất (0 = tất cả)."""
    import time as _t
    opens, closes = load_journal(journal)
    pairs, still = match_pairs(opens, closes)
    if days and days > 0:
        cut = float(now if now is not None else _t.time()) - float(days) * 86400.0
        pairs = [(o, c) for o, c in pairs if float((c or {}).get("ts") or 0) >= cut]
    return pairs, still


def _grp(pairs: list, key_fn) -> dict:
    """Gom nhóm -> {key: {n, wr, avg_r, sum_r, loss_r, gain_r}} (loss_r = |tổng R âm|)."""
    acc: dict = defaultdict(lambda: {"n": 0, "wins": 0, "sum_r": 0.0,
                                     "loss_r": 0.0, "gain_r": 0.0})
    for o, c in pairs:
        k = key_fn(o, c)
        if k is None:
            continue
        a = acc[k]
        r = float((c or {}).get("r") or 0.0)
        a["n"] += 1
        a["wins"] += 1 if (c or {}).get("won") else 0
        a["sum_r"] += r
        if r < 0:
            a["loss_r"] += abs(r)
        else:
            a["gain_r"] += r
    out = {}
    for k, a in acc.items():
        n = a["n"] or 1
        out[k] = {"n": a["n"], "wr": round(100.0 * a["wins"] / n, 1),
                  "avg_r": round(a["sum_r"] / n, 4), "sum_r": round(a["sum_r"], 3),
                  "loss_r": round(a["loss_r"], 3), "gain_r": round(a["gain_r"], 3)}
    return out


def hour_of(ts) -> int | None:
    try:
        import time as _t
        return int(_t.gmtime(float(ts)).tm_hour)
    except Exception:  # noqa: BLE001
        return None


def hold_bucket(o, c) -> str:
    try:
        mins = (float((c or {}).get("ts") or 0) - float((o or {}).get("ts") or 0)) / 60.0
    except Exception:  # noqa: BLE001
        return "?"
    if mins <= 0:
        return "?"
    if mins < 30:
        return "<30 phut"
    if mins < 120:
        return "30-120 phut"
    if mins < 480:
        return "2-8 gio"
    return ">8 gio"


def propose(kind: str, key, g: dict, share: float | None = None) -> str:
    """Câu đề xuất tất định cho 1 nhóm yếu (chỉ để xem xét)."""
    sh = "" if share is None else (" — dong gop %.1f%% tong lo" % share)
    if kind == "cap":
        return ("bo `%s` khoi SYMBOLS/EXTRA_SYMBOLS (n=%d, avgR=%+.3f)%s — nhu da bo ETH"
                % (key, g["n"], g["avg_r"], sh))
    if kind == "cap_top":
        return ("`%s` la nguon lo LON NHAT (n=%d, avgR=%+.3f, tong %+.2fR)%s — theo doi, "
                "can nhac giam uu tien/bo cap" % (key, g["n"], g["avg_r"], g["sum_r"], sh))
    if kind == "chien luoc":
        return ("them `%s` vao STRATEGY_BLOCK (n=%d, avgR=%+.3f)%s, hoac tin runtime auto-gate "
                "(STRATEGY_GATE=true)" % (key, g["n"], g["avg_r"], sh))
    if kind == "regime":
        return ("can nhac chan regime `%s` (n=%d, avgR=%+.3f)%s — ⚠️ CHUA co co che REGIME_BLOCK, "
                "phai them code" % (key, g["n"], g["avg_r"], sh))
    if kind == "huong":
        return ("can nhac loc huong `%s` (n=%d, avgR=%+.3f)%s — can them bang chung"
                % (key, g["n"], g["avg_r"], sh))
    if kind == "thoat":
        return ("ly do thoat `%s` chiem n=%d (avgR=%+.3f)%s — FLATTEN la dong vi the CUONG BUC "
                "(loi API / kill-switch): xem tan suat `api errors` trong logs/turbo_err.log"
                % (key, g["n"], g["avg_r"], sh))
    if kind == "giu":
        return ("giu lenh `%s` (n=%d, avgR=%+.3f)%s — lenh giu qua lau dang am; can nhac "
                "gioi han thoi gian giu (max-hold)" % (key, g["n"], g["avg_r"], sh))
    return ("%s: n=%d avgR=%+.3f%s" % (key, g["n"], g["avg_r"], sh))


def analyze(pairs: list, min_n: int = 15) -> dict:
    """Tất cả nhóm + đề xuất + số liệu tổng. Thuần tuý (test được)."""
    dims = {
        "cap": ("CẶP", lambda o, c: (c or {}).get("pair") or (o or {}).get("pair")),
        "huong": ("HƯỚNG", lambda o, c: str((c or {}).get("direction") or "").upper() or None),
        "chien luoc": ("CHIẾN LƯỢC", lambda o, c: (o or {}).get("strategy")),
        "regime": ("REGIME", lambda o, c: (o or {}).get("market_regime")),
        "ly do thoat": ("LÝ DO THOÁT", lambda o, c: (c or {}).get("reason")),
        "gio UTC": ("GIỜ (UTC)", lambda o, c: hour_of((o or {}).get("ts"))),
        "thoi gian giu": ("THỜI GIAN GIỮ", hold_bucket),
    }
    groups = {k: _grp(pairs, fn) for k, (_, fn) in dims.items()}
    total_loss = sum(g["loss_r"] for g in groups["cap"].values()) or 1.0
    total_r = round(sum(g["sum_r"] for g in groups["cap"].values()), 3)
    props = {
        "cap": [(k, g, propose("cap", k, g)) for k, g in groups["cap"].items()
                if g["n"] >= min_n and g["avg_r"] <= -0.10],
        "chien luoc": [(k, g, propose("chien luoc", k, g)) for k, g in groups["chien luoc"].items()
                       if str(k) not in ("NONE", "?", "None") and g["n"] >= min_n
                       and g["avg_r"] <= -0.10],
        "regime": [(k, g, propose("regime", k, g)) for k, g in groups["regime"].items()
                   if k and g["n"] >= min_n and g["avg_r"] <= -0.10],
        "huong": [(k, g, propose("huong", k, g)) for k, g in groups["huong"].items()
                  if k and g["n"] >= min_n and g["avg_r"] <= -0.05],
    }
    exits = groups["ly do thoat"]
    n_all = sum(g["n"] for g in exits.values()) or 1
    sl_share = round(100.0 * (exits.get("SL", {}).get("n", 0)) / n_all, 1)
    # (09/10) 2 rule bo sung — truong hop avgR chua xau toi -0.10 nhung VAN la nguon lo lon:
    #   (a) cap dong gop lo lon nhat (nhu BTC: avgR -0.064 nhung 28% tong lo)
    #   (b) FLATTEN (dong vi the CUONG BUC do loi API/kill-switch) va thoi gian giu dai
    top = sorted(((k, g) for k, g in groups["cap"].items()
                  if g["avg_r"] < 0 and k), key=lambda kv: -kv[1]["loss_r"])
    if top:
        k, g = top[0]
        share = 100.0 * g["loss_r"] / total_loss
        if share >= 20.0:
            props["cap"].append((k, g, propose("cap_top", k, g, share)))
    fl = exits.get("FLATTEN")
    if fl and fl["n"] >= min_n and fl["avg_r"] < 0:
        share = 100.0 * fl["loss_r"] / total_loss
        if share >= 15.0:
            props["ly do thoat"] = [("FLATTEN", fl, propose("thoat", "FLATTEN", fl, share))]
    hb = groups["thoi gian giu"].get(">8 gio")
    if hb and hb["n"] >= min_n and hb["avg_r"] < 0:
        share = 100.0 * hb["loss_r"] / total_loss
        if share >= 15.0:
            props["thoi gian giu"] = [(">8 gio", hb, propose("giu", ">8 gio", hb, share))]
    return {"groups": groups, "dims": dims, "props": props, "total_r": total_r,
            "total_loss_r": round(total_loss, 3), "n": n_all, "sl_share": sl_share,
            "min_n": min_n}


def render(rep: dict) -> str:
    lines = ["=" * 92,
             "PHAN TICH LO | n=%d lenh | tong R=%+.2f | tong R am=%.2f | SL chiem %.1f%% so lan thoat"
             % (rep["n"], rep["total_r"], rep["total_loss_r"], rep["sl_share"]),
             "=" * 92]
    for kind, (title, _) in rep["dims"].items():
        g = rep["groups"].get(kind) or {}
        if not g:
            continue
        lines += ["", "## %s" % title,
                  "  %-18s %5s %7s %9s %10s %13s"
                  % ("NHOM", "n", "WR%", "avgR", "tongR", "lo dong gop")]
        for k, v in sorted(g.items(), key=lambda kv: kv[1]["sum_r"]):
            share = 100.0 * v["loss_r"] / (rep["total_loss_r"] or 1.0)
            lines.append("  %-18s %5d %7.1f %+9.3f %+10.2f %12.1f%%"
                         % (str(k)[:18], v["n"], v["wr"], v["avg_r"], v["sum_r"], share))
    lines += ["", "=" * 92,
              "DE XUAT (rule tat dinh — CHI de xem xet, KHONG tu doi config)"]
    any_prop = False
    for kind in list(rep["dims"]):
        for _k, _g, text in rep["props"].get(kind, []):
            lines.append("  [%s] %s" % (kind.upper(), text))
            any_prop = True
    if not any_prop:
        lines.append("  (khong co nhom nao xau qua nguong — khong de xuat gi)")
    if rep["sl_share"] > 55:
        lines.append("  [SL] SL chiem %.1f%% so lan thoat (>55%%): xem lai do rong SL (ATR) "
                     "hoac loc setup yeu truoc khi vao" % rep["sl_share"])
    lines += ["", "Ghi chu: R = r-multiple; 'lo dong gop' = % trong TONG R am."]
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phan tich lo tu journal (chi doc)")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--days", type=float, default=0.0, help="chi N ngay gan nhat (0 = tat ca)")
    ap.add_argument("--min-n", type=int, default=15, help="nguong mau toi thieu cho 1 nhom")
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)
    try:  # console Windows (cp1252) khong in duoc tieng Viet -> ep UTF-8
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    pairs, still = load_pairs(args.journal, days=args.days)
    rep = analyze(pairs, min_n=args.min_n)
    print(render(rep))
    if still:
        print("\n(%d OPEN chua co CLOSE — lich su ghi chep)" % len(still))
    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, ensure_ascii=False, indent=1)
            print("[OK] da luu %s" % args.json)
        except OSError as e:
            print("[WARN] khong luu duoc: %s" % e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
