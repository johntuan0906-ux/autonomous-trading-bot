"""Trieu tap HOI DONG de QUYET DINH mot cau hoi van hanh (nhi phan).

    python tools/council_vote.py --question "Co nen reset kill-switch TESTNET?" \
        --allow "reset va chay tiep" --veto "giu ngung, sua nguong truoc" \
        --context "TESTNET trip 3 lan" --context "muc 12, 6 loi lien tiep"

Cach hoat dong: dung dung may moc cua bot (`agents.multi_model_council`) — khong co
duong tat rieng. `ALLOW` = chon `--allow`, `VETO` = chon `--veto`, `NO_OPINION` = khong
du thong tin. Phieu duoc ghi vao journal (`status=COUNCIL`) nen `agents.py
--council-health` va `tools/council_eval.py` dem duoc — quyet dinh co BANG CHUNG.

Vi sao co tool nay (15/10, yeu cau nguoi van hanh "hoi dong hay quyet dinh"): hoi dong
truoc day chi duoc hoi ve lenh giao dich. Nhung cau hoi that su kho (co nen tiep tuc
chay khi kill-switch trip? giam so model?) van do 1 nguoi quyet. Nay hoi dong duoc hoi
truc tiep, va cau tra loi duoc luu lai de doi chieu voi ket qua that.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def build_payload(question: str, allow: str, veto: str, context=(), extra=None) -> dict:
    """Payload cho hoi dong (ham THUAN TUY -> test duoc).

    Ghi ro mapping vi model phai tra ve dung 1 trong 3 gia tri ALLOW/VETO/NO_OPINION.
    """
    return {
        "kind": "OPERATIONS_DECISION",
        "symbol": "OPS", "direction": "DECISION",
        "question": str(question),
        "option_ALLOW": str(allow),
        "option_VETO": str(veto),
        "context": [str(c) for c in (context or [])],
        "instruction": ("Day KHONG phai lenh giao dich ma la QUYET DINH VAN HANH. "
                        "Tra ve ALLOW neu chon option_ALLOW, VETO neu chon option_VETO, "
                        "NO_OPINION neu thieu thong tin. Ghi ly do ngan gon."),
        **(extra or {}),
    }


def tally(results: dict) -> dict:
    """Dem phieu theo TUNG MODEL. Chiu duoc ca dict lan object (ham thuan)."""
    rows, n_allow, n_veto, n_abs = [], 0, 0, 0
    for model, d in (results or {}).items():
        if isinstance(d, dict):
            act = str(d.get("action") or "").upper()
            conf = d.get("confidence")
            why = d.get("reasons") or d.get("reason") or []
        else:                                   # Decision dataclass
            act = str(getattr(d, "action", "") or "").upper()
            conf = getattr(d, "confidence", None)
            why = getattr(d, "reasons", None) or getattr(d, "reason", "") or []
        if isinstance(why, str):
            why = [why]
        rows.append({"model": model, "action": act or "?",
                     "confidence": conf,
                     "reason": "; ".join(str(x) for x in why)[:200]})
        if act == "ALLOW":
            n_allow += 1
        elif act == "VETO":
            n_veto += 1
        else:
            n_abs += 1
    verdict = ("ALLOW" if n_allow > n_veto else
               "VETO" if n_veto > n_allow else "NO_OPINION")
    return {"rows": rows, "n_allow": n_allow, "n_veto": n_veto, "n_abstain": n_abs,
            "n": len(rows), "verdict": verdict}


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Hoi dong quyet dinh 1 cau hoi van hanh")
    ap.add_argument("--question", required=True)
    ap.add_argument("--allow", required=True, help="y nghia cua phieu ALLOW")
    ap.add_argument("--veto", required=True, help="y nghia cua phieu VETO")
    ap.add_argument("--context", action="append", default=[],
                    help="1 dong bang chung/ngu canh (lap lai duoc)")
    ap.add_argument("--models", default="", help="danh sach model, phay (rong = theo .env)")
    ap.add_argument("--no-journal", action="store_true", help="khong ghi phieu vao journal")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    import agents as AG
    from config import Settings

    cfg = Settings()
    if args.models:      # gioi han model -> 1 vong tra loi nhanh, du phieu
        ms = [m.strip() for m in args.models.split(",") if m.strip()]
        # (15/10) DINH TUYEN theo tien to — moi provider doc danh sach RIENG cua no:
        #   `cline-pass/...` -> agent_council_cline ; `llama3.2-3b-local` -> agent_council_local ;
        #   con lai -> agent_council_models (copilot...).
        # Loi that gap khi trieu tap hoi dong lan dau: de het vao agent_council_models thi
        # provider cline/local thay danh sach RONG -> "CA HAI provider deu bi chan" + 0 phieu.
        cur_local = [x.strip() for x in
                     str(getattr(cfg, "agent_council_local", "") or "").split(",") if x.strip()]

        def _norm_local(m):
            return m[len("local/"):] if m.startswith("local/") else m

        local_ms = [_norm_local(m) for m in ms
                    if m.startswith("local/") or _norm_local(m) in cur_local]
        cline_ms = [m for m in ms if m.startswith("cline-pass/")]
        other_ms = [m for m in ms if m not in cline_ms and _norm_local(m) not in local_ms]
        object.__setattr__(cfg, "agent_council_models", other_ms)
        object.__setattr__(cfg, "agent_council_cline", ",".join(cline_ms))
        object.__setattr__(cfg, "agent_council_local", ",".join(local_ms))
        for k in ("agent_council_qwen", "agent_council_muse", "agent_council_muse_cli",
                  "agent_council_urgent", "agent_council_fallbacks"):
            object.__setattr__(cfg, k, "")
        object.__setattr__(cfg, "agents_council", True)
        object.__setattr__(cfg, "agents_enabled", True)
    object.__setattr__(cfg, "council_rounds", 1)      # 1 vong: nhanh, du phieu

    payload = build_payload(args.question, args.allow, args.veto, args.context)
    t0 = time.time()
    res = AG.multi_model_council(cfg, payload, role="critic")
    # (15/10) Loi that: `multi_model_council` tra khoa **`votes`** (khong phai
    # `decisions`) + `action`/`confidence`/`why`. Ban dau chi doc `decisions` =>
    # hoi dong da bo phieu ma tool in ra "0 phieu / NO_OPINION" (bao sai).
    decs = None
    if isinstance(res, dict):
        decs = res.get("decisions") or res.get("votes")
        if not decs:
            decs = {k: v for k, v in res.items()
                    if isinstance(v, dict) and "action" in v}
    rep = tally(decs or {})
    rep["seconds"] = round(time.time() - t0, 1)
    rep["question"] = args.question
    rep["option_ALLOW"] = args.allow
    rep["option_VETO"] = args.veto
    rep["raw_action"] = (res or {}).get("action") if isinstance(res, dict) else None

    if not args.no_journal and rep["rows"]:
        try:
            layer = AG.AgentLayer(cfg)
            for r in rep["rows"]:
                layer.log_decision(
                    {"action": r["action"], "confidence": r["confidence"],
                     "reasons": [r["reason"]], "model": r["model"]},
                    extra={"status": "COUNCIL", "kind": "OPS_DECISION",
                           "question": args.question, "verdict": rep["verdict"]})
            rep["journal"] = "da ghi %d phieu" % len(rep["rows"])
        except Exception as e:  # noqa: BLE001
            rep["journal"] = "loi ghi journal: %s" % str(e)[:120]

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print("=== HOI DONG QUYET DINH | %d model | %.0fs ===" % (rep["n"], rep["seconds"]))
        print("  CAU HOI : %s" % args.question)
        print("  ALLOW = %s" % args.allow)
        print("  VETO  = %s" % args.veto)
        print("  %-34s %-10s %-5s %s" % ("MODEL", "PHIEU", "CONF", "LY DO"))
        for r in rep["rows"]:
            c = r["confidence"]
            print("  %-34s %-10s %-5s %s"
                  % (r["model"][:34], r["action"],
                     ("%.2f" % c) if isinstance(c, (int, float)) else "-", r["reason"][:90]))
        print("  --- KET QUA: %d ALLOW / %d VETO / %d khong y kien -> QUYET DINH: %s"
              % (rep["n_allow"], rep["n_veto"], rep["n_abstain"], rep["verdict"]))
        print("  -> %s" % (args.allow if rep["verdict"] == "ALLOW" else
                           args.veto if rep["verdict"] == "VETO" else "hoa/khong du phieu"))
        if rep.get("journal"):
            print("  journal: %s" % rep["journal"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
