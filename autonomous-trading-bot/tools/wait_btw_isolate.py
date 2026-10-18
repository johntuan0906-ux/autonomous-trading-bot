"""Cho vi the `BTW` dong -> chuyen cap do sang ISOLATED -> (tuy chon) hoi dong quyet dinh mo lai.

    python tools/wait_btw_isolate.py --target live
    python tools/wait_btw_isolate.py --target live --symbol BTW --poll 60 --notify-min 30

Yeu cau cua nguoi van hanh (16/10): *"cho den khi vi the BTW dong, sau do chuyen sang
Isolated roi moi tiep tuc vao lenh khac; hoi dong cap nhat lien tuc de nam thong tin"*.

Trinh tu:
  1. TAM DUNG vao lenh (`entries_gate.pause`) — vi the dang mo VAN duoc quan ly.
  2. Vong lap: doc vi the THAT tren san. Con mo -> ghi nhat ky dinh ky (`event=OPS`).
  3. Khi HET vi the: dat `set_margin_mode(ISOLATED)` cho cap do (Binance chi cho doi khi
     cap phang => day chinh la thoi diem hop le).
  4. Hoi dong bo phieu "co mo lai vao lenh khong?" (mac dinh ON) -> ALLOW thi `resume`,
     VETO thi GIU tam dung (nguoi van hanh mo tay).
  5. Moi buoc deu ghi journal + log => hoi dong/nguoi van hanh co vet lien tuc.

Fail-safe: doc san loi -> KHONG resume (cho tiep); het `--max-hours` -> thoat, giu tam dung.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _hide() -> dict:
    try:
        import winproc
        return winproc.hide_kwargs()
    except Exception:  # noqa: BLE001
        return {}


def journal_append(instance_dir: Path, rec: dict) -> None:
    """Ghi 1 dong vao journal cua instance (event=OPS — khong lan voi AGENT/OPEN/CLOSE)."""
    try:
        p = Path(instance_dir) / "logs" / "journal.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {"event": "OPS", "ts": time.time(), **rec}
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log(instance_dir: Path, msg: str) -> None:
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        p = Path(instance_dir) / "logs" / "wait_btw_isolate.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    try:
        print(line, flush=True)
    except Exception:  # noqa: BLE001
        pass


def position_qty(ex, symbol: str) -> float | None:
    """So hop dong dang mo cua `symbol`. None = KHONG doc duoc (fail-safe)."""
    try:
        rows = ex.fetch_positions([symbol]) or []
    except Exception as e:  # noqa: BLE001
        print("doc vi the loi: %s" % str(e)[:120], flush=True)
        return None
    for p in rows:
        if str(p.get("symbol") or "").upper() == symbol.upper():
            try:
                return abs(float(p.get("contracts") or 0))
            except (TypeError, ValueError):
                return None
    return 0.0


def set_isolated(ex, symbol: str) -> bool:
    """Dat ISOLATED cho cap (chi thanh cong khi cap PHANG)."""
    try:
        ex.set_margin_mode("isolated", symbol)
        return True
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "-4046" in msg or "No need to change" in msg:
            return True
        print("dat ISOLATED loi: %s" % msg[:160], flush=True)
        return False


def council_decide(instance_dir: Path, question: str, allow: str, veto: str,
                   contexts=()) -> dict:
    """Chay `tools/council_vote.py` trong instance dich -> {verdict, ...}."""
    cmd = [sys.executable, str(ROOT / "tools" / "council_vote.py"),
           "--question", question, "--allow", allow, "--veto", veto, "--json"]
    for c in contexts:
        cmd += ["--context", str(c)]
    try:
        p = subprocess.run(cmd, cwd=str(instance_dir), capture_output=True, text=True,
                           timeout=1200, **_hide())
    except Exception as e:  # noqa: BLE001
        return {"verdict": None, "err": str(e)[:160]}
    # (17/10) LOI THAT DA SUA: `--json` in JSON **nhieu dong** => tim `{...}` tren 1 dong
    # KHONG bao gio khop => verdict rong => tool hieu sai thanh VETO ("hoi dong KHONG cho mo
    # lai") du hoi dong da ALLOW. Nay lay tu `{` dau tien den `}` cuoi cung.
    out = p.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i >= 0 and j > i:
        try:
            d = json.loads(out[i:j + 1])
            return {"verdict": str(d.get("verdict") or ""), "n": d.get("n"),
                    "n_allow": d.get("n_allow"), "n_veto": d.get("n_veto")}
        except Exception as e:  # noqa: BLE001
            return {"verdict": None, "err": "json: %s" % str(e)[:120]}
    return {"verdict": None, "err": (out or p.stderr or "")[-160:]}


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Cho vi the dong -> Isolated -> hoi dong mo lai")
    ap.add_argument("--target", default="live", choices=("testnet", "live"))
    ap.add_argument("--symbol", default="BTW/USDT:USDT")
    ap.add_argument("--poll", type=float, default=60.0)
    ap.add_argument("--notify-min", type=float, default=30.0,
                    help="ghi nhat ky dinh ky moi N phut (0 = tat)")
    ap.add_argument("--max-hours", type=float, default=24.0)
    ap.add_argument("--no-council", action="store_true", help="khong hoi hoi dong khi xong")
    ap.add_argument("--dry-run", action="store_true", help="chi bao, khong dat/resume")
    args = ap.parse_args(argv)

    import entries_gate as EG
    import restart_bot as RB
    d = RB.instance_dir(args.target)
    ex = RB.exchange_client(d)
    if ex is None:
        print("[LOI] khong tao duoc client cho %s" % d)
        return 2

    reason = ("Cho vi the %s dong roi chuyen Isolated (yeu cau nguoi van hanh 16/10)"
              % args.symbol)
    gate = d / "logs" / "entries_pause.json"
    if not args.dry_run:
        EG.pause(reason, path=gate)
    log(d, "TAM DUNG vao lenh: %s" % reason)
    journal_append(d, {"status": "PAUSE_ON", "symbol": args.symbol, "note": reason})

    t0, last_notify = time.time(), 0.0
    while True:
        qty = position_qty(ex, args.symbol)
        if qty is None:
            log(d, "khong doc duoc vi the -> bo qua vong nay (fail-safe: GIU tam dung)")
        elif qty > 0:
            if args.notify_min and (time.time() - last_notify) >= args.notify_min * 60:
                last_notify = time.time()
                note = "%s con MO qty=%.6g -> van tam dung vao lenh" % (args.symbol, qty)
                log(d, note)
                journal_append(d, {"status": "PAUSE_WAIT", "symbol": args.symbol,
                                   "qty": qty, "note": note})
        else:
            log(d, "%s da DONG -> dat ISOLATED" % args.symbol)
            ok = True if args.dry_run else set_isolated(ex, args.symbol)
            journal_append(d, {"status": "ISOLATED" if ok else "ISOLATE_FAILED",
                               "symbol": args.symbol,
                               "note": ("dat margin type ISOLATED" if ok
                                        else "dat that bai")})
            log(d, "ISOLATED: %s" % ("OK" if ok else "THAT BAI"))
            verdict = "ALLOW"
            if ok and not args.no_council and not args.dry_run:
                rep = council_decide(
                    d,
                    ("Vi the %s da dong va da chuyen sang Isolated. Co mo lai vao lenh moi "
                     "tren tai khoan nay khong?" % args.symbol),
                    "mo lai vao lenh moi", "giu tam dung",
                    contexts=["Tam dung truoc do theo yeu cau nguoi van hanh de doi margin type",
                              "Bot da dat MARGIN_TYPE=ISOLATED cho cac cap moi tu 16/10"])
                verdict = str(rep.get("verdict") or "")
                log(d, "hoi dong: %s" % (verdict or rep.get("err") or "?"))
                journal_append(d, {"status": "COUNCIL_RESUME_VOTE", "verdict": verdict,
                                   "symbol": args.symbol})
            if args.dry_run or verdict == "ALLOW":
                if not args.dry_run:
                    EG.resume(path=gate, why="%s da dong + Isolated" % args.symbol)
                log(d, "MO LAI vao lenh (verdict=%s)" % (verdict or "-"))
                journal_append(d, {"status": "PAUSE_OFF", "symbol": args.symbol,
                                   "verdict": verdict})
                return 0
            log(d, "hoi dong KHONG cho mo lai (verdict=%s) -> GIU tam dung" % verdict)
            journal_append(d, {"status": "PAUSE_KEPT", "symbol": args.symbol,
                               "verdict": verdict})
            return 3
        if (time.time() - t0) >= float(args.max_hours) * 3600.0:
            # (17/10) LOI THAT: truoc day het gio la thoat NGAY, ke ca khi vi the da dong
            # trong luc cho => buoc Isolated KHONG BAO GIO chay, cong tam dung ket vinh vien
            # (do that: watcher thoat 16:19 17/10 khi BTW con mo; den 18:0x moi dong => bot
            # bi khoa ~26h, 716 vong PAUSED). Nay: da phang thi LAM TIEP buoc Isolated.
            if qty is not None and qty <= 0:
                log(d, "het thoi gian cho NHUNG cap da PHANG -> lam tiep buoc Isolated")
            else:
                log(d, "het thoi gian cho (%sh) -> thoat, VAN tam dung" % args.max_hours)
                journal_append(d, {"status": "PAUSE_TIMEOUT", "symbol": args.symbol})
                return 2
        time.sleep(max(5.0, float(args.poll)))


if __name__ == "__main__":
    raise SystemExit(main())
