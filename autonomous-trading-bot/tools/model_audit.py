"""Kiem tra model truoc khi them vao hoi dong AI (offline, tat dinh).

    python tools/model_audit.py                       # soi cau hinh .env hien tai
    python tools/model_audit.py --target live         # soi .env cua atb-live
    python tools/model_audit.py --hf dealignai/DeepSeek-V4.1-Flash-UNCENSORED-FP8 \
        --params-b 763 --size-gb 510                  # soi 1 repo HF (khong goi mang)

Vi sao co script nay (12/10): hoi dong AI doc du lieu NGOAI (tin tuc RSS, headline)
va co the bi prompt-injection; them mot model "uncensored/abliterated/crack" vao
hoi dong nghia la **bo luon lop tu choi** cua model do ma khong co bang chung nao
ve chat luong. Script nay bien viec "co nen dung model nay?" thanh **checklist
tat dinh**: nguon goc, giong co (red flag), license, kich thuoc/VRAM, co eval hay
khong, va co chay duoc o may nay hay khong.

KHONG goi mang: chi doc ten/model card da biet truoc. Muon so sanh chat luong thi
phai do bang `agents.py --ab-report` (A/B co/khong hoi dong) — khong doan.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
TARGETS = {"testnet": ROOT, "live": LIVE_DIR}

#: Tu khoa trong TEN model = co do (khong phai "chat luong kem" ma la "khong co
#: lop an toan + khong ro nguon goc + khong co eval"). Dung cho ca ten repo HF.
RED_FLAGS = ("uncensored", "abliterated", "dealign", "crack", "jailbreak",
             "nsfw", "unfiltered", "deleted", "leak", "warez")
#: Provider duoc duyet trong du an (xem .env + README muc 10-12).
KNOWN_PROVIDERS = ("cline-pass", "cline", "qwen", "ollama", "local", "copilot",
                   "muse", "gpt", "claude", "gemini", "grok", "kimi")
#: Model nho, chay duoc o may ca nhan (<= 8B) khi luong hoa 4-bit.
LOCAL_OK_PARAMS_B = 8.0


def parse_models(env_text: str) -> list:
    """Lay tat ca model trong cau hinh hoi dong tu noi dung `.env` (thuan tuy)."""
    keys = ("AGENT_COUNCIL_MODELS", "AGENT_COUNCIL_CLINE", "AGENT_COUNCIL_QWEN",
            "AGENT_COUNCIL_MUSE_CLI", "AGENT_COUNCIL_LOCAL", "AGENT_COUNCIL_URGENT",
            "AGENT_COUNCIL_FALLBACKS", "LOCAL_SKIP_MODELS")
    out: list = []
    for ln in env_text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, _, v = ln.partition("=")
        k, v = k.strip(), v.strip()
        if k not in keys or not v:
            continue
        if k == "AGENT_COUNCIL_CLINE" and v.lower() == "all":
            out.append(("AGENT_COUNCIL_CLINE", "all(cline-pass)"))
            continue
        for tok in re.split(r"[,\s]+", v):
            tok = tok.strip()
            if not tok:
                continue
            out.append((k, tok))
    # bo trung (giu thu tu)
    seen: set = set()
    uniq: list = []
    for k, m in out:
        if m not in seen:
            seen.add(m)
            uniq.append((k, m))
    return uniq


def provider_of(model: str) -> str:
    """Doan provider tu tien to `provider/model` (thuan tuy)."""
    m = str(model)
    if "/" in m:
        return m.split("/", 1)[0].lower()
    low = m.lower()
    for p in KNOWN_PROVIDERS:
        if low.startswith(p):
            return p
    if re.match(r"^[a-z0-9.\-]+:\d", low):      # vd llama3.2:3b (ollama)
        return "ollama"
    return "khong ro"


def red_flags(model: str) -> list:
    """Danh sach co do co trong ten model (thuan tuy)."""
    low = str(model).lower()
    return [f for f in RED_FLAGS if f in low]


def vram_needed_gb(params_b: float, bits: float = 16.0, overhead: float = 1.2) -> float:
    """VRAM toi thieu de giu trong so (GB) — MoE phai giu TAT CA trong so.

    `params_b` = tong tham so (ti), `bits` = so bit luong hoa (16/8/4).
    """
    try:
        p = float(params_b)
        b = float(bits)
    except (TypeError, ValueError):
        return 0.0
    if p <= 0 or b <= 0:
        return 0.0
    return round(p * b / 8.0 * float(overhead), 1)


def verdict(model: str, params_b: float = 0.0, bits: float = 16.0,
            vram_gb: float = 8.0, has_eval: bool = False,
            license_ok: bool = True) -> tuple:
    """Ket luan (muc, ly do) cho 1 model — THUAN TUY, test duoc.

    Muc: `OK` | `XEM LAI` | `KHONG NEN DUNG`.
    """
    flags = red_flags(model)
    need = vram_needed_gb(params_b, bits)
    why: list = []
    if flags:
        why.append("co do: %s (khong co lop tu choi + nguon goc khong kiem chung)"
                   % ", ".join(flags))
    if not license_ok:
        why.append("license khong ro/khong tuong thich voi base")
    if need and need > float(vram_gb):
        why.append("can ~%.0f GB VRAM > %.0f GB cua may -> KHONG chay duoc"
                   % (need, float(vram_gb)))
    if not has_eval:
        why.append("khong co bang chung eval (model-index rong)")
    if why:
        hard = bool(flags) or (need and need > float(vram_gb))
        return ("KHONG NEN DUNG" if hard else "XEM LAI", "; ".join(why))
    return ("OK", "nguon goc ro, co eval, chay duoc trong VRAM hien tai")


def audit_env(env_text: str, vram_gb: float = 8.0) -> list:
    """Audit toan bo hoi dong trong `.env` -> [(key, model, muc, ly do)]."""
    rows: list = []
    for key, model in parse_models(env_text):
        prov = provider_of(model)
        if model.startswith("all(") or prov in ("cline-pass", "cline", "qwen",
                                                "copilot", "muse", "gpt", "claude",
                                                "gemini", "grok", "kimi"):
            # model cloud: khong ton VRAM may nay; van kiem tra co do
            lvl, why = verdict(model, vram_gb=vram_gb, has_eval=True)
        else:
            lvl, why = verdict(model, vram_gb=vram_gb, has_eval=False)
        rows.append((key, model, lvl, why))
    return rows


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit model hoi dong / repo HF (offline)")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--vram-gb", type=float, default=8.0,
                    help="VRAM kha dung cua may (mac dinh 8 GB)")
    ap.add_argument("--hf", default="", help="id repo HF can soi (vd dealignai/...)")
    ap.add_argument("--params-b", type=float, default=0.0, help="tong tham so (ti)")
    ap.add_argument("--bits", type=float, default=16.0, help="bit luong hoa (16/8/4)")
    ap.add_argument("--size-gb", type=float, default=0.0, help="kich thuoc file (GB)")
    ap.add_argument("--has-eval", action="store_true", help="repo CO bang chung eval")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    rc = 0
    if args.hf:
        need = vram_needed_gb(args.params_b, args.bits)
        lvl, why = verdict(args.hf, args.params_b, args.bits, args.vram_gb,
                           has_eval=args.has_eval)
        print("=== AUDIT REPO: %s ===" % args.hf)
        print("  provider doan duoc : %s" % provider_of(args.hf))
        print("  co do trong ten    : %s" % (red_flags(args.hf) or "khong"))
        print("  tham so / luong hoa: %.1f B / %.0f bit" % (args.params_b, args.bits))
        print("  VRAM can (uoc)     : %.1f GB (may co %.1f GB)"
              % (need, args.vram_gb))
        if args.size_gb:
            print("  kich thuoc file    : %.1f GB (tai ve cung ton o dia)"
                  % args.size_gb)
        print("  KET LUAN           : %s — %s" % (lvl, why))
        if lvl == "KHONG NEN DUNG":
            rc = 2
    d = TARGETS[args.target]
    try:
        env_text = (d / ".env").read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print("LOI: khong doc duoc .env cua %s (%s)" % (args.target, e))
        return 2
    rows = audit_env(env_text, vram_gb=args.vram_gb)
    print("=== HOI DONG %s: %d muc ===" % (args.target.upper(), len(rows)))
    bad = 0
    for key, model, lvl, why in rows:
        mark = {"OK": "  ", "XEM LAI": "??", "KHONG NEN DUNG": "!!"}[lvl]
        print("%s %-22s %-28s %s" % (mark, key.replace("AGENT_COUNCIL_", ""),
                                     model, "" if lvl == "OK" else why[:110]))
        if lvl == "KHONG NEN DUNG":
            bad += 1
    print("KET LUAN: %s" % ("hoi dong sach" if not bad
                            else "%d muc KHONG NEN DUNG -> xem lai .env" % bad))
    return 2 if bad else rc


if __name__ == "__main__":
    raise SystemExit(main())

