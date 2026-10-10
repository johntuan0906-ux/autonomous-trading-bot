"""So sánh 2 chế độ chạy SONG SONG (TESTNET học ↔ LIVE thực chiến) + HỘI ĐỒNG quyết định.

    python compare_modes.py                 # so sanh + goi hoi dong AI de chon phuong an
    python compare_modes.py --no-council    # chi so sanh (nhanh, khong ton luot AI)
    python compare_modes.py --since 0       # tinh ca lich su (mac dinh: tu luc tach 2 instance)
    python compare_modes.py --apply         # ghi de xuat vao .env cua instance LIVE (co tran cung)
    python compare_modes.py --json

Cách hoạt động:
1. Đọc **2 journal riêng** (repo chính = TESTNET, `../atb-live` = LIVE) — chỉ tính lệnh
   **sau mốc tách** (`../atb-live/logs/.split_ts`) để so sánh công bằng.
2. In bảng so sánh: n · WR · PF(R) · E(R) · PnL · lý do thoát.
3. **Quy tắc TẤT ĐỊNH** chọn phương án (không phụ thuộc AI) — đây là thứ được `--apply`.
4. **HỘI ĐỒNG AI** (`agents.council_decision`) đọc bảng so sánh + danh sách phương án để
   **tư vấn** thêm (advisory). Hội đồng không tự đổi tiền/risk — giữ đúng nguyên tắc của dự án:
   AI chỉ cố vấn, mọi thay đổi rủi ro đều do con người/ngưỡng tất định quyết.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE_DIR = ROOT.parent / "atb-live"
SPLIT = LIVE_DIR / "logs" / ".split_ts"

OPTIONS = ("TANG_RISK_LIVE", "GIU_NGUYEN", "GIAM_RISK_LIVE", "PAUSE_LIVE", "CHI_TESTNET")
# Tran cung khi --apply (khong bao gio vuot cac muc nay du hoi dong noi gi)
RISK_MIN, RISK_MAX = 0.25, 1.0
MAXPOS_MIN, MAXPOS_MAX = 1, 3


def split_ts() -> float:
    """Mốc tách 2 instance (chỉ so sánh lệnh sau mốc này). 0 = tính cả lịch sử."""
    try:
        return float(SPLIT.read_text(encoding="utf-8").strip())
    except Exception:  # noqa: BLE001
        return 0.0


def mode_stats(path: Path, since: float = 0.0) -> dict:
    """Thống kê 1 chế độ từ journal riêng của nó."""
    from monitor_report import load_journal, match_pairs, stats
    if not path.exists():
        return {"n": 0, "wr": 0.0, "pf_r": 0.0, "e_r": 0.0, "pnl": 0.0,
                "err": "khong co journal"}
    opens, closes = load_journal(str(path))
    if since:
        closes = [c for c in closes if float(c.get("ts") or 0.0) >= since]
        opens = [o for o in opens if float(o.get("ts") or 0.0) >= since]
    st = stats(match_pairs(opens, closes)[0])
    st["err"] = ""
    return st


def decide(t: dict, l: dict) -> tuple:
    """Quy tắc TẤT ĐỊNH (không AI) — phương án + lý do. Đây là thứ `--apply` dùng."""
    ln, lp = int(l.get("n") or 0), float(l.get("pf_r") or 0.0)
    tp, tn = float(t.get("pf_r") or 0.0), int(t.get("n") or 0)
    if ln < 20:
        return "GIU_NGUYEN", "mau LIVE con it (n=%d < 20) -> giu nguyen, tiep tuc thu" % ln
    if lp < 1.0:
        return "GIAM_RISK_LIVE", "PF(R) LIVE %.3f < 1.0 -> giam risk LIVE" % lp
    if lp < 1.1 and tp >= 1.2:
        return "CHI_TESTNET", ("LIVE %.3f < 1.1 trong khi TESTNET %.3f >= 1.2 (n=%d) "
                              "-> hoc them o testnet" % (lp, tp, tn))
    if lp >= 1.2 and tp >= 1.2:
        return "TANG_RISK_LIVE", "ca 2 che do PF>=1.2 (LIVE %.3f, TESTNET %.3f) -> tang risk" % (lp, tp)
    return "GIU_NGUYEN", "LIVE %.3f / TESTNET %.3f -> giu nguyen" % (lp, tp)


def council_advice(rep: dict, log=None) -> dict:
    """HỘI ĐỒNG AI tư vấn chọn phương án (advisory — không tự đổi tiền/risk)."""
    try:
        from agents import AgentLayer, council_decision
        from config import Settings
        layer = AgentLayer(cfg=Settings())
        payload = {
            "task": "chon_phuong_an_2_che_do",
            "cau_hoi": ("Bot dang chay SONG SONG: TESTNET (de hoc) va LIVE (tien that). "
                        "Chon MOT phuong an phu hop nhat cho LIVE."),
            "phuong_an": list(OPTIONS),
            "so_sanh": {
                "testnet": {k: rep["testnet"].get(k) for k in ("n", "wr", "pf_r", "e_r")},
                "live": {k: rep["live"].get(k) for k in ("n", "wr", "pf_r", "e_r")},
                "quy_tac_tat_dinh": rep["pick"][0],
                "ly_do_tat_dinh": rep["pick"][1],
            },
        }
        res = council_decision(layer, payload, log=log)
        out = {"action": str(res.get("action") or ""), "why": str(res.get("why") or "")[:400],
               "pick": "", "source": "council"}
        # Hoi dong 3 vai co the tra NO_OPINION voi cau hoi "meta" (khong phai setup giao dich)
        # -> hoi them 1 vai arbiter va KHOP ten phuong an trong cau tra loi.
        txt = " ".join([out["action"], out["why"]])
        if "NO_OPINION" in out["action"].upper() or not out["action"]:
            try:
                d = layer.vote("arbiter", payload)
                parts = [str(getattr(d, "action", "") or ""),
                         str(getattr(d, "note", "") or "")]
                parts += [str(x) for x in (getattr(d, "reasons", None) or [])]
                txt = " ".join(parts)
                out["action"] = str(getattr(d, "action", "") or "") or "NO_OPINION"
                out["why"] = txt[:400]
                out["source"] = "arbiter"
            except Exception as e:  # noqa: BLE001
                out["why"] = (out["why"] + " | arbiter loi: " + str(e)[:80]).strip(" |")
        up = txt.upper()
        out["pick"] = next((o for o in OPTIONS if o in up), "")
        return out
    except Exception as e:  # noqa: BLE001
        return {"action": "", "why": "hoi dong loi/khong san sang: %s" % str(e)[:160]}


def apply_pick(pick: str, live_dir: Path | None = None) -> dict:
    """Ghi phương án vào `.env` của instance LIVE (giới hạn trong TRAN CUNG)."""
    import state_sync as SS
    live_dir = live_dir or LIVE_DIR
    envp = live_dir / ".env"
    if not envp.exists():
        return {"ok": False, "err": "khong co %s" % envp}
    cur = envp.read_text(encoding="utf-8")
    if pick == "GIAM_RISK_LIVE":
        upd = {"RISK_PER_TRADE_PCT": "0.25", "MAX_POSITIONS": "1"}
    elif pick == "CHI_TESTNET":
        upd = {"RISK_PER_TRADE_PCT": "0.25", "MAX_POSITIONS": "1", "MIN_PF": "1.2"}
    elif pick == "PAUSE_LIVE":
        upd = {"MAX_POSITIONS": "0", "RISK_PER_TRADE_PCT": "0.25"}
    elif pick == "TANG_RISK_LIVE":
        upd = {"RISK_PER_TRADE_PCT": "0.75", "MAX_POSITIONS": "3"}
    else:
        return {"ok": True, "noop": True, "pick": pick}
    # tran cung: khong bao gio vuot RISK_MAX/MAXPOS_MAX
    r = float(upd.get("RISK_PER_TRADE_PCT", RISK_MIN))
    p = int(float(upd.get("MAX_POSITIONS", MAXPOS_MIN)))
    upd["RISK_PER_TRADE_PCT"] = "%g" % min(max(r, RISK_MIN), RISK_MAX)
    upd["MAX_POSITIONS"] = str(min(max(p, MAXPOS_MIN), MAXPOS_MAX))
    envp.write_text(SS.set_env_values(cur, upd), encoding="utf-8")
    return {"ok": True, "updates": upd, "env": str(envp)}


def render(rep: dict) -> str:
    L: list = []
    L.append("=" * 78)
    L.append("SO SANH 2 CHE DO (song song) | %s | tinh tu moc tach %s"
             % (rep["ts_human"], rep["since_human"]))
    L.append("=" * 78)
    L.append("  %-10s %6s %7s %8s %8s %10s" % ("CHE DO", "n", "WR%", "PF(R)", "E(R)", "PnL$"))
    for name, st in (("TESTNET", rep["testnet"]), ("LIVE", rep["live"])):
        if st.get("err"):
            L.append("  %-10s  (%s)" % (name, st["err"]))
            continue
        L.append("  %-10s %6d %7.1f %8.3f %+8.3f %+10.3f"
                 % (name, int(st.get("n") or 0), float(st.get("wr") or 0),
                    float(st.get("pf_r") or 0), float(st.get("e_r") or 0),
                    float(st.get("pnl") or 0)))
    L.append("")
    L.append("QUY TAC TAT DINH -> %s" % rep["pick"][0])
    L.append("  ly do: %s" % rep["pick"][1])
    adv = rep.get("council") or {}
    if adv:
        L.append("")
        L.append("HOI DONG AI (tu van) -> %s%s"
                 % (adv.get("action") or "(khong co y kien)",
                    ("  [chon: %s]" % adv["pick"]) if adv.get("pick") else ""))
        if adv.get("why"):
            L.append("  %s" % str(adv["why"])[:400])
        L.append("  (hoi dong CHI tu van — muc risk/so vi the do nguong tat dinh + ban quyet)")
    L.append("=" * 78)
    return "\n".join(L)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="So sanh TESTNET vs LIVE + hoi dong quyet dinh")
    ap.add_argument("--no-council", action="store_true", help="khong goi hoi dong AI")
    ap.add_argument("--since", type=float, default=None, help="moc thoi gian (0 = ca lich su)")
    ap.add_argument("--apply", action="store_true", help="ghi phuong an vao .env instance LIVE")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    since = split_ts() if args.since is None else float(args.since)
    t = mode_stats(ROOT / "logs" / "journal.jsonl", since)
    l = mode_stats(LIVE_DIR / "logs" / "journal.jsonl", since)
    pick = decide(t, l)
    rep = {"ts_human": time.strftime("%d/%m/%Y %H:%M:%S"),
           "since_human": (time.strftime("%d/%m %H:%M", time.localtime(since)) if since
                           else "(ca lich su)"),
           "testnet": t, "live": l, "pick": pick, "council": {}}
    if not args.no_council:
        rep["council"] = council_advice(rep)
    print(render(rep))
    if args.apply:
        res = apply_pick(pick[0])
        print("APPLY: %s" % res)
        rep["apply"] = res
    if args.json:
        small = {k: rep[k] for k in ("ts_human", "testnet", "live", "pick", "council")}
        print(json.dumps(small, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
