"""Chan doan: vi sao agent REVIEW sau khi dong lenh van goi provider da chet?

    cd ../atb-live ; python ../autonomous-trading-bot/tools/diag_review.py

Vi sao (15/10): journal LIVE co 100% ban ghi `review_agent` = "loi provider: copilot CLI
rc=1: You have exceeded your monthly quota" du `.env` da co `AGENT_COUNCIL_COPILOT_UNTIL`.
Guard `_provider_blocked` (13/10) nam trong `turbo_demo.agent_vote_review`; cong cu nay
in ra: ten provider THAT cua layer review + ket qua `_provider_blocked` cho tung ten
=> biet ngay guard co khop ten hay khong (loi "ten provider khac nhau" rat kho thay).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def main() -> int:
    import agents as AG
    from config import Settings

    cfg = Settings()
    print("=== CHAN DOAN REVIEW AGENT | cwd=%s ===" % Path.cwd())
    print("  AGENTS_ENABLED=%s | AGENT_COUNCIL_COPILOT_UNTIL=%s"
          % (getattr(cfg, "agents_enabled", None),
             getattr(cfg, "agent_council_copilot_until", None)))
    try:
        import turbo_demo as TD
        layer = TD.agent_layer(cfg)
    except Exception as e:  # noqa: BLE001
        print("  [LOI] khong tao duoc layer review: %s" % str(e)[:200])
        return 1
    if layer is None:
        print("  layer review = None (agents dang TAT -> review se khong chay)")
        return 0
    prov = str(getattr(getattr(layer, "provider", None), "name", "") or "")
    print("  layer review: provider=%r model=%r enabled=%s"
          % (prov, getattr(layer, "model", None), layer.enabled()))
    print("  chi phi uoc tinh 1 lan review (1200 in/200 out): $%.6f"
          % float(AG.cost_usd(str(getattr(layer, "model", "") or ""), 1200, 200)))
    try:
        print("  ngan sach: %s" % layer.budget.snapshot())
    except Exception as e:  # noqa: BLE001
        print("  ngan sach: khong doc duoc (%s)" % str(e)[:60])
    norm = getattr(AG, "_provider_label", None)
    cands = [prov, prov.replace("_cli", ""), "copilot", "copilot_cli", "cline", "cline-pass"]
    if callable(norm):
        cands.insert(1, norm(prov))
    for name in dict.fromkeys(cands):
        try:
            why = AG._provider_blocked(name, cfg)
        except Exception as e:  # noqa: BLE001
            why = "LOI: %s" % str(e)[:80]
        print("  _provider_blocked(%-12s) -> %s" % (name, why or "KHONG BI CHAN"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
