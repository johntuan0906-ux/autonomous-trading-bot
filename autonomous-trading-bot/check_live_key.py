"""Kiểm tra cặp KEY LIVE đã điền trong .env (đọc số dư THẬT, chỉ ĐỌC).

    python check_live_key.py            # kiem tra + in so du that + muc rui ro
    python check_live_key.py --retry 5  # so lan thu doc vi (mac dinh 5 — loi -2015 hay ngat quang)
    python check_live_key.py --json     # them dong JSON de may doc

Dung khi: ban vua tao key tren Binance THAT va dan vao .env
    BINANCE_LIVE_API_KEY=...
    BINANCE_LIVE_API_SECRET=...
(2 dong nay KHONG dung den key demo dang chay testnet.)

Khi loi, in MA LOI THAT (vd -2015 key/IP/quyen) + IP ma Binance THAY (co the KHAC
IP api.ipify.org neu mang co nhieu duong ra) de chan doan nhanh.

Ket qua: exit 0 = key OK va du dieu kien tu sang LIVE (>= AUTO_LIVE_MIN_EQUITY),
         exit 2 = chua OK (thieu key / khong doc duoc / so du thap).
"""
from __future__ import annotations

import argparse
import json
import sys
import time


def mask(s: str) -> str:
    s = str(s or "")
    return (s[:6] + "…" + s[-4:]) if len(s) > 12 else ("(rong)" if not s else "***")


def public_ip() -> str:
    """IP công khai của máy (để biết cần whitelist IP nào trên Binance)."""
    try:
        import urllib.request
        return urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode().strip()
    except Exception:  # noqa: BLE001
        return "?"


def ip_diag(cfg, tries: int = 6, sleep_s: float = 0.6) -> dict:
    """Đọc ví vài lần, gom kết quả theo **IP công khai của từng lần**.

    Trả `{"by_ip": {ip: (so_lan_ok, tong_lan)}, "rejected": {ip_binance: so_lan}}`.

    Vì sao: máy có nhiều đường ra Internet (2 WAN/cân bằng tải) ⇒ mỗi request có thể ra
    bằng IP khác nhau. Nếu key bật *"Restrict access to trusted IPs only"* mà whitelist
    thiếu 1 IP thì lỗi `-2015` **ngắt quãng**. `rejected` lấy IP từ chính message `-2015`
    của Binance (IP mà Binance thực sự thấy bị chặn) — chính xác hơn IP do ipify báo,
    vì máy có thể đổi đường ra giữa 2 lần gọi.
    """
    import state_sync as SS
    from exchange import request_ip_from_error
    by_ip: dict = {}
    rejected: dict = {}
    for _ in range(max(1, int(tries))):
        ip = public_ip()
        ok = equity_ok_once(cfg)
        o, n = by_ip.get(ip, (0, 0))
        by_ip[ip] = (o + (1 if ok else 0), n + 1)
        if not ok:
            ipb = request_ip_from_error(SS.last_live_error())
            if ipb:
                rejected[ipb] = rejected.get(ipb, 0) + 1
        if sleep_s:
            time.sleep(float(sleep_s))
    return {"by_ip": by_ip, "rejected": rejected}


def equity_ok_once(cfg) -> bool:
    """Đọc được số dư ví THẬT lần này? (bọc `state_sync.real_equity_usdt` để test được)."""
    import state_sync as SS
    return SS.real_equity_usdt(cfg) is not None


