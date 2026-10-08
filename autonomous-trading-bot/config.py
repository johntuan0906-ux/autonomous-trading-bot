"""Central configuration — loads from environment (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "y", "on")


_KMO_WARNED = False


def _kill_monitor_only() -> bool:
    """(02/10) KILL_MONITOR_ONLY — BAT BUOC true o DEMO/testnet.

    Vi sao: san demo chan MOI lenh stop (`-4045 Reach max stop order limit`, da kiem chung
    02/10 ngay ca khi so lenh treo = 0) -> khong the co SL tren san, nen monitor mem la
    lop bao ve DUY NHAT. Neu bot thoat han khi kill-switch trip thi vi the con lai tren
    san bi bo quen (dung kieu "vi the mo coi" 01/10). Chi LIVE moi cho phep tat.
    """
    want = _get_bool("KILL_MONITOR_ONLY", True)
    if want or not _get_bool("BINANCE_TESTNET", True):
        return want
    global _KMO_WARNED
    if not _KMO_WARNED:
        _KMO_WARNED = True
        import logging
        logging.getLogger("config").error(
            "KILL_MONITOR_ONLY=false bi BO QUA o DEMO: san demo chan moi lenh stop (-4045) "
            "nen monitor mem la lop bao ve DUY NHAT -> ep bat lai (chi LIVE moi cho phep tat).")
    return True


def _get_tuple(name: str, default: tuple) -> tuple:
    """Parse danh sach symbol cach nhau boi dau phay — dung cho SYMBOLS/EXTRA_SYMBOLS.

    Tra tuple string da strip, loai bo phan tu rong. Neu env khong dat hoac rong
    thi tra default (giup unit test khong can env van chay qua default 4 cap cu).
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    vals = tuple(s.strip() for s in raw.split(",") if s.strip())
    return vals or default


