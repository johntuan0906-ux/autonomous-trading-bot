"""Sinh `golden/cases.jsonl` — bo ca cho `tools/golden_set.py`.

    python tools/golden_build.py            # ghi golden/cases.jsonl
    python tools/golden_build.py --print    # chi in ra man hinh

Vi sao tach BUILD va RUN: ca phai **co dinh, versioned trong git** (golden set ma sinh lai moi
lan chay thi khong con la "bo ca chuan"). File nay chi tao 2 loai:
- ca VIET TAY (normal / edge / failure) tu du lieu da do trong `REPO_IDEAS` §23-28 va cac lop
  loi da va (B-030 dao dau SHORT, B-031 R rac, B-033 hoc lech, B-043 single-best-setup);
- ca DO TU JOURNAL (`journal_feats`): do tinh toan ven cua `feats` THAT (thieu key/NaN/ngoai
  dai) — phan "Measured Context" kiem tra duoc bang so lieu that.

KHONG lay KET QUA gia (PnL) lam dap an: lam vay la hoc lai qua khu (overfit) va ca se "sai"
oan khi thi truong doi. Dap an o day la DIEU KIEN HOP LE (clip, tran risk, min_n...).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import learner as L  # noqa: E402

OUT_PATH = ROOT / "golden" / "cases.jsonl"
#: Feature vector "trung tinh": moi trong so = 0 ⇒ p = sigmoid(b) ⇒ edge = 0 khi b = 0.
ZERO_W = {f: 0.0 for f in L.FEATURES}
#: Moi vi the 4 USDT risk tren equity 1000 = 0,4% (cau hinh TESTNET that, B-043).
POS = {"direction": "LONG", "entry": 100.0, "sl": 96.0, "qty": 1.0}


def _case(cid, kind, component, title, inp, output=None, must=None, must_not=None,
          source="synthetic") -> dict:
    return {"id": cid, "kind": kind, "component": component, "title": title,
            "input": inp, "source": source,
            "expect": {"output": output or {}, "must": list(must or []),
                       "must_not": list(must_not or [])}}


def curated() -> list:
    """Ca viet tay: moi ca chot 1 DIEU KIEN (khong chot 1 con so vo nghia)."""
    return [
        # ---- feats: clip + cong thuc (Measured Context) --------------------
        _case("syn-feats-clip", "edge", "feats",
              "diem tho 9/-9 phai bi CLIP ve [-1,1] (khong tin thang do tho)",
              {"tech_score": 9.0, "sent": -9.0},
              {"tech": 1.0, "sent": -1.0, "trend": -1.0, "vol_conf": -0.3,
               "retest": -0.2, "vwap": -1.0, "bb": 0.0, "sr": 0.0},
              ["tech:<=:1.0", "tech:>=:-1.0", "sent:>=:-1.0", "sent:<=:1.0"]),
        _case("syn-feats-flat-market", "edge", "feats",
              "ATR = 0 (thi truong dung yen) => vol_norm ve bien duoi -1",
              {"atr_pct": 0.0}, {"vol_norm": -1.0}, ["vol_norm:>=:-1.0"]),
        _case("syn-feats-neutral-default", "normal", "feats",
              "mac dinh trung tinh: khong tin hieu thi moi feature = 0",
              {}, {"tech": 0.0, "sent": 0.0, "rsi_bias": 0.0, "struct": 0.0,
                   "regime": 0.0, "htf": 0.0, "sweep": 0.0}),
        # ---- learner: luoi an toan + quy uoc dao dau SHORT (B-030) ---------
        _case("syn-learn-neutral-never-blocks", "failure", "learner_edge",
              "trong so = 0 => edge = 0 (model trung tinh KHONG duoc chan lenh)",
              {"weights": ZERO_W, "b": 0.0, "direction": "LONG",
               "feats": {"tech": 1.0, "regime": 1.0, "struct": 1.0}},
              {"edge": 0.0, "p_long": 0.5}, ["edge:>:-0.0001", "edge:<:0.0001"]),
        _case("syn-learn-strong-long", "normal", "learner_edge",
              "trong so duong + feats duong => edge duong (ung ho vao lenh)",
              {"weights": {"tech": 2.0}, "b": 0.0, "direction": "LONG",
               "feats": {"tech": 1.0}},
              {"edge": 0.761594, "p_long": 0.880797}, ["edge:>:0.5"]),
        _case("syn-learn-short-mirror", "normal", "learner_edge",
              "b = 0: SHORT phai la GUONG cua LONG (edge = -edge_long)",
              {"weights": {"tech": 2.0}, "b": 0.0, "direction": "SHORT",
               "feats": {"tech": 1.0}},
              {"edge": -0.761594}, ["edge:<:-0.5"]),
        _case("syn-learn-bias-long", "edge", "learner_edge",
              "b = 1 (thien lech LONG): edge LONG = 0,905 (khong phai 1 - 2p cu)",
              {"weights": {"tech": 2.0}, "b": 1.0, "direction": "LONG",
               "feats": {"tech": 1.0}},
              {"edge": 0.905148, "p_long": 0.952574}, ["edge:>:0.9"]),
        _case("syn-learn-bias-short-not-mirror", "edge", "learner_edge",
              "b != 0: SHORT KHONG duoc la -(LONG) — phai dao dau FEATURES (B-030)",
              {"weights": {"tech": 2.0}, "b": 1.0, "direction": "SHORT",
               "feats": {"tech": 1.0}},
              {"edge": -0.462117}, ["edge:>:-0.9"], ["edge:<=:-0.905148"]),
        # ---- strategy: phan loai setup -------------------------------------
        _case("syn-strategy-range-reversal", "normal", "strategy_classify",
              "range + tai S + nen xac nhan => D_RANGE_REVERSAL",
              {"direction": "LONG", "regime": "RANGE", "near_sr": "S",
               "pattern_bias": 1.0}, {"strategy": "D_RANGE_REVERSAL"}),
        _case("syn-strategy-none", "failure", "strategy_classify",
              "khong co gi khop => NONE (khong duoc bia ra setup)",
              {"direction": "LONG"}, {"strategy": "NONE"}),
        _case("syn-strategy-trend-pullback", "normal", "strategy_classify",
              "trend + htf thuan + RSI 50 => A_TREND_PULLBACK",
              {"direction": "LONG", "regime": "TREND_UP", "htf": 1, "rsi": 50.0},
              {"strategy": "A_TREND_PULLBACK"}),
        _case("syn-strategy-sweep-reclaim", "normal", "strategy_classify",
              "sweep nguoc huong + reclaim => C_LIQ_SWEEP_RECLAIM",
              {"direction": "LONG", "sweep": True, "sweep_bias": 1.0, "struct": 1.0},
              {"strategy": "C_LIQ_SWEEP_RECLAIM"}),
        # ---- strategy gate: blocklist + du mau ------------------------------
        _case("syn-gate-none-always-open", "edge", "strategy_gate",
              "NONE luon duoc qua (khong du thong tin de ket luan)",
              {"code": "NONE"}, {"blocked": False, "n": 0}),
        _case("syn-gate-blocklist", "normal", "strategy_gate",
              "co trong STRATEGY_BLOCK => chan TRUOC khi do mau",
              {"code": "A_TREND_PULLBACK", "blocklist": ["A_TREND_PULLBACK"],
               "stats": {}}, {"blocked": True, "n": 0},
              ["reason:contains:STRATEGY_BLOCK"]),
        _case("syn-gate-insufficient-sample", "edge", "strategy_gate",
              "n < min_n => KHONG chan (thieu mau thi khong duoc ket luan)",
              {"code": "A_TREND_PULLBACK", "min_n": 10,
               "stats": {"A_TREND_PULLBACK": {"n": 5, "wins": 1, "sum_r": -2.0}}},
              {"blocked": False, "n": 5, "avg_r": -0.4}),
        _case("syn-gate-negative-data", "normal", "strategy_gate",
              "du mau (n=30) + avgR am => chan",
              {"code": "A_TREND_PULLBACK", "min_n": 10,
               "stats": {"A_TREND_PULLBACK": {"n": 30, "wins": 5, "sum_r": -9.0}}},
              {"blocked": True, "n": 30, "avg_r": -0.3}),
        # ---- lessons gate: nguong TAT DINH, khong "cam nhan" -----------------
        _case("syn-lessons-gate-hit", "failure", "lessons_gate",
              "to hop n=40 avgR -0,5 => phai co trong danh sach chan",
              {"buckets": {"RANGE|LONG": {"n": 40, "avg_r": -0.5, "wr": 0.3,
                                          "pnl": -40.0}}},
              {"n_gates": 1}, ["keys:contains:RANGE"]),
        _case("syn-lessons-gate-small-n", "edge", "lessons_gate",
              "cung avgR nhung n=5 => KHONG chan (min_n = 20)",
              {"buckets": {"RANGE|LONG": {"n": 5, "avg_r": -0.5, "wr": 0.0,
                                          "pnl": -5.0}}},
              {"n_gates": 0, "keys": []}),
        # ---- tran risk danh muc (P0-6, B-043) -------------------------------
        _case("syn-risk-cap-blocked", "failure", "risk_cap",
              "4 vi the x 0,4% = 1,6% + moi 0,4% > tran 1,6% => CHAN",
              {"equity": 1000.0, "cap_pct": 1.6, "new_risk_usd": 4.0,
               "positions": {"A": POS, "B": POS, "C": POS, "D": POS}},
              {"ok": False, "cur_pct": 1.6}, ["reason:contains:tran risk"]),
        _case("syn-risk-cap-ok", "normal", "risk_cap",
              "danh muc rong + 0,6% < tran 2% => cho vao",
              {"equity": 1000.0, "cap_pct": 2.0, "new_risk_usd": 6.0,
               "positions": {}},
              {"ok": True, "reason": "ok", "cur_pct": 0.0}),
        _case("syn-risk-cap-boundary", "edge", "risk_cap",
              "cham DUNG tran (2,0% = cap) => khong duoc chan oan",
              {"equity": 1000.0, "cap_pct": 2.0, "new_risk_usd": 20.0,
               "positions": {}}, {"ok": True, "cur_pct": 0.0}),
        # ---- so vi the (B-043: "single best setup" chi khi 1 slot) ----------
        _case("syn-portfolio-multi-slot", "normal", "portfolio_open",
              "MAX_POSITIONS=4 + dang 1 vi the => VAN mo duoc cap khac (B-043)",
              {"max_positions": 4, "symbol": "ETH/USDT:USDT", "direction": "LONG",
               "positions": {"BTC/USDT:USDT": POS}},
              {"ok": True, "reason": "ok", "n_open": 1}),
        _case("syn-portfolio-single-slot", "edge", "portfolio_open",
              "MAX_POSITIONS=1 => giu luat 'single best setup'",
              {"max_positions": 1, "symbol": "ETH/USDT:USDT", "direction": "LONG",
               "positions": {"BTC/USDT:USDT": POS}},
              {"ok": False}, ["reason:contains:single-best-setup"]),
        _case("syn-portfolio-duplicate", "failure", "portfolio_open",
              "cung symbol => khong bao gio mo 2 lan",
              {"max_positions": 4, "symbol": "BTC/USDT:USDT", "direction": "LONG",
               "positions": {"BTC/USDT:USDT": POS}},
              {"ok": False}, ["reason:contains:duplicate"]),
        _case("syn-portfolio-max-reached", "edge", "portfolio_open",
              "da du so vi the => chan",
              {"max_positions": 2, "symbol": "ETH/USDT:USDT", "direction": "LONG",
               "positions": {"BTC/USDT:USDT": POS, "SOL/USDT:USDT": POS}},
              {"ok": False}, ["reason:contains:max positions"]),

        # ---- (09/11, B-046) CONG AN TOAN: tam dung vao lenh -------------------
        # Tai lieu "Golden-Set Eval" nêu dung 4 tinh huong nay; bo ca cu phu "tinh toan"
        # ma thieu cong lam bot DUNG — sai o cong dung moi la thu ton tien that.
        _case("syn-entries-paused-blocks", "failure", "entries_gate",
              "dang tam dung vao lenh => KHONG mo lenh moi, ly do phai doc duoc",
              {"paused": True, "reason": "hoi dong 4-0 VETO resume"},
              {"paused": True, "until_set": False}, ["reason:contains:hoi dong"]),
        _case("syn-entries-expired-resumes", "edge", "entries_gate",
              "tam dung CO HAN: qua 24h phai TU MO LAI (chong 'tam dung roi quen')",
              {"paused": True, "reason": "nguoi sau kill-switch", "hours": 24,
               "advance_sec": 25 * 3600},
              {"paused": False}, ["reason:contains:het han"]),
        _case("syn-entries-corrupt-failsafe", "failure", "entries_gate",
              "file trang thai HONG => coi nhu DANG tam dung (fail-safe, khong tu mo lai)",
              {"corrupt": True},
              {"paused": True, "corrupt": True, "until_set": True}),
        # ---- CONG: san chan IP (-1003 / 418) ---------------------------------
        _case("syn-api-ban-1003", "normal", "api_ban",
              "thong bao -1003: doc moc het bi chan (ms -> giay) + ma API_BAN",
              {"text": '{"code":-1003,"msg":"Way too many requests; IP(222.253.53.82) '
                       'banned until 1793987694544"}'},
              {"banned": True, "code": "API_BAN", "until": 1793987694.544}),
        _case("syn-api-ban-none", "edge", "api_ban",
              "loi KHONG phai chan IP => until = 0 (khong tu nghi 15 phut vo co)",
              {"text": '{"code":-2019,"msg":"Margin is insufficient."}'},
              {"banned": False, "until": 0.0, "code": "ORDER_REJECT"}),
        # ---- KILL-SWITCH (bao ve VON) ----------------------------------------
        _case("syn-kill-3-losses-ok", "normal", "kill_switch",
              "3 lan thua lien tiep < 5 => CHUA dung bot",
              {"losses": 3, "balance": 1000.0},
              {"halt": False, "tripped": False, "consec_losses": 3}),
        _case("syn-kill-5-losses-trip", "failure", "kill_switch",
              "5 lan thua lien tiep => PHAI dung (muc 12), ly do phai doc duoc",
              {"losses": 5, "balance": 1000.0},
              {"halt": True, "tripped": True}, ["reason:contains:consecutive"]),
        _case("syn-kill-daily-dd", "failure", "kill_switch",
              "lo trong ngay 28,3% (LIVE that 38,44 -> 27,56 USDT) => trip",
              {"start_equity": 38.44, "start_balance": 38.44, "balance": 27.56},
              {"halt": True, "tripped": True}, ["reason:contains:daily loss"]),
        _case("syn-kill-dust-not-counted", "edge", "kill_switch",
              "loss DUST 0,0011 USDT < 0,5 => KHONG tinh la lan thua (B-027)",
              {"losses": 5, "balance": 1000.0, "loss_pnl": -0.0011},
              {"halt": False, "tripped": False, "consec_losses": 0}),
        # ---- CONG: tu sang LIVE (tien that) ----------------------------------
        _case("syn-golive-no-keys", "failure", "go_live",
              "chua co key LIVE => KHONG tu sang tien that",
              {"armed": True, "equity": 100.0, "ready": {"ok": True},
               "guard": {"ok": True}, "live_keys": False},
              {"ok": False}, ["why:contains:BINANCE_LIVE_API_KEY"]),
        _case("syn-golive-equity-low", "failure", "go_live",
              "vi that 5 USDT < 20 USDT toi thieu => KHONG doi che do",
              {"armed": True, "equity": 5.0, "ready": {"ok": True},
               "guard": {"ok": True}, "min_equity": 20.0},
              {"ok": False}, ["why:contains:toi thieu"]),
        _case("syn-golive-ok", "normal", "go_live",
              "du dieu kien (armed + key + san sang + equity 25) => cho phep doi",
              {"armed": True, "equity": 25.0, "ready": {"ok": True},
               "guard": {"ok": True}, "min_equity": 20.0},
              {"ok": True}),
        # ---- AUTONOMY LADDER: khi nao hoi dong duoc NANG quyen veto ----------
        _case("syn-council-ready-no", "failure", "council_ready",
              "brier 0,341 > 0,25 + chi 31 mau => KHONG duoc nang quyen (so lieu THAT)",
              {"rep": {"cases": 31, "calibration": {"brier": 0.341},
                       "per_model": {"m1": {"matched": 12, "value_r": 0.05}}}},
              {"ready": False}, ["reasons:contains:brier"]),
        _case("syn-council-ready-yes", "normal", "council_ready",
              "brier 0,20 + 1 model value_r>0 voi n>=30 => DU dieu kien (nguoi van xac nhan)",
              {"rep": {"cases": 40, "calibration": {"brier": 0.20},
                       "per_model": {"m1": {"matched": 40, "value_r": 0.12}}}},
              {"ready": True, "cases": 40, "models_ok": ["m1"]}),

        # ---- (09/11) TUOI DU LIEU theo nguon (#4): nen chet thi KHONG duoc quyet dinh --
        _case("syn-fresh-all-fresh", "normal", "freshness",
              "nen 20 s + OI 600 s => moi nguon tuoi, duoc quyet dinh",
              {"ages": {"candles": 20.0, "deriv": 600.0, "liq": 600.0}},
              {"ok": True, "blocking": [], "stale": [], "reason_code": ""}),
        _case("syn-fresh-candles-stale", "edge", "freshness",
              "nen 1500 s > TTL 900 s: CU nhung chua chet => van duoc quyet dinh (co canh bao)",
              {"ages": {"candles": 1500.0}}, {"ok": True, "blocking": []},
              ["by_source.candles.level:==:stale"]),
        _case("syn-fresh-candles-dead", "failure", "freshness",
              "nen 5000 s > 3x TTL => CHET, phai chan quyet dinh + ma DATA_STALE",
              {"ages": {"candles": 5000.0, "deriv": 60.0}},
              {"ok": False, "blocking": ["candles"], "reason_code": "DATA_STALE"}),
        _case("syn-fresh-missing-candles", "failure", "freshness",
              "KHONG co moc thoi gian nen => coi nhu CHET (khong duoc coi la moi)",
              {"ages": {"deriv": 60.0}},
              {"ok": False, "blocking": ["candles"], "reason_code": "DATA_STALE"}),
        _case("syn-fresh-context-dead-not-blocking", "edge", "freshness",
              "OI/thanh ly chet chi la THIEU BOI CANH, khong duoc chan lenh",
              {"ages": {"candles": 10.0, "deriv": 99999.0}},
              {"ok": True, "blocking": [], "reason_code": ""},
              ["dead:contains:deriv"]),
    ]


def journal_cases(journal: str = "logs/journal.jsonl", limit: int = 500) -> list:
    """Ca do tu JOURNAL THAT: `feats` phai du 20 key, khong NaN, trong [-1,1].

    Day la ca "normal" nhung chay tren du lieu THAT ⇒ bat duoc drift feature (them/bot key,
    NaN do chia 0 khi ATR = 0) — thu ma unit test voi du lieu gia khong bao gio thay.
    """
    return [_case("jrn-feats-integrity", "normal", "journal_feats",
                  "feats that trong journal: du key, khong NaN, trong [-1,1]",
                  {"journal": journal, "limit": limit},
                  {"violations": []}, ["n_checked:>=:100"], source="journal")]


def build(journal: str = "logs/journal.jsonl", limit: int = 500) -> list:
    """Toan bo bo ca: viet tay (behavior contract) + do tu journal (du lieu that)."""
    return curated() + journal_cases(journal, limit)


def write_cases(cases: list, path=OUT_PATH) -> str:
    """Ghi JSONL qua `atomic` (1 dong 1 ca) — ca phai on dinh va versioned trong git."""
    import atomic
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases)
    atomic.write_text_atomic(str(p), text)
    return str(p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sinh golden/cases.jsonl cho golden-set eval")
    ap.add_argument("--journal", default="logs/journal.jsonl", help="journal de do feats that")
    ap.add_argument("--limit", type=int, default=500, help="so ban ghi OPEN lay mau")
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--print", action="store_true", dest="do_print",
                    help="in ra man hinh, khong ghi file")
    args = ap.parse_args(argv)
    cases = build(args.journal, args.limit)
    if args.do_print:
        print(json.dumps(cases, ensure_ascii=False, indent=1))
        return 0
    p = write_cases(cases, args.out)
    kinds: dict = {}
    comps: dict = {}
    for c in cases:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
        comps[c["component"]] = comps.get(c["component"], 0) + 1
    print("da ghi %s: %d ca | kind: %s | cong: %s"
          % (p, len(cases), ", ".join("%s=%d" % kv for kv in sorted(kinds.items())),
             ", ".join("%s=%d" % kv for kv in sorted(comps.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

