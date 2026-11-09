"""Do TUOI du lieu theo tung nguon (freshness/TTL) — lop "Measured Context" con thieu.

Vi sao co (09/11, muc #4 cua REPO_IDEAS §29.3):
- Bot da co `api_ban` (B-044, chan IP) nhung **khong biet du lieu cu bao lau**. Do that:
  nen (ohlcv) fetch moi vong, con OI/funding/thanh ly cache **600 s** (`_CTX_TTL`), tin tuc
  thi khong co moc thoi gian trong payload ⇒ hoi dong nhan "boi canh" ma khong biet phan nao
  da cu, va van quyet dinh nhu nhau.
- Tai lieu "Measured Context" yeu cau: moi nguon co TTL rieng + **hien thi tuoi du lieu**
  trong context gui LLM. Thieu TTL thi 2 tinh huong khac han (nen 20 s vs nen 3 gio) cho ra
  cung mot quyet dinh — dung lop loi "im lang" (khong ai thay du lieu da chet).

Thiet ke:
  * `TTL_SEC`  — nguong TUOI binh thuong theo nguon (giay);
  * `HARD_MULT`— qua `TTL * HARD_MULT` thi coi la du lieu CHET ⇒ khong duoc quyet dinh;
  * `evaluate()` — ham THUAN TUY: nhan dict TUOI (giay) -> phan loai fresh/stale/dead,
    tra ma ly do `DATA_STALE` khi co nguon chet (dung `reason_codes`, khong bia ma moi).

Khong doc file, khong mang ⇒ test duoc offline va dung duoc o ca noi GHI (bot) lan noi DOC.
"""
from __future__ import annotations

import time

#: Tuoi toi da BINH THUONG cua tung nguon (giay). Nguon la -> `DEFAULT_TTL`.
TTL_SEC: dict[str, float] = {
    "candles": 900.0,     # nen: ghi de theo timeframe (xem `ttl_for_timeframe`)
    "deriv": 900.0,       # OI / funding / long-short: boi canh cham, cache 600 s o turbo_demo
    "liq": 900.0,         # thanh ly: nhu tren
    "news": 3600.0,       # tin tuc: cham la binh thuong, qua 1 gio la cu
    "equity": 120.0,      # so du vi: phai tuoi, sai so du = sai size
    "lessons": 86400.0,   # bai hoc tich luy: 1 ngay la binh thuong
}
DEFAULT_TTL = 900.0
#: Qua `TTL * HARD_MULT` ⇒ du lieu CHET (khong duoc dung de quyet dinh).
HARD_MULT = 3.0
#: Nguon BAT BUOC phai tuoi moi duoc quyet dinh. Vi sao khong phai TAT CA: OI/thanh ly/tin
#: tuc la BOI CANH — thieu no thi quyet dinh kem thong tin, con nen (candles) ma chet thi
#: moi con so (score/ATR/SL/TP) deu la cua qua khu ⇒ phai chan.
REQUIRED = ("candles",)
#: Ma ly do khi co nguon chet (da co trong `reason_codes.CODES`).
STALE_CODE = "DATA_STALE"

LEVELS = ("fresh", "stale", "dead")


def ttl_for_timeframe(tf: str, base: float | None = None) -> float:
    """TTL cua nen theo khung thoi gian: `1m`->3 phut, `15m`->45 phut, `1h`->3 gio...

    Vi sao khong dung mot con so: nen 1m cu 10 phut la CHET, con nen 1h cu 10 phut la binh
    thuong — dung mot nguong cho ca hai la doan sai. `base` cho phep ghi de (env).
    """
    if base is not None:
        try:
            b = float(base)
            if b > 0:
                return b
        except (TypeError, ValueError):
            pass
    m = 1.0
    s = str(tf or "").strip().lower()
    try:
        if s.endswith("m"):
            m = float(s[:-1] or 1)
        elif s.endswith("h"):
            m = 60.0 * float(s[:-1] or 1)
        elif s.endswith("d"):
            m = 1440.0 * float(s[:-1] or 1)
        elif s.endswith("w"):
            m = 10080.0 * float(s[:-1] or 1)
    except ValueError:
        m = 1.0
    return max(60.0, 3.0 * m * 60.0)      # 3 nen


def age_sec(ts, now: float | None = None) -> float:
    """Tuoi (giay) cua moc `ts`; thieu/khong hop le -> `float('inf')` (coi nhu CHET).

    Tra `inf` chu khong tra 0: du lieu khong ro moc thoi gian KHONG duoc coi la moi —
    do la khac biet giua "an toan" va "tu lam minh tin".
    """
    try:
        v = float(ts)
    except (TypeError, ValueError):
        return float("inf")
    if v != v or v <= 0:                  # NaN: `v <= 0` la False ⇒ phai kiem rieng,
        return float("inf")               # khong thi max(0, now-nan) = 0 = "moi" (tu lua minh)
    t = float(now if now is not None else time.time())
    return max(0.0, t - v)