def print_ip_table(table: dict) -> None:
    """In bảng `IP : x/y lần OK` + **IP mà Binance TỪ CHỐI** + cách sửa."""
    by_ip = (table or {}).get("by_ip") or {}
    rejected = (table or {}).get("rejected") or {}
    if not by_ip and not rejected:
        return
    if by_ip:
        print("  Doc theo tung IP ra Internet (IP ipify bao cho tung lan):")
        for ip, (o, n) in sorted(by_ip.items(), key=lambda kv: (-kv[1][0], kv[0])):
            print("    %-16s : %d/%d lan OK" % (ip, o, n))
    if rejected:
        print("  IP ma Binance TU CHOI (doc tu chinh message -2015):")
        for ip, n in sorted(rejected.items()):
            print("    %-16s : %d lan bi chan  <-- KHONG nam trong whitelist cua key" % (ip, n))
        print("    ⇒ Sua: Binance > API Management > key > Edit restrictions >")
        print("      TAT 'Restrict access to trusted IPs only' (chac chan nhat: may co nhieu IP ra),")
        print("      hoac them (cac) IP tren vao whitelist.")
    if by_ip and len(by_ip) > 1 and all(o == 0 for o, _ in by_ip.values()):
        print("    ⚠️ Moi IP deu 0/x: may co the DOI duong ra giua luc goi ipify va luc goi")
        print("      Binance (can bang tai 2 WAN) ⇒ bang chi de tham khao; TAT gioi han IP la chac chan.")


