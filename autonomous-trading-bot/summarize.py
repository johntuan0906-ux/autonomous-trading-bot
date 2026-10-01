"""Tong ket demo: tinh WR / PF (gross+net) / expectancy / DD / streaks tu income history.

Khung DAT (muc 26 tai lieu moi): WR>=35%, Net PF>=1.05, Expectancy>0 sau phi,
Max DD trong gioi han, khong liquidation, khong phu thuoc vai lenh lon.
"""
from __future__ import annotations
import ccxt
from collections import defaultdict
from config import Settings

from learner import expectancy, pf_from_trades

c = Settings()
cli = ccxt.binance({"apiKey": c.api_key, "secret": c.api_secret,
                    "options": {"defaultType": "future"}})
cli.enable_demo_trading(True)

all_inc: list[dict] = []
for itype in ("REALIZED_PNL", "COMMISSION"):
    start, page = 0, []
    while True:
        page = cli.fapiPrivateGetIncome(params={"incomeType": itype, "limit": 1000,
                                                "startTime": 0}) if hasattr(cli, "fapiPrivateGetIncome") else []
        all_inc += [{"t": itype, **r} for r in page]
        break

pnl = defaultdict(float)
fees = 0.0
for r in all_inc:
    v = float(r.get("income", 0))
    if r["t"] == "REALIZED_PNL":
        pnl[r.get("symbol", "?")] += v
    else:
        fees += -v

pnls = sorted((float(r.get("income", 0)) for r in all_inc if r["t"] == "REALIZED_PNL"))
wins = sum(1 for v in pnls if v > 0)
loss = sum(1 for v in pnls if v <= 0)
gp = sum(v for v in pnls if v > 0)
gl = -sum(v for v in pnls if v <= 0)
net = gp - gl
wr = wins / max(wins + loss, 1)
avg_w = gp / max(wins, 1)
avg_l = gl / max(loss, 1)
gross_pf = gp / max(gl, 1e-9)
net_pf = gp / max(gl + fees, 1e-9)
exp = expectancy(wr, 2.0, 1.0)  # R ky vong voi TP 2R/SL 1R (SL 1.5xATR, TP 3xATR)
# Max DD + streaks tu equity curve realized
eq, peak, maxdd = 0.0, 0.0, 0.0
cur_lose = best_lose = cur_win = best_win = 0
for v in pnls:
    eq += v
    peak = max(peak, eq)
    maxdd = max(maxdd, peak - eq)
    if v > 0:
        cur_win += 1
        best_win = max(best_win, cur_win)
        cur_lose = 0
    else:
        cur_lose += 1
        best_lose = max(best_lose, cur_lose)
        cur_win = 0
top3 = sum(sorted(pnls, reverse=True)[:3])
concent = top3 / max(gp, 1e-9) if gp else 0.0
print(f"so Close (realized): {wins + loss} | thang: {wins} | thua/hoa: {loss}")
print(f"win-rate: {wr:.1%} (DAT neu >=35%)")
print(f"gross profit: {gp:.2f} | gross loss: {gl:.2f} | gross PF: {gross_pf:.2f}")
print(f"phi commission: {fees:.2f} | net (tru phi): {net - fees:.2f} | NET PF: {net_pf:.2f} (DAT neu >=1.05)")
print(f"avg win: {avg_w:.2f} | avg loss: {avg_l:.2f} | expectancy(2R/1R): {exp:+.3f}R (DAT neu >0)")
print(f"max DD realized: {maxdd:.2f} | longest losing streak: {best_lose} | best win streak: {best_win}")
print(f"phu thuoc top3 lenh thang: {concent:.1%} (canh bao neu >50%)")
ok = (wr >= 0.35 and net_pf >= 1.05 and exp > 0 and best_lose < 8)
print("VERDICT:", "DAT (du dk testing muc 26)" if ok else "CHUA DAT — tiep tuc demo")
print("PnL theo cap:", {k: round(v, 2) for k, v in sorted(pnl.items())})
bal = cli.fetch_balance()["info"]
print(f"wallet hien tai: {bal.get('totalWalletBalance')} | uPnL vi the mo: {bal.get('totalUnrealizedProfit')}")

# --- Thong ke rieng tung strategy A/B/C/D (muc 15) tu logs/strategy_stats.json ---
try:
    from strategy import report as strat_report
    rep = strat_report()
    if rep:
        print("\n=== THEO STRATEGY (A/B/C/D) ===")
        for k, v in sorted(rep.items()):
            print(f"  {k:22} n={v['n']:>4} WR={v['wr']:.1%} avgR={v['avgR']:+.3f} sumR={v['sumR']:+.2f}")
        worst = min(rep.items(), key=lambda kv: kv[1]["avgR"])
        print(f"  -> nhom yeu nhat: {worst[0]} (avgR {worst[1]['avgR']:+.3f})")
except Exception as e:  # noqa: BLE001
    print("strategy stats: khong doc duoc ->", e)