def level_of(age: float, ttl: float, hard_mult: float = HARD_MULT) -> str:
    """Phan loai 1 nguon: `fresh` | `stale` | `dead` (ham THUAN TUY)."""
    try:
        a = float(age)
    except (TypeError, ValueError):
        return "dead"
    if a != a or a == float("inf"):        # NaN / inf
        return "dead"
    try:
        t = float(ttl)
    except (TypeError, ValueError):
        t = DEFAULT_TTL
    if a <= t:
        return "fresh"
    if a > t * float(hard_mult or HARD_MULT):
        return "dead"
    return "stale"


def evaluate(ages: dict, ttl: dict | None = None,
             hard_mult: float = HARD_MULT, required=None) -> dict:
    """Phan loai TOAN BO nguon. `ages` = {ten_nguon: TUOI_giay} (ham THUAN TUY).

    Tra:
      ok          — True neu khong nguon BAT BUOC nao chet (`required`, mac dinh `REQUIRED`);
      dead        — nguon CHET (nguon bat buoc chet ⇒ khong duoc quyet dinh);
      blocking    — nguon bat buoc bi chet (danh sach duy nhat lam `ok=False`);
      stale       — nguon cu nhung con dung duoc;
      worst       — nguon co ty le tuoi/TTL lon nhat (de in 1 dong log);
      reason_code — `DATA_STALE` khi co nguon bat buoc chet, nguoc lai '';
      by_source   — {ten: {age, ttl, level}} de hien thi "tuoi du lieu" cho LLM.
    """
    req = tuple(REQUIRED if required is None else required)
    ttls = dict(TTL_SEC)
    ttls.update({str(k): float(v) for k, v in (ttl or {}).items()})
    by: dict = {}
    dead: list = []
    stale: list = []
    blocking: list = []
    worst = ""
    worst_ratio = -1.0
    for name, raw in sorted((ages or {}).items()):
        name = str(name)
        try:
            age = float(raw)
        except (TypeError, ValueError):
            age = float("inf")
        if age != age:                       # NaN
            age = float("inf")
        t = float(ttls.get(name, DEFAULT_TTL))
        lv = level_of(age, t, hard_mult)
        by[name] = {"age": None if age == float("inf") else round(age, 1),
                    "ttl": round(t, 1), "level": lv}
        if lv == "dead":
            dead.append(name)
            if name in req:
                blocking.append(name)
        elif lv == "stale":
            stale.append(name)
        ratio = float("inf") if age == float("inf") else (age / t if t > 0 else float("inf"))
        if ratio > worst_ratio:
            worst_ratio = ratio
            worst = name
    # nguon BAT BUOC khong co mat trong `ages` cung la thieu du lieu ⇒ chan
    for name in req:
        if name not in by:
            by[name] = {"age": None, "ttl": round(float(ttls.get(name, DEFAULT_TTL)), 1),
                        "level": "dead"}
            dead.append(name)
            blocking.append(name)
    return {"ok": not blocking, "dead": dead, "stale": stale, "blocking": blocking,
            "worst": worst,
            "worst_ratio": None if worst_ratio == float("inf") else round(worst_ratio, 2),
            "reason_code": STALE_CODE if blocking else "",
            "by_source": by}


def summary_line(rep: dict) -> str:
    """1 dong de ghi log/Telegram: `candles 20s | deriv 640s | news 3500s`."""
    parts = []
    for name, d in (rep.get("by_source") or {}).items():
        age = d.get("age")
        parts.append("%s %s" % (name, "?" if age is None else "%ss" % int(age)))
    return " | ".join(parts)


def ttl_from_cfg(cfg, timeframe: str | None = None) -> dict:
    """Bang TTL lay tu `cfg` (env) — de nguoi van hanh chinh duoc ma khong sua code.

    `DATA_TTL_SEC` = "candles=900,deriv=1200" (ghi de tung nguon);
    `DATA_TTL_HARD_MULT` = he so "chet"; `DATA_TTL_CANDLES_BASE` ghi de TTL nen (giay).
    """
    out: dict = {}
    raw = str(getattr(cfg, "data_ttl_sec", "") or "")
    for item in raw.replace(";", ",").split(","):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        try:
            out[k.strip()] = float(v)
        except ValueError:
            continue
    if timeframe:
        out.setdefault("candles", ttl_for_timeframe(
            timeframe, getattr(cfg, "data_ttl_candles_base", None)))
    return out


def hard_mult_from_cfg(cfg) -> float:
    """He so "du lieu CHET" tu `cfg.data_ttl_hard_mult` (mac dinh `HARD_MULT`)."""
    try:
        v = float(getattr(cfg, "data_ttl_hard_mult", HARD_MULT) or HARD_MULT)
    except (TypeError, ValueError):
        return HARD_MULT
    return v if v >= 1.0 else HARD_MULT