def ip_change_note(cur: str) -> str:
    """Ghi IP hiện tại vào logs/.last_public_ip; cảnh báo nếu IP ĐÃ ĐỔI.

    Vì sao: nếu key có bật 'Restrict access to trusted IPs only' mà IP mạng đổi
    (mạng động / CGNAT / VPN) thì Binance trả -2015 và key "đang đúng" vẫn không đọc được.
    """
    try:
        from pathlib import Path
        p = Path(__file__).resolve().parent / "logs" / ".last_public_ip"
        old = p.read_text(encoding="utf-8").strip() if p.exists() else ""
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cur, encoding="utf-8")
        if old and cur and cur != "?" and old != cur:
            return ("⚠️ IP DA DOI: %s -> %s ⇒ nếu key bat 'Restrict access to trusted IPs' "
                    "thi se loi -2015" % (old, cur))
    except Exception:  # noqa: BLE001
        pass
    return ""


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kiem tra KEY LIVE trong .env")
    ap.add_argument("--json", action="store_true", help="in them JSON")
    ap.add_argument("--retry", type=int, default=5,
                    help="so lan thu doc vi (mac dinh 5: loi -2015 do IP co the NGAT QUANG)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    from config import Settings
    import risk_tier
    import state_sync as SS

    cfg = Settings()
    key, secret, src = SS.key_pair(cfg)
    min_eq = float(getattr(cfg, "auto_live_min_equity", 10.0) or 10.0)
    print("=" * 74)
    print("KIEM TRA KEY LIVE | nguon dang dung = %s" % src)
    print("=" * 74)
    print("  BINANCE_LIVE_API_KEY      : %s" % mask(getattr(cfg, "live_api_key", "")))
    print("  BINANCE_LIVE_API_SECRET   : %s" % mask(getattr(cfg, "live_api_secret", "")))
    print("  BINANCE_API_KEY (demo)    : %s" % mask(getattr(cfg, "api_key", "")))
    if src != "live":
        print("\n-> CHUA dien key LIVE (dang dung key demo/API chung).")
        print("   Dien 2 dong BINANCE_LIVE_API_KEY / BINANCE_LIVE_API_SECRET vao .env")
        print("   (huong dan tao key: README muc 16). Testnet KHONG bi anh huong.")
        return 2

    tries = max(1, int(args.retry))
    health = SS.real_equity_health(cfg, tries=tries)
    eq, ok_n, used, stable = health["eq"], health["ok_n"], health["tries"], health["stable"]
    err = health["err"] or SS.last_live_error()
    tier = risk_tier.tier_for(eq)
    ok_eq = eq is not None and float(eq) >= min_eq
    ip_me = public_ip()
    print("\n  IP cong khai cua may       : %s" % ip_me)
    ip_note = ip_change_note(ip_me)
    if ip_note:
        print("  %s" % ip_note)
    print("  So du USDT THAT           : %s" % ("?" if eq is None else "%.2f" % eq))
    print("  Doc vi on dinh            : %d/%d lan thanh cong (can >=%d) %s"
          % (ok_n, used, health["min_ok"],
             "OK" if stable else "<-- KHONG ON DINH, chua nen sang LIVE"))
    print("  Nguong toi thieu          : %.2f USDT (AUTO_LIVE_MIN_EQUITY)" % min_eq)
    print("  Muc rui ro se ap dung     : %s (%s) — risk %s%% · %s vi the"
          % (tier["name"], tier["label"], tier["risk_pct"], tier["max_positions"]))
    print("  Cap se giao dich          : %s" % (tier["symbols"] + " + " + tier["extra_symbols"]
                                                if tier["feasible_any"] else "(khong co)"))
    ip_table = None
    if not stable:
        # (09/10) Key khong on dinh: do tiep theo TUNG IP ra Internet de biet IP nao bi chan.
        ip_table = ip_diag(cfg, tries=min(6, max(2, tries)), sleep_s=0.6)
        print_ip_table(ip_table)
    if eq is None:
        from exchange import request_ip_from_error
        ip_bin = request_ip_from_error(err)
        print("  Chi tiet loi              : %s" % (err or "(khong co)"))
        if ip_bin:
            print("  IP Binance THAY           : %s" % ip_bin)
            if ip_bin != ip_me:
                print("  ⚠️ KHAC IP ipify (%s) ⇒ mang ra Internet co NHIEU duong/IP." % ip_me)
        if "-2015" in err:
            print("\n-> Loi -2015 (key / IP / quyen). Kiem tra theo thu tu:")
            print("   1) Binance > API Management > key > Edit restrictions:")
            print("      - TAT 'Restrict access to trusted IPs only'  << KHUYEN NGHI voi may nay")
            print("        vi IP ra Internet KHONG on dinh (ipify=%s, Binance thay=%s)." % (ip_me, ip_bin or "?"))
            print("        Neu BAT: bot LIVE se loi API NGAT QUANG -> co the KHONG dat duoc SL!")
            print("      - Bat ca 'Enable Reading' VA 'Enable Futures' (thieu 1 trong 2 cung -2015).")
            print("   2) Vua Regenerate secret? -> dan lai secret MOI vao .env.")
            print("   3) Luu tren Binance roi doi 1-2 phut, chay lai lenh nay.")
        elif not err:
            print("\n-> KHONG doc duoc so du nhung khong co ma loi (mang? ccxt?).")
        else:
            print("\n-> Khong doc duoc so du: xem ma loi o tren (key het hieu luc / mang / quyen).")
        print("   Loi chi tiet cung duoc ghi vao logs/state_sync.log")
    elif not ok_eq:
        print("\n-> So du %.2f < %.2f USDT: nap them USDT vao vi Futures (USDT-M)." % (eq, min_eq))
    elif not stable:
        print("\n-> ⚠️ Doc duoc so du nhung KEY KHONG ON DINH (%d/%d lan)."
              % (ok_n, used))
        print("   Bot VAN CHAY TESTNET (chot 4b chan sang LIVE). Sua:")
        print("   Binance > API Management > key > Edit restrictions > TAT")
        print("   'Restrict access to trusted IPs only' (mang nay nhieu IP ra) roi thu lai.")
    else:
        print("\n-> OK: key LIVE doc duoc ON DINH, so du du dieu kien"
              " => chot 4 + 4b se qua khi cong LIVE dat.")
    if args.json:
        print(json.dumps({"source": src, "equity": eq, "min_equity": min_eq,
                          "tier": tier["name"], "ok": bool(ok_eq and stable),
                          "tries": used, "ok_n": ok_n, "stable": stable,
                          "by_ip": {k: list(v) for k, v in (ip_table or {}).get("by_ip", {}).items()},
                          "rejected": (ip_table or {}).get("rejected", {}),
                          "error": err}, ensure_ascii=False))
    return 0 if (ok_eq and stable) else 2


if __name__ == "__main__":
    raise SystemExit(main())
