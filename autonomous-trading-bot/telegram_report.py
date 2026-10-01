"""Bao cao trang thai bot -> Telegram (CHI DOC: khong dat/huy lenh, khong sua state).

Tra loi 2 cau hoi hay gap:
  1) Vi the dang thay tren san nam o TESTNET (demo, tien gia) hay LIVE (tien that)?
     -> Doi chieu: client ma BOT dung (demo.binance.com) + thu doc endpoint LIVE
        bang chinh key do. Key demo -> LIVE tra ve -2015 => ket luan chac chan.
  2) Kill-switch dang the nao? "trip" bao nhieu lan? Co dang chan bot khong?
     -> risk_state.json (state song sot qua restart) + dem dong log THAT SU la trip
        (khac voi dong "dang NGUNG" lap lai moi lan supervisor restart).

Chay:
    python telegram_report.py            # thu thap + gui Telegram
    python telegram_report.py --dry      # chi in man hinh, khong gui
    python telegram_report.py --no-net   # bo qua buoc goi san (doc file local)
    python telegram_report.py --journal logs/journal.jsonl --log logs/turbo_err.log

An toan: moi lenh goi san o day deu la READ-ONLY (fetch_positions/fetch_balance/
fetch_open_orders). Khong co create/cancel order nao trong file nay.
"""
from __future__ import annotations

import argparse
import json
import time

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

import notify  # noqa: E402  (gui Telegram, tai dung convention san co)
from monitor_report import load_journal, match_pairs, stats  # noqa: E402

MAX_LEN = 4000            # gioi han 1 message Telegram
KILL_FRESH = "ERROR KILL-SWITCH:"
KILL_BLOCKED = "KILL-SWITCH dang NGUNG"


def read_json(path: str, default: dict | None = None) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001
        return dict(default or {})


def dem_kill(log_path: str) -> dict:
    """Dem DUNG so lan trip that (dong 'ERROR KILL-SWITCH:') va so dong bi chan lap.

    Vi sao can: supervisor restart moi ~5 phut -> moi lan in 1 dong 'dang NGUNG'.
    4810 dong nhu vay KHONG co nghia la 4810 lan trip.
    """
    trips, blocked, first = 0, 0, ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                if KILL_FRESH in ln:
                    trips += 1
                    if not first:
                        first = ln.strip()
                elif KILL_BLOCKED in ln:
                    blocked += 1
    except OSError:
        pass
    return {"trips": trips, "blocked": blocked, "first_trip": first}


def _fmt_money(v) -> str:
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "?"


def _fmt_ts(ts, fmt: str = "%Y-%m-%d %H:%M") -> str:
    try:
        return time.strftime(fmt, time.localtime(float(ts)))
    except (TypeError, ValueError, OSError):
        return "?"


def _api_url(cli) -> str:
    """Url REST ma client dang dung. ccxt luc tra ve PHANG, luc LONG nhau
    ({'api': {'private': ...}}) -> phai thu ca 2 kieu, neu khong se in ra ca dict.
    """
    u = getattr(cli, "urls", None) or {}
    cands = [u]
    for k in ("api", "test", "demo"):
        v = u.get(k) if isinstance(u, dict) else None
        if isinstance(v, dict):
            cands.append(v)
    for c in cands:
        for key in ("fapiPrivate", "private", "fapiPublic"):
            v = c.get(key) if isinstance(c, dict) else None
            if isinstance(v, str) and v:
                return v
    return "?"


