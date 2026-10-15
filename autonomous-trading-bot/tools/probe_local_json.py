"""Chan doan: model LOCAL (llamafile) co tuan theo rang buoc JSON khong?

    python tools/probe_local_json.py
    python tools/probe_local_json.py --question "..." --timeout 120

Vi sao (15/10): model local 3B do duoc `parse=ok` nhung `raw_text` la **vi du JSON lap
lai** (no "day" dinh dang chu khong phan tich lenh) => phieu rong thong tin, `value_r`
am. `agents.OpenAICompatProvider(json_mode=True)` thu lan luot
`json_schema -> json_object -> khong rang buoc`; cong cu nay cho biet server local
THUC SU chap nhan che do nao (thay vi doan).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Kiem tra rang buoc JSON cua model local")
    ap.add_argument("--question", default="Nen reset kill-switch TESTNET (tai khoan demo) "
                                         "de co du lieu hoc? Tra ALLOW neu nen, VETO neu khong.")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    import agents as AG
    from config import Settings

    cfg = Settings()
    p = AG.OpenAICompatProvider(model=str(getattr(cfg, "agent_council_local", "local")),
                                base_url=str(getattr(cfg, "agent_local_base_url", "")),
                                api_key=str(getattr(cfg, "agent_local_api_key", "local")),
                                json_mode=True)
    sysmsg = ("Tra ve DUY NHAT 1 JSON: {\"action\":\"ALLOW|VETO|NO_OPINION\","
              "\"confidence\":0..1,\"reasons\":[\"...\"],\"risk_flags\":[\"...\"]}")
    try:
        out = p.complete(sysmsg, args.question, timeout=args.timeout)
    except Exception as e:  # noqa: BLE001
        print("[LOI] goi model local that bai: %s" % str(e)[:200])
        return 1
    parsed = AG.parse_decision(out.get("text") or "", role="critic")
    rep = {"json_mode_used": p.json_mode_used, "text": out.get("text"),
           "tokens_in": out.get("tokens_in"), "tokens_out": out.get("tokens_out"),
           "action": (parsed or {}).get("action"), "note": (parsed or {}).get("note")}
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print("=== RANG BUOC JSON CHO MODEL LOCAL ===")
        print("  che do server chap nhan : %s  (schema > object > off)" % rep["json_mode_used"])
        print("  phieu doc duoc          : %s (%s)" % (rep["action"], rep["note"]))
        print("  token                   : in=%s out=%s" % (rep["tokens_in"], rep["tokens_out"]))
        print("  tra loi                 : %s" % str(rep["text"])[:300].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