@dataclass(frozen=True)
class Settings:
    # Binance
    api_key: str = field(default_factory=lambda: _get("BINANCE_API_KEY"))
    api_secret: str = field(default_factory=lambda: _get("BINANCE_API_SECRET"))
    testnet: bool = field(default_factory=lambda: _get_bool("BINANCE_TESTNET", True))
    # Phase 5: interlock LIVE — phai bat tay xac nhan moi cho phep chay tien that
    # (xem live_guard.py: con phai dat n>=50, PF>=1.2, risk<=2%, lev<=10, khong tripped).
    live_confirm: bool = field(default_factory=lambda: _get_bool("LIVE_CONFIRM", False))

    # Universe
    symbols: tuple = field(default_factory=lambda: _get_tuple(
        "SYMBOLS", ("BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT")))
    # Cap mo rong khi muon tang toc thu mau testnet (khong bat buoc).
    # Giu DRY vi turbo_demo chi mo them khi con slot trong MAX_POSITIONS.
    extra_symbols: tuple = field(default_factory=lambda: _get_tuple("EXTRA_SYMBOLS", ()))
    timeframe: str = field(default_factory=lambda: _get("TIMEFRAME", "15m"))
    ohlcv_limit: int = field(default_factory=lambda: _get_int("OHLCV_LIMIT", 200))

    # Behaviour
    dry_run: bool = field(default_factory=lambda: _get_bool("DRY_RUN", True))
    poll_interval_sec: int = field(default_factory=lambda: _get_int("POLL_INTERVAL_SEC", 60))
    leverage: int = field(default_factory=lambda: _get_int("LEVERAGE", 5))
    risk_per_trade_pct: float = field(default_factory=lambda: _get_float("RISK_PER_TRADE_PCT", 1.0))
    balance_usdt: float = field(default_factory=lambda: _get_float("BALANCE_USDT", 1000.0))

    # Ranking
    w_tech: float = field(default_factory=lambda: _get_float("W_TECH", 0.65))
    w_sent: float = field(default_factory=lambda: _get_float("W_SENT", 0.35))
    min_alpha_score: float = field(default_factory=lambda: _get_float("MIN_ALPHA_SCORE", 0.35))
    min_edge: float = field(default_factory=lambda: _get_float("MIN_EDGE", 0.10))
    max_positions: int = field(default_factory=lambda: _get_int("MAX_POSITIONS", 1))
    allow_hedge_opposite: bool = field(default_factory=lambda: _get_bool("ALLOW_HEDGE_OPPOSITE", False))

    # Risk / ATR                       (sweep best: SL 2.0, TP 5.0 -> PF 1.242 PASS, E +0.0756R)
    atr_period: int = field(default_factory=lambda: _get_int("ATR_PERIOD", 14))
    sl_atr_mult: float = field(default_factory=lambda: _get_float("SL_ATR_MULT", 2.0))
    tp_atr_mult: float = field(default_factory=lambda: _get_float("TP_ATR_MULT", 5.0))
    max_daily_loss_pct: float = field(default_factory=lambda: _get_float("MAX_DAILY_LOSS_PCT", 2.0))
    max_atr_pct: float = field(default_factory=lambda: _get_float("MAX_ATR_PCT", 0.05))
    max_consecutive_errors: int = field(default_factory=lambda: _get_int("MAX_CONSECUTIVE_ERRORS", 5))
    min_tp_pct: float = field(default_factory=lambda: _get_float("MIN_TP_PCT", 0.0))
    # Notional toi thieu cua san: Binance USDT-M LIVE = 5 USDT; DEMO/testnet doi khi
    # bao -4164 "notional must be no smaller than 20". Mac dinh theo CHE DO dang chay
    # (co the ghi de bang MIN_NOTIONAL_USDT trong .env) — hoi dong 14 model 01/10 da
    # chi ra rang de 20 tren live se lam bot coi vai vi the nho la "bui" va ghi CLOSE
    # trong khi lenh van con tren san.
    min_notional_usdt: float = field(default_factory=lambda: _get_float(
        "MIN_NOTIONAL_USDT", 20.0 if _get_bool("BINANCE_TESTNET", True) else 5.0))

    # Position life-cycle management (muc 12/13 tai lieu): partial / breakeven / trail
    partial_at_r: float = field(default_factory=lambda: _get_float("PARTIAL_AT_R", 0.3))
    partial_pct: float = field(default_factory=lambda: _get_float("PARTIAL_PCT", 0.5))
    be_at_r: float = field(default_factory=lambda: _get_float("BE_AT_R", 1.0))
    trail_atr_mult: float = field(default_factory=lambda: _get_float("TRAIL_ATR_MULT", 1.0))
    cooldown_sec: int = field(default_factory=lambda: _get_int("COOLDOWN_SEC", 0))
    tg_token: str = field(default_factory=lambda: _get("TELEGRAM_BOT_TOKEN"))
    tg_chat: str = field(default_factory=lambda: _get("TELEGRAM_CHAT_ID"))

    # ---- An toan / P0 hardening (xem README muc 6) ----
    # Tran TONG risk dong thoi (% equity). MAX_POSITIONS=4 x risk 1% = 4% la qua cao
    # cho tien that -> mac dinh 3%, khuyen nghi 2% khi moi len live.
    max_total_risk_pct: float = field(default_factory=lambda: _get_float("MAX_TOTAL_RISK_PCT", 3.0))
    adopt_positions: bool = field(default_factory=lambda: _get_bool("ADOPT_POSITIONS", True))
    round_timeout_sec: int = field(default_factory=lambda: _get_int("ROUND_TIMEOUT_SEC", 90))
    socket_timeout_sec: int = field(default_factory=lambda: _get_int("SOCKET_TIMEOUT_SEC", 20))
    risk_state_path: str = field(default_factory=lambda: _get("RISK_STATE_PATH", "logs/risk_state.json"))
    managed_state_path: str = field(
        default_factory=lambda: _get("MANAGED_STATE_PATH", "logs/managed_state.json"))

    # ---- P0-reconcile: doi chieu journal voi fill san, ghi bu CLOSE bi thieu ----
    # Vi sao can: bot tat/restart trong luc mo vi the -> san dong bang SL/TP nhung
    # khong ai ghi CLOSE -> n/WR/PF/LONG-SHORT thieu -> gate LIVE bi lech.
    # Chi ghi log, KHONG sua risk_state, KHONG gui lenh len san.
    # (Duong dan journal KHONG cau hinh qua env: phai trung voi cho bot ghi.)
    reconcile_journal: bool = field(
        default_factory=lambda: _get_bool("RECONCILE_JOURNAL", True))

    # (02/10) Kill-switch dang ngung -> CHI quan ly vi the dang mo (khong mo lenh moi) thay vi
    # thoat han. Ly do: demo chan moi lenh stop (-4045) nen khi bot thoat, vi the con tren san
    # khong co SL tren san VA cung khong co monitor mem = "vi the mo coi" (da xay ra 01/10).
    # Dat KILL_MONITOR_ONLY=false de quay lai hanh vi cu (thoat + supervisor restart).
    kill_monitor_only: bool = field(default_factory=_kill_monitor_only)

    reconcile_days: int = field(default_factory=lambda: _get_int("RECONCILE_DAYS", 7))
    # Tran tan suat goi API (supervisor spawn lai nhieu lan -> khong quet lien tuc).
    reconcile_min_interval_sec: int = field(
        default_factory=lambda: _get_int("RECONCILE_MIN_INTERVAL_SEC", 3600))

    # ---- Strategy gate: chan setup thuoc strategy dang am (khong ha nguong entry) ----
    # Muc dich: loai nhom setup keo PF xuong (vi du A_TREND_PULLBACK avgR -0.59 30/09)
    # ma khong noim loang tieu chuan vao lenh cho cac strategy khac. Gate chi bat khi
    # du mau (STRAT_MIN_N) va avgR am ro (duoi -STRAT_AVG_R). Tat = STRATEGY_GATE=false.
    strategy_gate: bool = field(default_factory=lambda: _get_bool("STRATEGY_GATE", True))
    strat_min_n: int = field(default_factory=lambda: _get_int("STRAT_MIN_N", 10))
    strat_avg_r: float = field(default_factory=lambda: _get_float("STRAT_AVG_R", 0.10))
    # Blocklist chu dong: cac strategy da co bang chung am tu BACKTEST (khong can
    # cho du mau journal). Vi du: A_TREND_PULLBACK am ben 14d (n=162) + 30d (n=394).
    strategy_block: tuple = field(
        default_factory=lambda: _get_tuple("STRATEGY_BLOCK", ()))
    strat_stats_path: str = field(
        default_factory=lambda: _get("STRAT_STATS_PATH", "logs/strategy_stats.json"))

    # ---- Phase 1: tang multi-AI agent (CHI CO VAN, mac dinh TAT) ----
    # Agent khong duoc sua qty/SL/TP/kill-switch; quyet dinh cua agent chi duoc
    # ghi vao journal (event=AGENT) de do luong ("shadow"). Bat lenh thuc thi
    # phai la mot thay doi co chu dich sau khi shadow cho thay co loi.
    agents_enabled: bool = field(default_factory=lambda: _get_bool("AGENTS_ENABLED", False))
    agents_shadow: bool = field(default_factory=lambda: _get_bool("AGENTS_SHADOW", True))
    # stub = offline (khong can key) | openai | anthropic (REST, can key trong .env)
    agent_provider: str = field(default_factory=lambda: _get("AGENT_PROVIDER", "stub"))
    agent_model: str = field(default_factory=lambda: _get("AGENT_MODEL", ""))
    agent_timeout_sec: int = field(default_factory=lambda: _get_int("AGENT_TIMEOUT_SEC", 6))
    agent_cache_sec: int = field(default_factory=lambda: _get_int("AGENT_CACHE_SEC", 900))
    agent_daily_calls: int = field(default_factory=lambda: _get_int("AGENT_DAILY_CALLS", 200))
    agent_daily_budget_usd: float = field(
        default_factory=lambda: _get_float("AGENT_DAILY_BUDGET_USD", 1.0))
    agent_max_errors: int = field(default_factory=lambda: _get_int("AGENT_MAX_ERRORS", 5))
    agent_max_prompt_tokens: int = field(
        default_factory=lambda: _get_int("AGENT_MAX_PROMPT_TOKENS", 1200))
    agent_state_path: str = field(
        default_factory=lambda: _get("AGENT_STATE_PATH", "logs/agent_state.json"))
    # Phase 3: agent phan tich -> de xuat -> gate tat dinh -> file cho nguoi duyet.
    agent_proposals_path: str = field(
        default_factory=lambda: _get("AGENT_PROPOSALS_PATH", "logs/agent_proposals.jsonl"))
    reflect_min_n: int = field(default_factory=lambda: _get_int("REFLECT_MIN_N", 20))

    # ---- Council (hoi dong 2 vong + chu toa) — 01/10, MAC DINH TAT ----
    # Bat: macro -> critic (doc y kien macro) -> arbiter (chu toa) theo quy tac quorum
    # tat dinh trong agents._final_from_council. Van la SHADOW (chi ghi nhan/di Telegram).
    agents_council: bool = field(default_factory=lambda: _get_bool("AGENTS_COUNCIL", False))
    # Hoi dong NHIEU MODEL THAT chay song song (vd claude-sonnet-5.5, gemini-3.8-flash,
    # grok-4.6, kimi-k3...) thay vi 1 model dong 3 vai. Model treo/loi = phieu trang,
    # KHONG co buoc chon 1 model "hop ly nhat". Danh sach: AGENT_COUNCIL_MODELS (csv),
    # trong = dung agents.COUNCIL_MULTI_MODELS (da kiem chung qua CLI 01/10/2026).
    agents_council_multi_model: bool = field(
        default_factory=lambda: _get_bool("AGENTS_COUNCIL_MULTI_MODEL", False))
    agent_council_models: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_MODELS", ""))
    # Model Cline (cline-pass/...) ngoi chung hoi dong voi Copilot CLI: "all" = catalog
    # 14 model (tru CLINE_SKIP_MODELS) | csv | rong = tat. Can CLINE_API_KEY.
    agent_council_cline: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_CLINE", ""))
    # (05/10) Tam nghi 1 bo hoi dong theo ngay (ISO YYYY-MM-DD): bo QuaProvider do den
    # het ngay nay (vd Copilot het quota hang thang -> AGENT_COUNCIL_COPILOT_UNTIL=2026-11-01).
    # Rong = khong chan. Provider con lai tu lam 100% (khong treo, khong ngat viec).
    agent_council_copilot_until: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_COPILOT_UNTIL", ""))
    agent_council_cline_until: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_CLINE_UNTIL", ""))
    # Model Muse (Meta Model API, muse/...) tham gia hoi dong (06/10): csv | rong = tat.
    # Can MUSE_API_KEY tai https://dev.meta.ai. Tam nghi theo ngay: AGENT_COUNCIL_MUSE_UNTIL.
    agent_council_muse: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_MUSE", ""))
    agent_council_muse_until: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_MUSE_UNTIL", ""))
    # Ngan sach LINH HOAT theo do kho: van de de (hau het model dong thuan, it phieu
    # trang) -> dung ngan sach thuong (AGENT_TIMEOUT_SEC/AGENT_DAILY_CALLS/BUDGET o
    # tren), KHONG ton them. Van de kho (hoa phieu HOAC >= AGENT_HARD_ABSTAIN_RATIO
    # model bi treo) -> tu dong thu lai CAC MODEL TREO voi ngan sach "hard" o duoi
    # (bo qua chi phi, uu tien co cau tra loi). Tat bang AGENT_BUDGET_ADAPTIVE=false.
    agent_budget_adaptive: bool = field(
        default_factory=lambda: _get_bool("AGENT_BUDGET_ADAPTIVE", True))
    agent_hard_abstain_ratio: float = field(
        default_factory=lambda: _get_float("AGENT_HARD_ABSTAIN_RATIO", 0.3))
    agent_timeout_sec_hard: float = field(
        default_factory=lambda: _get_float("AGENT_TIMEOUT_SEC_HARD", 240.0))
    agent_daily_calls_hard: int = field(
        default_factory=lambda: _get_int("AGENT_DAILY_CALLS_HARD", 2000))
    agent_daily_budget_usd_hard: float = field(
        default_factory=lambda: _get_float("AGENT_DAILY_BUDGET_USD_HARD", 1000.0))
    # Gui tom tat phien hop hoi dong len Telegram (mac dinh TAT de khong spam).
    agent_tg_votes: bool = field(default_factory=lambda: _get_bool("AGENT_TG_VOTES", False))
    # Hoi dong 2 VONG phan bien (05/10): vong 1 vote mu -> tong hop -> vong 2 moi agent
    # thay y kien cua nhau (peer votes) -> vote lai. Tang chat luong khi hoa phieu/chia re.
    # Dat >=2 de bat; =1 hoac 0 = tat (hanh vi cu: 1 vong duy nhat).
    council_rounds: int = field(default_factory=lambda: _get_int("COUNCIL_ROUNDS", 2))
    # Nguon bang chung de cap quyen veto: "SETUP" (macro/critic) hoac "COUNCIL" (arbiter).
    agent_veto_source: str = field(
        default_factory=lambda: _get("AGENT_VETO_SOURCE", "SETUP").strip().upper() or "SETUP")

    # ---- Phase 4: cap quyen hanh dong CHO AGENT, nhung phai co bang chung shadow ----
    # MAC DINH TAT: chi bat khi agent_authority() chung minh nhom VETO te hon ALLOW
    # (n_veto >= AGENT_VETO_MIN_N va gap >= AGENT_VETO_MIN_GAP). Veto chi duoc PHEP
    # BO QUA 1 lenh (giam rui ro) — khong the tang size/doi SL-TP/dong lenh.
    agents_veto_enabled: bool = field(
        default_factory=lambda: _get_bool("AGENTS_VETO_ENABLED", False))
    agent_veto_min_conf: float = field(
        default_factory=lambda: _get_float("AGENT_VETO_MIN_CONF", 0.7))
    agent_veto_min_n: int = field(default_factory=lambda: _get_int("AGENT_VETO_MIN_N", 10))
    agent_veto_min_gap: float = field(
        default_factory=lambda: _get_float("AGENT_VETO_MIN_GAP", 0.15))
    # Tu dong ap dung de xuat block/unblock (sau gate tat dinh). MAC DINH TAT.
    agent_auto_apply: bool = field(
        default_factory=lambda: _get_bool("AGENT_AUTO_APPLY", False))
    # Phase 2 — duong KHONG can API key (dung subscription Copilot):
    #   AGENT_PROVIDER=copilot_cli  -> shell ra `copilot -p <prompt>` (can cai that)
    #   AGENT_PROVIDER=vscode_lm    -> POST toi bridge extension dang chay
    agent_copilot_bin: str = field(default_factory=lambda: _get("AGENT_COPILOT_BIN", "copilot"))
    # Vi du chan tool: "-p {prompt} --model {model} --deny-tool write --deny-tool shell"
    agent_copilot_args: str = field(
        default_factory=lambda: _get("AGENT_COPILOT_ARGS", "-p {prompt}"))
    agent_vscode_lm_url: str = field(
        default_factory=lambda: _get("AGENT_VSCODE_LM_URL", "http://127.0.0.1:8765/complete"))
    agent_vscode_lm_token: str = field(
        default_factory=lambda: _get("AGENT_VSCODE_LM_TOKEN", ""))
    # (08/10) Provider thu 4: Qwen Code (QwenLM/qwen-code) headless `qwen -p <prompt>`.
    # Tuong tu AGENT_COPILOT_BIN/ARGS; khong can API key (dung cau hinh qwen-code).
    agent_qwen_bin: str = field(default_factory=lambda: _get("AGENT_QWEN_BIN", "qwen"))
    agent_qwen_args: str = field(
        default_factory=lambda: _get("AGENT_QWEN_ARGS", "-p {prompt}"))
    agent_council_qwen: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_QWEN", ""))
    agent_council_qwen_until: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_QWEN_UNTIL", ""))
    # (08/10) Retry loi tam thoi (429/5xx/timeout) truoc khi NO_OPINION (tong so lan goi).
    agent_retry_attempts: int = field(
        default_factory=lambda: _get_int("AGENT_RETRY_ATTEMPTS", 2))
    # Tran chi phi THEO VONG council (USD, 0 = tat - chi tinh chi phi/ngay nhu cu).
    agent_round_budget_usd: float = field(
        default_factory=lambda: _get_float("AGENT_ROUND_BUDGET_USD", 0.0))
    # Provider exhausted lan 1 -> PAUSE so giay nay roi tu mo lai (lan 2 -> block han).
    agent_provider_pause_sec: float = field(
        default_factory=lambda: _get_float("AGENT_PROVIDER_PAUSE_SEC", 1800.0))
    # Fallback chain theo model: 'primary>f1,f2|primary2>g1' (tu dong trong nhom co tien to).
    agent_council_fallbacks: str = field(
        default_factory=lambda: _get("AGENT_COUNCIL_FALLBACKS", ""))


    # Sentiment
    cryptopanic_token: str = field(default_factory=lambda: _get("CRYPTOPANIC_TOKEN"))
    sentiment_cache_sec: int = field(default_factory=lambda: _get_int("SENTIMENT_CACHE_SEC", 300))
    block_long_below: float = field(default_factory=lambda: _get_float("BLOCK_LONG_BELOW", -0.5))
    block_short_above: float = field(default_factory=lambda: _get_float("BLOCK_SHORT_ABOVE", 0.5))
    use_llm_sentiment: bool = field(default_factory=lambda: _get_bool("USE_LLM_SENTIMENT", False))

    def __post_init__(self) -> None:
        total = self.w_tech + self.w_sent
        if total <= 0:
            raise ValueError("W_TECH + W_SENT must be > 0")
        if self.tp_atr_mult / max(self.sl_atr_mult, 1e-9) < 2.0 - 1e-9:
            raise ValueError("TP_ATR_MULT / SL_ATR_MULT must be >= 2.0 (R:R >= 1:2)")
        if self.max_total_risk_pct <= 0:
            raise ValueError("MAX_TOTAL_RISK_PCT must be > 0")
        if self.round_timeout_sec < 10:
            raise ValueError("ROUND_TIMEOUT_SEC must be >= 10 (tranh vong lap bi treo)")
        if not self.symbols:
            raise ValueError("SYMBOLS must be non-empty")
        if len(set(self.extra_symbols) & set(self.symbols)):
            raise ValueError("EXTRA_SYMBOLS must not overlap SYMBOLS")