def probe_san(cfg, pair: str | None = None) -> dict:
    """READ-ONLY: client BOT dung (demo) vs thu doc LIVE bang cung key.

    pair=None -> lay TAT CA vi the dang mo (bot chay 8 cap).
    Tra ve {'demo': {...}, 'live': {...}} — 'live.ok=False' + loi -2015 nghia la
    key chi co hieu luc tren demo/testnet => vi the nhin thay KHONG phai tien that.
    """
    out: dict = {"demo": {}, "live": {}}
    try:
        import ccxt  # type: ignore
    except ImportError:
        out["err"] = "thieu ccxt — chay: pip install ccxt"
        return out

    cli = None
    try:
        cli = ccxt.binance({"apiKey": cfg.api_key, "secret": cfg.api_secret,
                            "options": {"defaultType": "future"},
                            "enableRateLimit": True})
        try:
            cli.enable_demo_trading(True)      # giong exchange.py (bot that)
        except Exception:  # noqa: BLE001
            cli.set_sandbox_mode(True)         # fallback cu
        out["demo"]["api_url"] = _api_url(cli)
        bal = cli.fetch_balance()
        info = bal.get("info") or {}
        eq = None
        for k in ("totalMarginBalance", "totalWalletBalance"):
            try:
                eq = float(info.get(k))
                break
            except (TypeError, ValueError):
                continue
        out["demo"]["equity"] = eq
        poss = []
        for p in cli.fetch_positions([pair] if pair else None):
            qty = float(p.get("contracts") or 0)
            if qty == 0:
                continue
            _ip = p.get("info") or {}
            poss.append({"symbol": p.get("symbol"), "side": p.get("side"),
                         "qty": qty, "entry": p.get("entryPrice"),
                         "mark": p.get("markPrice"), "upnl": p.get("unrealizedPnl"),
                         "lev": p.get("leverage") or _ip.get("leverage")})
        out["demo"]["positions"] = poss
        try:
            out["demo"]["orders"] = len(cli.fetch_open_orders(pair))
        except Exception as e:  # noqa: BLE001
            out["demo"]["orders_err"] = str(e)[:120]
    except Exception as e:  # noqa: BLE001
        out["demo"]["err"] = str(e)[:200]
    finally:
        try:
            if cli is not None and hasattr(cli, "close"):
                cli.close()
        except Exception:  # noqa: BLE001
            pass

    try:
        live = ccxt.binance({"apiKey": cfg.api_key, "secret": cfg.api_secret,
                             "options": {"defaultType": "future"},
                             "enableRateLimit": True})
        out["live"]["api_url"] = _api_url(live)
        try:
            bal = live.fetch_balance()         # READ-ONLY
            info = bal.get("info") or {}
            out["live"]["ok"] = True
            out["live"]["equity"] = info.get("totalMarginBalance")
        except Exception as e:  # noqa: BLE001
            out["live"]["ok"] = False
            out["live"]["err"] = str(e)[:160]
        finally:
            try:
                if hasattr(live, "close"):
                    live.close()
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        out["live"]["ok"] = False
        out["live"]["err"] = str(e)[:160]
    return out


def collect(cfg, journal_path: str, log_path: str, no_net: bool,
            pair: str | None = None) -> dict:
    """Gom moi thung tin can thiet cho build_report (de test de dang)."""
    opens, closes = load_journal(journal_path)
    pairs, still = match_pairs(opens, closes)
    st = stats(pairs)
    managed = read_json(getattr(cfg, "managed_state_path", "logs/managed_state.json"))
    ks = read_json(getattr(cfg, "risk_state_path", "logs/risk_state.json"))
    last_close = max((float(c.get("ts") or 0) for c in closes), default=0.0)
    syms = list(getattr(cfg, "symbols", ()) or ()) + \
        list(getattr(cfg, "extra_symbols", ()) or ())
    snap = {
        "now": time.time(),
        "testnet": bool(getattr(cfg, "testnet", True)),
        "dry_run": bool(getattr(cfg, "dry_run", True)),
        "leverage": getattr(cfg, "leverage", "?"),
        "n_symbols": len(syms),
        "journal": {"n": st.get("n"), "wr": st.get("wr"), "pf_r": st.get("pf_r"),
                    "e_r": st.get("e_r"), "pnl": st.get("pnl"),
                    "open_unmatched": len(still), "last_close_ts": last_close},
        "managed": len((managed or {}).get("trades") or {}),
        "kill": {"tripped": bool(ks.get("tripped")), "reason": ks.get("reason") or "",
                 "day": ks.get("day") or ""},
        "kill_hist": dem_kill(log_path),
        "san": {"demo": {}, "live": {}},
    }
    if not no_net and getattr(cfg, "api_key", ""):
        snap["san"] = probe_san(cfg, pair)
    elif not no_net:
        snap["san"] = {"err": "thieu BINANCE_API_KEY trong .env"}
    return snap


