"""In cau hinh THUC TE ma instance trong thu muc hien tai dang dung.

    cd atb-live && python ../autonomous-trading-bot/tools/instance_env.py
    python tools/instance_env.py                 # instance trong repo chinh

Vi sao (15/10): do that mot loi rat kho thay — `config.py` goi `load_dotenv()` luc
IMPORT, va `dotenv` tim `.env` theo **thu muc cua module goi** (khong theo cwd) =>
cong cu chay "cho" LIVE nhung van doc `.env` cua repo chinh (`BINANCE_TESTNET=true`,
key demo) => `-2015 Invalid API-key`. Cong cu nay doi chieu:
  1. `.env` cua thu muc hien tai (nguon THAT),
  2. bien moi truong OS (co the GHI DE `.env` vi `load_dotenv` khong override),
  3. gia tri `Settings()` thuc te ma bot/tool se dung.
Lech nhau o muc nao = chi ra nguyen nhan ngay.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

KEYS = ("BINANCE_TESTNET", "BINANCE_API_KEY", "BINANCE_API_SECRET",
        "BINANCE_LIVE_API_KEY", "AGENT_PROVIDER", "AGENT_MODEL",
        "AGENT_COUNCIL_CLINE", "AGENT_COUNCIL_LOCAL", "AGENT_COUNCIL_QWEN",
        "CLINE_SKIP_MODELS", "LOCAL_SKIP_MODELS", "AGENT_COUNCIL_SINGLE_BELOW",
        "LIVE_CONFIRM", "DRY_RUN")


def _mask(v: str) -> str:
    v = str(v or "")
    return (v[:6] + "..." + v[-4:]) if len(v) > 14 else v


def read_env_file(path: Path) -> dict:
    """Doc `.env` (khong phu thuoc dotenv) -> dict. Dong `#` bi bo qua."""
    out: dict = {}
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip()
    return out


def report(root: Path | None = None) -> dict:
    """So sanh .env (file) vs OS env vs Settings() — ham THUAN TUY ve mat doc."""
    root = Path(root or Path.cwd())
    envf = read_env_file(root / ".env")
    sys.path.insert(0, str(root))
    from config import Settings
    cfg = Settings()
    eff = {"BINANCE_TESTNET": str(getattr(cfg, "testnet", None)),
           "LIVE_CONFIRM": str(getattr(cfg, "live_confirm", None)),
           "DRY_RUN": str(getattr(cfg, "dry_run", None)),
           "AGENT_PROVIDER": str(getattr(cfg, "agent_provider", "")),
           "AGENT_MODEL": str(getattr(cfg, "agent_model", "")),
           "BINANCE_API_KEY": str(getattr(cfg, "api_key", "")),
           "BINANCE_LIVE_API_KEY": str(getattr(cfg, "live_api_key", ""))}
    rows = []
    for k in KEYS:
        f = envf.get(k, "")
        o = os.environ.get(k, "")
        e = eff.get(k, "")
        rows.append({"key": k, "env_file": _mask(f), "os_env": _mask(o),
                     "settings": _mask(e),
                     "overridden_by_os": bool(o) and f and (o != f)})
    return {"root": str(root), "rows": rows,
            "os_override": [r["key"] for r in rows if r["overridden_by_os"]]}


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    rep = report()
    print("=== MOI TRUONG THUC TE CUA INSTANCE | %s ===" % rep["root"])
    print("  %-28s %-24s %-24s %s" % ("BIEN", ".env (file)", "OS env", "Settings()"))
    for r in rep["rows"]:
        flag = "  <-- OS GHI DE .env" if r["overridden_by_os"] else ""
        print("  %-28s %-24s %-24s %s%s"
              % (r["key"], r["env_file"] or "-", r["os_env"] or "-",
                 r["settings"] or "-", flag))
    if rep["os_override"]:
        print("  !! Bien bi OS ghi de: %s (load_dotenv KHONG override) -> sua .env se"
              " KHONG co tac dung" % ", ".join(rep["os_override"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