def build_report(snap: dict) -> str:
    """Sinh text bao cao (ham THUAN — test duoc, khong goi mang)."""
    lg = snap.get("journal") or {}
    kh = snap.get("kill_hist") or {}
    ks = snap.get("kill") or {}
    san = snap.get("san") or {}
    demo = san.get("demo") or {}
    live = san.get("live") or {}
    L: list = []
    add = L.append

    add("BÁO CÁO BOT | " + _fmt_ts(snap.get("now")))
    add(f"env: BINANCE_TESTNET={snap.get('testnet')} | DRY_RUN={snap.get('dry_run')} "
        f"| LEVERAGE={snap.get('leverage')} | {snap.get('n_symbols')} cap")
    add("")

    # ---- 1) Vi the nam o dau ----
    add("[1] VI THE DANG THAY O DAU — TESTNET hay LIVE?")
    if san.get("err"):
        add("   (bo qua buoc goi san: " + str(san["err"]) + ")")
    if demo.get("api_url"):
        add(f"   - client BOT dung: {demo['api_url']}")
    if demo.get("err"):
        add(f"   - doc demo loi: {demo['err']}")
    poss = demo.get("positions") or []
    if poss:
        for p in poss:
            add(f"   - {p['symbol']} {str(p.get('side')).upper()} qty={p.get('qty')} "
                f"entry={p.get('entry')} mark={p.get('mark')} "
                f"uPnL={_fmt_money(p.get('upnl'))}$ lev={p.get('lev') or '?'}")
    elif demo:
        add("   - khong co vi the nao dang mo (tren tai khoan demo)")
    if demo.get("equity") is not None:
        add(f"   - equity demo: {_fmt_money(demo.get('equity'))} USDT")
    if "orders" in demo:
        add(f"   - lenh treo: {demo['orders']}"
            + (" (khong co SL/TP)" if demo["orders"] == 0 else ""))
        if demo["orders"] == 0 and poss:
            add("     !!! KHONG co SL/TP tren san -> dang bao ve bang MONITOR phan mem "
                "(chi khi bot chay). Kiem tra: python arm_protection.py")
    if live:
        if live.get("ok"):
            add("   !!! NGUY HIEM: key NAY doc duoc ca san LIVE "
                f"(equity that={_fmt_money(live.get('equity'))}) "
                "=> kiem tra tai khoan that ngay!")
        else:
            add(f"   - thu doc LIVE bang chinh key do: BI TU CHOI — {live.get('err')}")
    verdict = None
    if snap.get("testnet") and live and live.get("ok") is False:
        verdict = ("   => KET LUAN: vi the tren la cua tai khoan DEMO/TESTNET "
                   "(tien gia) - KHONG phai tien that.")
    elif live and live.get("ok") is True:
        verdict = ("   => KET LUAN: key co hieu luc tren LIVE - tien THAT. "
                   "Kiem tra `python live_guard.py` truoc khi lam gi tiep.")
    elif snap.get("testnet"):
        verdict = "   => Cau hinh dang la TESTNET (BINANCE_TESTNET=true)."
    if verdict:
        add(verdict)
    add("")

    # ---- 2) Kill-switch ----
    add("[2] KILL-SWITCH")
    if ks.get("tripped"):
        add(f"   - trang thai: DANG TRIPPED (chua reset) | ly do: {ks.get('reason')} "
            f"| ngay ghi: {ks.get('day')}")
    else:
        add("   - trang thai: SACH (khong bi chan)")
    add(f"   - so lan TRIP that trong log: {kh.get('trips', 0)} lan")
    if kh.get("first_trip"):
        add(f"     {str(kh['first_trip'])[:110]}")
    add(f"   - so dong 'dang NGUNG' lap lai: {kh.get('blocked', 0)} "
        "(chi la log moi lan supervisor restart, KHONG phai so lan trip)")
    if ks.get("tripped"):
        add("   - he qua: bot KHONG mo lenh moi cho toi khi reset")
        add("   - muon chay lai: python risk.py --reset  (kiem tra nguyen nhan truoc)")
    add("")

    # ---- 3) So lieu testnet ----
    add("[3] SO LIEU TESTNET (journal)")
    add(f"   - da dong n={lg.get('n')} | WR={lg.get('wr')}% | PF(R)={lg.get('pf_r')} "
        f"| E(R)={lg.get('e_r')} | PnL={_fmt_money(lg.get('pnl'))}$")
    add(f"   - lan dong gan nhat: {_fmt_ts(lg.get('last_close_ts'))} "
        f"| OPEN chua ghep: {lg.get('open_unmatched')} | bot dang quan: {snap.get('managed')} lenh")
    add("")

    # ---- 4) De xuat ----
    add("[4] DE XUAT")
    if ks.get("tripped"):
        add("   - xem lai vi sao hom do lo 2% roi `python risk.py --reset` de tiep tuc thu mau")
    try:
        if float(lg.get("n") or 0) < 50 or float(lg.get("pf_r") or 0) < 1.2:
            add(f"   - con thieu du lieu (n={lg.get('n')}/50, PF={lg.get('pf_r')}/1.2): "
                "chay tiep testnet, CHUA chuyen LIVE")
    except (TypeError, ValueError):
        pass
    add("   - kiem tra cong LIVE: python live_guard.py | chan doan vi the: python positions.py")
    txt = "\n".join(str(x) for x in L).strip()
    return txt[:MAX_LEN]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bao cao bot -> Telegram (read-only)")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--log", default="logs/turbo_err.log")
    ap.add_argument("--pair", default="", help="chi 1 cap (mac dinh: tat ca)")
    ap.add_argument("--dry", action="store_true", help="chi in, khong gui")
    ap.add_argument("--no-net", action="store_true", help="khong goi san")
    args = ap.parse_args(argv)

    from config import Settings
    cfg = Settings()
    snap = collect(cfg, args.journal, args.log, args.no_net, args.pair or None)
    text = build_report(snap)
    print(text)
    print("-" * 60)
    if args.dry:
        print("[dry] khong gui Telegram")
        return 0
    ok = notify.send(cfg.tg_token, cfg.tg_chat, text)
    print("[telegram]", "DA GUI" if ok else "GUI THAT BAI (kiem tra TELEGRAM_BOT_TOKEN/CHAT_ID)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
