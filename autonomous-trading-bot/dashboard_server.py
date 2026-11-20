# -*- coding: utf-8 -*-
"""dashboard_server.py — Read-only local web dashboard cho autonomous-trading-bot.

Chi doc 100% tu file cuc bo (TESTNET tai thu muc repo + LIVE tai ../atb-live/ chi doc).
KHONG goi API Binance, KHONG ghi file nao, bind cung 127.0.0.1.

Chay:
    python dashboard_server.py              # http://127.0.0.1:8780
    python dashboard_server.py --port 8780
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

# =============================================================================
# Configuration block
# =============================================================================
ROOT = Path(__file__).resolve().parent
LIVE_ROOT = ROOT.parent / "atb-live"
STATIC_DIR = ROOT / "dashboard"

DEFAULT_HOST = "127.0.0.1"
ALLOWED_BIND_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_PORT = 8780
SOCKET_TIMEOUT_SEC = 10.0
MAX_CONCURRENT_REQUESTS = 32
MAX_RESPONSE_BYTES = 2_000_000

HEARTBEAT_WATCHDOG_DEFAULT_SEC = 360.0
SNAPSHOT_STALE_SEC = 900.0
JSON_RETRY_DELAY_SEC = 0.02

MAX_TRADES_LIMIT = 200
DEFAULT_TRADES_LIMIT = 50
MAX_OUTBOX_ITEMS = 40
MAX_AGENT_VOTES = 150
MAX_LEDGER_ITEMS = 80
MAX_AUTONOMY_ITEMS = 60
MAX_DOC_CHARS = 120_000
MAX_EQUITY_POINTS = 360
ALLOWED_WINDOWS = frozenset({0, 7, 14, 30, 90})

STATIC_WHITELIST: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}

DOC_WHITELIST: dict[str, tuple[str, str, str]] = {
    "state": ("testnet", "STATE.md", "STATE.md (TESTNET)"),
    "live_state": ("live", "STATE.md", "STATE.md (LIVE)"),
    "operations": ("testnet", "OPERATIONS.md", "OPERATIONS.md"),
    "context": ("testnet", "CONTEXT.md", "CONTEXT.md"),
    "lessons": ("testnet", "LESSONS.md", "LESSONS.md (TESTNET)"),
    "live_lessons": ("live", "LESSONS.md", "LESSONS.md (LIVE)"),
    "security_audit": ("testnet", "SECURITY_AUDIT.md", "SECURITY_AUDIT.md"),
    "council_gaps": ("testnet", "COUNCIL_GAPS.md", "COUNCIL_GAPS.md"),
    "agents": ("testnet", "AGENTS.md", "AGENTS.md"),
}

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    (
        "Content-Security-Policy",
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
        "form-action 'none'; frame-ancestors 'self'",
    ),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Cache-Control", "no-store"),
)

# =============================================================================
# Reuse project deterministic analytics modules (single source of truth)
# =============================================================================
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import monitor_report as MR  # noqa: E402
import perf_report as PR  # noqa: E402


# =============================================================================
# Server-side redaction (defense-in-depth over field whitelisting)
# =============================================================================
_RE_HC_PING = re.compile(r"https?://hc-ping\.com/[A-Za-z0-9_-]+", re.I)
_RE_TG_URL = re.compile(r"/bot[0-9]{5,15}:[A-Za-z0-9_-]{16,}")
_RE_TG_RAW = re.compile(r"\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}\b")
_RE_URL_USERINFO = re.compile(r"(https?://)[^/\s@]+@", re.I)
_RE_SECRET_KV = re.compile(
    r"(?i)\b(api[_-]?key|api[_-]?secret|binance[_a-z]*secret|binance[_a-z]*key|"
    r"telegram[_a-z]*token|authorization|bearer|secret|password|passwd|private[_-]?key|"
    r"access[_-]?token|refresh[_-]?token)\s*([:=])\s*['\"]?([^\s,'\"&}\]]{4,})['\"]?"
)
_RE_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{12,}")
_RE_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_RE_LONG_HEX = re.compile(r"\b[0-9a-fA-F]{48,}\b")
_RE_LONG_B64 = re.compile(r"\b(?=[A-Za-z0-9+/_-]{48,}\b)(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z0-9+/_-]{48,}={0,2}\b")
_SAFE_IPS = frozenset({"127.0.0.1", "0.0.0.0"})


def _mask_ip(match: re.Match[str]) -> str:
    ip = match.group(0)
    return ip if ip in _SAFE_IPS else "<ip_redacted>"


def redact_text(value: str) -> str:
    """Redact ping UUIDs, Telegram tokens, secrets, userinfo URLs, IPs, long tokens."""
    s = str(value)
    s = _RE_HC_PING.sub("https://hc-ping.com/<redacted>", s)
    s = _RE_TG_URL.sub("/bot<token_redacted>", s)
    s = _RE_TG_RAW.sub("<token_redacted>", s)
    s = _RE_URL_USERINFO.sub(r"\1<userinfo_redacted>@", s)
    s = _RE_BEARER.sub("Bearer <token_redacted>", s)
    s = _RE_SECRET_KV.sub(r"\1\2<redacted>", s)
    s = _RE_IPV4.sub(_mask_ip, s)
    s = _RE_LONG_HEX.sub("<hex_redacted>", s)
    s = _RE_LONG_B64.sub("<token_redacted>", s)
    return s


def redact_obj(obj: Any) -> Any:
    """Recursively redact every string leaf and sanitize non-finite floats."""
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {redact_text(str(k)): redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_obj(v) for v in obj]
    return redact_text(str(obj))


def _safe_float(v: Any, default: float | None = None) -> float | None:
    if v is None or isinstance(v, bool):
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return default if (math.isnan(f) or math.isinf(f)) else f


def _safe_int(v: Any, default: int | None = None) -> int | None:
    if v is None or isinstance(v, bool):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _fmt_ts(ts: float | None) -> str | None:
    if not ts or ts <= 0:
        return None
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    except (OSError, ValueError, OverflowError):
        return None


# =============================================================================
# Path safety checks (static assets only)
# =============================================================================
_FORBIDDEN_TOKENS = (".env", "id_rsa", "id_ed25519", ".git", ".npmrc", ".netrc", "key", "token", "secret")
_WIN_DEVICES = frozenset({
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})


def is_suspicious_path(raw_path: str) -> bool:
    """Detect traversal, encoded traversal, null bytes, Windows ADS, device names, secrets."""
    if "\x00" in raw_path or "\\" in raw_path:
        return True
    decoded = unquote(raw_path)
    if "\x00" in decoded or "\\" in decoded or ":" in decoded:
        return True
    lower = decoded.lower()
    if ".." in lower or "%2e" in raw_path.lower():
        return True
    segments = [seg for seg in lower.split("/") if seg]
    for seg in segments:
        stem = seg.split(".")[0]
        if stem in _WIN_DEVICES:
            return True
        if seg.startswith(".env") or seg in {"logs", "__pycache__", ".git", ".venv", "venv"}:
            return True
        for tok in (".env", "id_rsa", "id_ed25519", ".npmrc", ".netrc"):
            if tok in seg:
                return True
    return False


def resolve_static_file(static_dir: Path, url_path: str) -> tuple[Path, str] | None:
    """Resolve ONLY whitelisted static assets inside static_dir; reject symlinks & escapes."""
    if is_suspicious_path(url_path):
        return None
    entry = STATIC_WHITELIST.get(url_path)
    if entry is None:
        return None
    filename, content_type = entry
    base = static_dir.resolve()
    candidate = base / filename
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return None
        resolved = candidate.resolve()
        if not resolved.is_relative_to(base):
            return None
    except OSError:
        return None
    return resolved, content_type


# =============================================================================
# Thread-safe incremental caches (Read-Only DataStore)
# =============================================================================
class _JsonCacheEntry:
    __slots__ = ("mtime_ns", "size", "data")

    def __init__(self, mtime_ns: int, size: int, data: Any) -> None:
        self.mtime_ns = mtime_ns
        self.size = size
        self.data = data


class _JournalState:
    """Incremental reader for journal.jsonl with rotation detection & memoized analytics."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.offset = 0
        self.mtime_ns = 0
        self.size = 0
        self.opens: list[dict[str, Any]] = []
        self.closes: list[dict[str, Any]] = []
        self.agent_votes: collections.deque[dict[str, Any]] = collections.deque(maxlen=MAX_AGENT_VOTES)
        self.paired_version = -1
        self.version = 0
        self.paired: list[tuple[dict[str, Any] | None, dict[str, Any]]] = []
        self.still_open_count = 0
        self.perf_memo: dict[tuple[int, int, bool, float], dict[str, Any]] = {}

    def _reset(self) -> None:
        self.offset = 0
        self.mtime_ns = 0
        self.size = 0
        self.opens.clear()
        self.closes.clear()
        self.agent_votes.clear()
        self.paired = []
        self.still_open_count = 0
        self.perf_memo.clear()
        self.version += 1

    def _ingest_line(self, raw_line: bytes) -> None:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("{"):
            return
        try:
            rec = json.loads(line)
        except ValueError:
            return
        if not isinstance(rec, dict):
            return
        ev = str(rec.get("event") or "")
        if ev == "CLOSE" or ("won" in rec and ev != "OPEN"):
            self.closes.append(rec)
        elif ev == "OPEN" or ("entry" in rec and ev != "AGENT"):
            self.opens.append(rec)
        elif ev == "AGENT" or ("action" in rec and "agent" in rec):
            self.agent_votes.append({
                "ts": _safe_float(rec.get("ts")),
                "role": str(rec.get("role") or ""),
                "agent": str(rec.get("agent") or ""),
                "provider": str(rec.get("provider") or ""),
                "model": str(rec.get("model") or ""),
                "action": str(rec.get("action") or ""),
                "confidence": _safe_float(rec.get("confidence")),
                "symbol": str(rec.get("symbol") or rec.get("pair") or ""),
                "direction": str(rec.get("direction") or ""),
                "status": str(rec.get("status") or ""),
                "shadow": bool(rec.get("shadow", True)),
                "latency_ms": _safe_float(rec.get("latency_ms")),
                "cost_usd": _safe_float(rec.get("cost_usd")),
                "note": str(rec.get("note") or "")[:240],
                "reasons": [str(x)[:280] for x in (rec.get("reasons") or [])[:4]],
                "risk_flags": [str(x)[:120] for x in (rec.get("risk_flags") or [])[:4]],
            })

    def sync(self) -> tuple[bool, float | None]:
        """Synchronize cache with file on disk. Returns (exists, mtime_sec)."""
        with self.lock:
            try:
                st = self.path.stat()
            except OSError:
                if self.size > 0 or self.opens or self.closes:
                    self._reset()
                return False, None

            mtime_sec = st.st_mtime_ns / 1_000_000_000.0
            if st.st_mtime_ns == self.mtime_ns and st.st_size == self.size:
                return True, mtime_sec

            if st.st_size < self.offset or st.st_mtime_ns < self.mtime_ns:
                self._reset()

            try:
                with self.path.open("rb") as fh:
                    fh.seek(self.offset)
                    chunk = fh.read()
            except OSError:
                return True, mtime_sec

            if chunk:
                last_nl = chunk.rfind(b"\n")
                if last_nl >= 0:
                    complete = chunk[: last_nl + 1]
                    for raw_line in complete.splitlines():
                        self._ingest_line(raw_line)
                    self.offset += last_nl + 1
                    self.version += 1
                    self.perf_memo.clear()
                else:
                    # Single complete JSON line without trailing newline when file is stable
                    stripped = chunk.strip()
                    if stripped.startswith(b"{") and stripped.endswith(b"}"):
                        try:
                            json.loads(stripped.decode("utf-8", errors="replace"))
                        except ValueError:
                            pass
                        else:
                            self._ingest_line(stripped)
                            self.offset += len(chunk)
                            self.version += 1
                            self.perf_memo.clear()

            self.mtime_ns = st.st_mtime_ns
            self.size = st.st_size
            return True, mtime_sec

    def get_paired(self) -> tuple[list[tuple[dict[str, Any] | None, dict[str, Any]]], int, int]:
        with self.lock:
            if self.paired_version != self.version:
                pairs, still = MR.match_pairs(self.opens, self.closes)
                pairs.sort(key=lambda pair: float((pair[1] or {}).get("ts") or 0.0))
                self.paired = pairs
                self.still_open_count = len(still)
                self.paired_version = self.version
            return self.paired, self.still_open_count, self.version

    def get_agent_votes(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(reversed(self.agent_votes))


class DataStore:
    """Read-only aggregator over TESTNET and LIVE local directories."""

    def __init__(self, testnet_root: Path = ROOT, live_root: Path = LIVE_ROOT) -> None:
        self.roots: dict[str, Path] = {
            "testnet": Path(testnet_root).resolve(),
            "live": Path(live_root).resolve(),
        }
        self._json_locks: dict[Path, threading.Lock] = {}
        self._json_locks_guard = threading.Lock()
        self._json_cache: dict[Path, _JsonCacheEntry] = {}
        self._journals: dict[str, _JournalState] = {
            name: _JournalState(root / "logs" / "journal.jsonl")
            for name, root in self.roots.items()
        }

    def _lock_for(self, path: Path) -> threading.Lock:
        with self._json_locks_guard:
            lock = self._json_locks.get(path)
            if lock is None:
                lock = threading.Lock()
                self._json_locks[path] = lock
            return lock

    def _read_json(self, path: Path) -> tuple[Any, float | None, bool, bool]:
        """Read JSON file with mtime/size cache and mid-write retry.

        Returns: (data, mtime_sec, exists, stale_fallback)
        """
        lock = self._lock_for(path)
        with lock:
            try:
                st = path.stat()
            except OSError:
                return None, None, False, False

            mtime_sec = st.st_mtime_ns / 1_000_000_000.0
            cached = self._json_cache.get(path)
            if cached is not None and cached.mtime_ns == st.st_mtime_ns and cached.size == st.st_size:
                return cached.data, mtime_sec, True, False

            for attempt in range(2):
                try:
                    raw = path.read_text(encoding="utf-8", errors="replace")
                    data = json.loads(raw)
                    self._json_cache[path] = _JsonCacheEntry(st.st_mtime_ns, st.st_size, data)
                    return data, mtime_sec, True, False
                except (OSError, ValueError):
                    if attempt == 0:
                        time.sleep(JSON_RETRY_DELAY_SEC)
            if cached is not None:
                return cached.data, cached.mtime_ns / 1_000_000_000.0, True, True
            return None, mtime_sec, True, True

    def _read_jsonl_tail(self, path: Path, limit: int) -> tuple[list[dict[str, Any]], float | None, bool]:
        lock = self._lock_for(path)
        with lock:
            try:
                st = path.stat()
            except OSError:
                return [], None, False
            mtime_sec = st.st_mtime_ns / 1_000_000_000.0
            cached = self._json_cache.get(path)
            if cached is not None and cached.mtime_ns == st.st_mtime_ns and cached.size == st.st_size:
                return list(cached.data[-limit:]), mtime_sec, True
            rows: list[dict[str, Any]] = []
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                if cached is not None:
                    return list(cached.data[-limit:]), mtime_sec, True
                return [], mtime_sec, True
            for ln in text.splitlines():
                ln = ln.strip()
                if not ln.startswith("{"):
                    continue
                try:
                    rec = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(rec, dict):
                    rows.append(rec)
            self._json_cache[path] = _JsonCacheEntry(st.st_mtime_ns, st.st_size, rows)
            return list(rows[-limit:]), mtime_sec, True

    def _instance_root(self, instance: str) -> Path:
        inst = instance.lower()
        if inst not in self.roots:
            raise ValueError(f"Unsupported instance: {instance}")
        return self.roots[inst]

    # -------------------------------------------------------------------------
    # Instance overview (whitelist fields, honest STALE/UNKNOWN states)
    # -------------------------------------------------------------------------
    def build_instance_overview(self, instance: str, now: float | None = None) -> dict[str, Any]:
        now = float(now if now is not None else time.time())
        root = self._instance_root(instance)
        logs = root / "logs"

        hb_raw, hb_mt, hb_ok, hb_stale = self._read_json(logs / "heartbeat.json")
        snap_raw, snap_mt, snap_ok, snap_stale = self._read_json(logs / "state_snapshot.json")
        risk_raw, risk_mt, risk_ok, risk_stale = self._read_json(logs / "risk_state.json")
        managed_raw, man_mt, man_ok, man_stale = self._read_json(logs / "managed_state.json")
        orders_raw, ord_mt, ord_ok, ord_stale = self._read_json(logs / "orders_snapshot.json")
        ban_raw, ban_mt, ban_ok, _ = self._read_json(logs / "api_ban.json")
        pause_raw, _, pause_ok, _ = self._read_json(logs / "entries_pause.json")
        ops_q_raw, _, _, _ = self._read_json(logs / "ops_questions.json")
        agent_raw, _, agent_ok, _ = self._read_json(logs / "agent_state.json")
        chb_raw, _, chb_ok, _ = self._read_json(logs / "council_heartbeat.json")

        hb = hb_raw if isinstance(hb_raw, dict) else {}
        snap = snap_raw if isinstance(snap_raw, dict) else {}
        risk = risk_raw if isinstance(risk_raw, dict) else {}
        managed = managed_raw if isinstance(managed_raw, dict) else {}
        orders = orders_raw if isinstance(orders_raw, dict) else {}
        ban = ban_raw if isinstance(ban_raw, dict) else {}
        pause = pause_raw if isinstance(pause_raw, dict) else {}
        agent = agent_raw if isinstance(agent_raw, dict) else {}
        chb = chb_raw if isinstance(chb_raw, dict) else {}

        # Heartbeat status (never claim RUNNING if missing or expired)
        snap_bot = snap.get("bot") if isinstance(snap.get("bot"), dict) else {}
        watchdog_sec = _safe_float(snap_bot.get("watchdog_sec"), HEARTBEAT_WATCHDOG_DEFAULT_SEC) or HEARTBEAT_WATCHDOG_DEFAULT_SEC
        hb_ts = _safe_float(hb.get("ts"))
        hb_age = round(max(0.0, now - hb_ts), 1) if hb_ts else None
        if not hb_ok or hb_ts is None:
            bot_status = "UNKNOWN"
        elif hb_stale or hb_age is None or hb_age > watchdog_sec:
            bot_status = "STALE"
        else:
            bot_status = "ALIVE"

        # Equity & daily loss vs cap
        equity = _safe_float(hb.get("equity"))
        if equity is None:
            equity = _safe_float(snap.get("equity_demo"))
        start_equity = _safe_float(risk.get("start_equity"))
        peak_balance = _safe_float(risk.get("peak_balance"))
        max_daily_loss_pct = _safe_float(risk.get("max_daily_loss_pct"))
        daily_pnl_usdt: float | None = None
        daily_pnl_pct: float | None = None
        if equity is not None and start_equity and start_equity > 0:
            daily_pnl_usdt = round(equity - start_equity, 4)
            daily_pnl_pct = round((equity - start_equity) / start_equity * 100.0, 2)

        # Kill-switch
        if not risk_ok or not risk:
            ks_status = "UNKNOWN"
            ks_tripped = None
        else:
            ks_tripped = bool(risk.get("tripped"))
            ks_status = "TRIPPED" if ks_tripped else "OK"

        # API ban status
        ban_until = _safe_float(ban.get("until")) if ban_ok else None
        ban_remaining_s = round(ban_until - now, 1) if (ban_until and ban_until > now) else 0.0
        api_ban_active = bool(ban_until and ban_until > now)

        # Positions & protection count
        trades_dict = managed.get("trades") if isinstance(managed.get("trades"), dict) else {}
        open_positions_count = len(trades_dict) if man_ok else None
        snap_cfg = snap.get("config") if isinstance(snap.get("config"), dict) else {}
        max_positions = _safe_int(snap_cfg.get("max_positions"))

        if ord_ok and orders:
            protect_orders = _safe_int(orders.get("protect_orders"))
            naked_list = list(orders.get("naked") or [])
            orphan_count = _safe_int(orders.get("orphans"), 0)
            dupes_dict = orders.get("dupes") if isinstance(orders.get("dupes"), dict) else {}
            dust_list = list(orders.get("dust") or [])
            exchange_pos_count = _safe_int(orders.get("positions"))
            expected_protect = (
                max(0, (exchange_pos_count - len(dust_list)) * 2)
                if exchange_pos_count is not None
                else (open_positions_count * 2 if open_positions_count is not None else None)
            )
            prot_status = (
                "ALERT"
                if (naked_list or dupes_dict or (orphan_count and orphan_count > 0))
                else ("STALE" if (ord_mt and now - ord_mt > 3600) else "OK")
            )
        else:
            protect_orders = None
            naked_list = []
            orphan_count = None
            dupes_dict = {}
            dust_list = []
            expected_protect = None
            prot_status = "UNKNOWN"

        # Pending ops questions
        pending_ops = 0
        if isinstance(ops_q_raw, list):
            pending_ops = sum(
                1 for q in ops_q_raw
                if isinstance(q, dict) and str(q.get("status") or "OPEN").upper() not in {"ANSWERED", "CLOSED", "DONE"}
            )

        # Snapshot windows / live_ready / live_guard
        live_ready_raw = snap.get("live_ready") if isinstance(snap.get("live_ready"), dict) else {}
        live_guard_raw = snap.get("live_guard") if isinstance(snap.get("live_guard"), dict) else {}
        tier_raw = snap.get("tier") if isinstance(snap.get("tier"), dict) else {}
        snap_journal = snap.get("journal") if isinstance(snap.get("journal"), dict) else {}
        snap_windows = snap.get("windows") if isinstance(snap.get("windows"), dict) else {}

        mtimes = [m for m in (hb_mt, snap_mt, risk_mt, man_mt, ord_mt) if m is not None]
        as_of = max(mtimes) if mtimes else None
        is_stale = bool(
            hb_stale or snap_stale or risk_stale or man_stale or ord_stale
            or bot_status != "ALIVE"
            or (as_of is None)
            or (now - as_of > SNAPSHOT_STALE_SEC)
        )

        # Alerts synthesis (critical operator signals)
        alerts: list[dict[str, str]] = []
        if ks_status == "TRIPPED":
            alerts.append({"level": "danger", "code": "KILL_SWITCH", "msg": f"Kill-switch TRIPPED: {risk.get('reason') or 'khong ro ly do'}"})
        if bot_status != "ALIVE":
            alerts.append({"level": "danger" if bot_status == "STALE" else "warn", "code": "HEARTBEAT", "msg": f"Bot heartbeat {bot_status} (tuoi: {hb_age}s / nguong {watchdog_sec}s)"})
        if api_ban_active:
            alerts.append({"level": "danger", "code": "API_BAN", "msg": f"San dang chan IP (-1003): con {round(ban_remaining_s / 60.0, 1)} phut (den {ban.get('readable') or ''})"})
        if naked_list:
            alerts.append({"level": "danger", "code": "NAKED_POS", "msg": f"{len(naked_list)} vi the KHONG CO SL/TP: {', '.join(str(x) for x in naked_list)}"})
        if dupes_dict:
            alerts.append({"level": "warn", "code": "DUPE_ORDERS", "msg": f"Co lenh bao ve trung: {', '.join(str(k) for k in dupes_dict.keys())}"})
        if orphan_count and orphan_count > 0:
            alerts.append({"level": "warn", "code": "ORPHAN_ORDERS", "msg": f"Co {orphan_count} lenh mo coi tren san"})
        if pause_ok and pause.get("paused"):
            alerts.append({"level": "warn", "code": "ENTRIES_PAUSED", "msg": f"Tam dung mo lenh moi: {pause.get('reason') or ''}"})
        if agent_ok and agent.get("disabled"):
            alerts.append({"level": "warn", "code": "AGENT_DISABLED", "msg": f"Agent provider bi tat: {agent.get('disabled')}"})
        if pending_ops > 0:
            alerts.append({"level": "info", "code": "OPS_PENDING", "msg": f"{pending_ops} cau hoi van hanh dang cho duyet"})

        return {
            "instance": instance,
            "exists": root.is_dir(),
            "as_of": as_of,
            "as_of_human": _fmt_ts(as_of),
            "stale": is_stale,
            "git_head": str(snap.get("git_head") or ""),
            "bot": {
                "status": bot_status,
                "pid": _safe_int(hb.get("pid") or snap_bot.get("pid")),
                "round": _safe_int(hb.get("round") or snap_bot.get("round")),
                "phase": str(hb.get("phase") or snap_bot.get("phase") or "UNKNOWN"),
                "heartbeat_ts": hb_ts,
                "heartbeat_age_s": hb_age,
                "watchdog_sec": watchdog_sec,
            },
            "equity": {
                "current": equity,
                "start_day": start_equity,
                "peak": peak_balance,
                "daily_pnl_usdt": daily_pnl_usdt,
                "daily_pnl_pct": daily_pnl_pct,
                "max_daily_loss_pct": max_daily_loss_pct,
                "day": str(risk.get("day") or ""),
                "mode": str(risk.get("mode") or ("live" if instance == "live" else "demo")),
            },
            "kill_switch": {
                "status": ks_status,
                "tripped": ks_tripped,
                "reason": str(risk.get("reason") or ""),
                "errors": _safe_int(risk.get("errors")),
                "max_errors": _safe_int(risk.get("max_errors")),
                "consec_losses": _safe_int(risk.get("consec_losses")),
                "max_consec_losses": _safe_int(risk.get("max_consec_losses")),
            },
            "api_ban": {
                "active": api_ban_active,
                "until": ban_until,
                "readable": str(ban.get("readable") or ""),
                "reason": str(ban.get("reason") or ""),
                "remaining_s": ban_remaining_s,
                "recorded_at": ban_mt,
            },
            "entries_pause": {
                "known": pause_ok,
                "paused": bool(pause.get("paused")) if pause_ok else None,
                "reason": str(pause.get("reason") or ""),
                "since": _safe_float(pause.get("since")),
            },
            "positions": {
                "open": open_positions_count,
                "max": max_positions,
                "exchange_total": _safe_int(orders.get("positions")) if ord_ok else None,
                "dust_count": len(dust_list) if ord_ok else None,
            },
            "protection": {
                "status": prot_status,
                "protect_orders": protect_orders,
                "expected_orders": expected_protect,
                "naked": naked_list,
                "orphans": orphan_count,
                "dupes_count": len(dupes_dict),
                "as_of": ord_mt,
                "as_of_human": _fmt_ts(ord_mt),
            },
            "config": {
                "testnet": snap_cfg.get("testnet"),
                "dry_run": snap_cfg.get("dry_run"),
                "live_confirm": snap_cfg.get("live_confirm"),
                "risk_pct": _safe_float(snap_cfg.get("risk_pct")),
                "max_total_risk_pct": _safe_float(snap_cfg.get("max_total_risk_pct")),
                "leverage": _safe_int(snap_cfg.get("leverage")),
                "max_positions": max_positions,
                "tier_label": str(tier_raw.get("label") or ""),
                "tier_note": str(tier_raw.get("note") or ""),
            },
            "gates": {
                "live_ready_ok": live_ready_raw.get("ok") if snap_ok else None,
                "live_ready_verdict": str(live_ready_raw.get("verdict") or "UNKNOWN"),
                "live_ready_blockers": list(live_ready_raw.get("blockers") or []),
                "live_guard_ok": live_guard_raw.get("ok") if snap_ok else None,
                "live_guard_blockers": list(live_guard_raw.get("blockers") or []),
            },
            "snapshot_stats": {
                "all": {
                    "n": _safe_int(snap_journal.get("n")),
                    "wr": _safe_float(snap_journal.get("wr")),
                    "pf_r": _safe_float(snap_journal.get("pf_r")),
                    "pf_pnl": _safe_float(snap_journal.get("pf_pnl")),
                    "e_r": _safe_float(snap_journal.get("e_r")),
                    "pnl": _safe_float(snap_journal.get("pnl")),
                },
                "windows": {
                    str(k): {
                        "n": _safe_int(v.get("n")),
                        "wr": _safe_float(v.get("wr")),
                        "pf_r": _safe_float(v.get("pf_r")),
                        "pf_pnl": _safe_float(v.get("pf_pnl")),
                        "e_r": _safe_float(v.get("e_r")),
                        "pnl": _safe_float(v.get("pnl")),
                    }
                    for k, v in snap_windows.items()
                    if isinstance(v, dict)
                },
            },
            "council_summary": {
                "ok": chb.get("ok") if chb_ok else None,
                "mode": str(chb.get("mode") or "UNKNOWN"),
                "spend_today": _safe_float(chb.get("spend_today")),
                "cycles_today": _safe_int(chb.get("cycles_today")),
                "models": list((snap.get("council") or {}).get("models") or chb.get("models") or []),
                "agent_calls_today": _safe_int(agent.get("calls")),
                "agent_cost_today": _safe_float(agent.get("cost_usd")),
                "agent_disabled": str(agent.get("disabled") or ""),
            },
            "pending_ops": pending_ops,
            "alerts": alerts,
        }

    def get_deadman_summary(self) -> dict[str, Any]:
        """Whitelist-only view of deadman.json (NEVER exposes hc-ping URLs)."""
        raw, mt, ok, stale = self._read_json(self.roots["testnet"] / "logs" / "deadman.json")
        if not ok or not isinstance(raw, dict):
            return {"known": False, "ok": None, "reason": "UNKNOWN", "as_of": None, "stale": True, "instances": [], "pings": []}
        instances = []
        for it in raw.get("instances") or []:
            if not isinstance(it, dict):
                continue
            instances.append({
                "name": str(it.get("name") or ""),
                "round": _safe_int(it.get("round")),
                "hb_age_s": _safe_float(it.get("hb_age_s")),
                "supervisor_pid": _safe_int(it.get("supervisor_pid")),
                "kill_tripped": bool(it.get("kill_tripped")),
                "errors_win": dict(it.get("errors_win") or {}),
            })
        pings = []
        for p in raw.get("pings") or []:
            if not isinstance(p, dict):
                continue
            # Deliberately drop `url` so Healthchecks UUIDs can NEVER leak
            pings.append({
                "instance": str(p.get("instance") or ""),
                "ok": bool(p.get("ok")),
                "status": _safe_int(p.get("status")),
            })
        ts = _safe_float(raw.get("ts"))
        return {
            "known": True,
            "ok": bool(raw.get("ok")),
            "reason": str(raw.get("reason") or ""),
            "muted": bool(raw.get("muted")),
            "ts": ts,
            "ts_human": _fmt_ts(ts),
            "as_of": mt,
            "stale": stale,
            "instances": instances,
            "pings": pings,
        }

    def get_overview(self, target: str) -> dict[str, Any]:
        now = time.time()
        deadman = self.get_deadman_summary()
        if target == "both":
            t_data = self.build_instance_overview("testnet", now=now)
            l_data = self.build_instance_overview("live", now=now)
            return {
                "target": "both",
                "read_only": True,
                "server_ts": now,
                "server_ts_human": _fmt_ts(now),
                "testnet": t_data,
                "live": l_data,
                "deadman": deadman,
            }
        inst_data = self.build_instance_overview(target, now=now)
        return {
            "target": target,
            "read_only": True,
            "server_ts": now,
            "server_ts_human": _fmt_ts(now),
            "data": inst_data,
            "deadman": deadman,
        }

    # -------------------------------------------------------------------------
    # Positions & Protection tab
    # -------------------------------------------------------------------------
    def get_positions(self, instance: str) -> dict[str, Any]:
        root = self._instance_root(instance)
        logs = root / "logs"

        managed_raw, man_mt, man_ok, man_stale = self._read_json(logs / "managed_state.json")
        orders_raw, ord_mt, ord_ok, ord_stale = self._read_json(logs / "orders_snapshot.json")
        dust_raw, dust_mt, dust_ok, _ = self._read_json(logs / "dust_skip.json")
        banned_raw, ban_mt, ban_ok, _ = self._read_json(logs / "banned_pairs.json")
        recon_raw, rec_mt, rec_ok, _ = self._read_json(logs / "reconcile_state.json")

        managed = managed_raw if isinstance(managed_raw, dict) else {}
        orders = orders_raw if isinstance(orders_raw, dict) else {}
        per_symbol = orders.get("per_symbol") if isinstance(orders.get("per_symbol"), dict) else {}
        naked_set = set(str(s) for s in (orders.get("naked") or []))
        dupes_map = orders.get("dupes") if isinstance(orders.get("dupes"), dict) else {}

        positions = []
        trades = managed.get("trades") if isinstance(managed.get("trades"), dict) else {}
        for sym, t in sorted(trades.items()):
            if not isinstance(t, dict):
                continue
            entry = _safe_float(t.get("entry"))
            sl = _safe_float(t.get("sl"))
            tp = _safe_float(t.get("tp"))
            init_sl = _safe_float(t.get("initial_sl"))
            qty = _safe_float(t.get("qty"))
            init_qty = _safe_float(t.get("init_qty"))
            direction = str(t.get("direction") or "")
            notional = round(entry * qty, 2) if (entry is not None and qty is not None) else None
            sl_pct = round(abs(entry - sl) / entry * 100.0, 2) if (entry and sl is not None) else None
            tp_pct = round(abs(tp - entry) / entry * 100.0, 2) if (entry and tp is not None) else None
            rr = round(abs(tp - entry) / abs(entry - sl), 2) if (entry and sl is not None and tp is not None and abs(entry - sl) > 0) else None
            prot_ids = t.get("prot_ids") if isinstance(t.get("prot_ids"), dict) else {}
            positions.append({
                "symbol": str(sym),
                "direction": direction,
                "qty": qty,
                "init_qty": init_qty,
                "entry": entry,
                "sl": sl,
                "initial_sl": init_sl,
                "tp": tp,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "rr": rr,
                "notional_est": notional,
                "partial_done": bool(t.get("partial_done")),
                "be_done": bool(t.get("be_done")),
                "booked_pnl": _safe_float(t.get("booked_pnl"), 0.0),
                "mfe_r": round(_safe_float(t.get("mfe_r"), 0.0) or 0.0, 3),
                "strategy": str(t.get("strategy") or "NONE"),
                "has_sl_id": bool(prot_ids.get("sl")),
                "has_tp_id": bool(prot_ids.get("tp")),
                "exchange_orders": _safe_int(per_symbol.get(sym)),
                "is_naked": str(sym) in naked_set,
                "has_dupes": str(sym) in dupes_map,
            })

        dust_symbols = []
        if dust_ok and isinstance(dust_raw, dict):
            why_map = dust_raw.get("why") if isinstance(dust_raw.get("why"), dict) else {}
            for s in dust_raw.get("symbols") or []:
                dust_symbols.append({"symbol": str(s), "why": str(why_map.get(s) or "")})

        banned_pairs = []
        if ban_ok and isinstance(banned_raw, dict):
            for sym, info in sorted(banned_raw.items()):
                if not isinstance(info, dict):
                    continue
                banned_pairs.append({
                    "symbol": str(sym),
                    "n": _safe_int(info.get("n")),
                    "avg_r": _safe_float(info.get("avg_r")),
                    "pf_r": _safe_float(info.get("pf_r")),
                    "total_r": _safe_float(info.get("total_r")),
                    "banned_at": str(info.get("banned_at") or ""),
                    "reason": str(info.get("reason") or ""),
                })

        orders_audit = {
            "known": ord_ok and bool(orders),
            "as_of": ord_mt,
            "as_of_human": _fmt_ts(ord_mt),
            "stale": ord_stale,
            "orders": _safe_int(orders.get("orders")),
            "positions": _safe_int(orders.get("positions")),
            "protect_orders": _safe_int(orders.get("protect_orders")),
            "by_type": dict(orders.get("by_type") or {}),
            "orphans": _safe_int(orders.get("orphans")),
            "orphan_symbols": list(orders.get("orphan_symbols") or []),
            "dupes": dict(dupes_map),
            "naked": list(orders.get("naked") or []),
            "dust": list(orders.get("dust") or []),
            "per_symbol": dict(per_symbol),
        }

        reconcile = {
            "known": rec_ok and isinstance(recon_raw, dict),
            "last_run": _safe_float((recon_raw or {}).get("last_run")) if isinstance(recon_raw, dict) else None,
            "last_run_human": _fmt_ts(_safe_float((recon_raw or {}).get("last_run"))) if isinstance(recon_raw, dict) else None,
            "episodes": _safe_int((recon_raw or {}).get("episodes")) if isinstance(recon_raw, dict) else None,
            "written": _safe_int((recon_raw or {}).get("written")) if isinstance(recon_raw, dict) else None,
            "matched": _safe_int((recon_raw or {}).get("matched")) if isinstance(recon_raw, dict) else None,
        }

        as_of = max([m for m in (man_mt, ord_mt, dust_mt, ban_mt, rec_mt) if m is not None], default=None)
        return {
            "instance": instance,
            "as_of": as_of,
            "as_of_human": _fmt_ts(as_of),
            "stale": bool(man_stale or ord_stale or not man_ok),
            "managed_known": man_ok,
            "saved_ts": _safe_float(managed.get("saved_ts")),
            "saved_ts_human": _fmt_ts(_safe_float(managed.get("saved_ts"))),
            "positions": positions,
            "orders_audit": orders_audit,
            "dust_skip": dust_symbols,
            "banned_pairs": banned_pairs,
            "reconcile": reconcile,
        }

    # -------------------------------------------------------------------------
    # Performance & Trades (reuses monitor_report B-031 + perf_report 8 metrics)
    # -------------------------------------------------------------------------
    def _build_window_stats(self, pairs: list[tuple[dict[str, Any] | None, dict[str, Any]]], days: int, now: float) -> dict[str, Any]:
        if days > 0:
            cutoff = now - days * 86400.0
            filtered = [(o, c) for o, c in pairs if (_safe_float((c or {}).get("ts"), 0.0) or 0.0) >= cutoff]
        else:
            filtered = pairs
        st = MR.stats(filtered)
        return {
            "days": days,
            "n": _safe_int(st.get("n"), 0),
            "n_dropped": _safe_int(st.get("n_dropped"), 0),
            "wins": _safe_int(st.get("wins"), 0),
            "wr": _safe_float(st.get("wr"), 0.0),
            "pf_r": _safe_float(st.get("pf_r"), 0.0),
            "pf_pnl": _safe_float(st.get("pf_pnl"), 0.0),
            "e_r": _safe_float(st.get("e_r"), 0.0),
            "pnl": _safe_float(st.get("pnl"), 0.0),
        }

    def get_performance(self, instance: str, days: int = 30, bot_only: bool = True) -> dict[str, Any]:
        root = self._instance_root(instance)
        js = self._journals[instance]
        exists, mt = js.sync()
        if not exists:
            return {
                "instance": instance,
                "known": False,
                "stale": True,
                "as_of": None,
                "days": days,
                "bot_only": bot_only,
                "note": "Khong tim thay logs/journal.jsonl",
            }

        pairs, still_open, version = js.get_paired()
        risk_raw, _, _, _ = self._read_json(root / "logs" / "risk_state.json")
        strat_raw, strat_mt, _, _ = self._read_json(root / "logs" / "strategy_stats.json")
        start_balance = _safe_float((risk_raw or {}).get("start_balance"), PR.DEFAULT_BALANCE) if isinstance(risk_raw, dict) else PR.DEFAULT_BALANCE
        if not start_balance or start_balance <= 0:
            start_balance = PR.DEFAULT_BALANCE

        now_bucket = int(time.time() // 30) * 30
        cache_key = (version, days, bot_only, float(start_balance))
        with js.lock:
            cached_rep = js.perf_memo.get(cache_key)
        if cached_rep is not None and cached_rep.get("_bucket") == now_bucket:
            out = dict(cached_rep)
            out.pop("_bucket", None)
            return out

        now = float(time.time())
        selected_pairs = [(o, c) for o, c in pairs if o is not None] if bot_only else list(pairs)
        total_bot_pairs = sum(1 for o, _ in pairs if o is not None)
        total_manual_pairs = len(pairs) - total_bot_pairs

        if days > 0:
            cutoff = now - days * 86400.0
            window_pairs = [(o, c) for o, c in selected_pairs if (_safe_float((c or {}).get("ts"), 0.0) or 0.0) >= cutoff]
        else:
            window_pairs = selected_pairs

        # B-031 strict R validation using monitor_report._r_ok
        valid_pairs = [(o, c) for o, c in window_pairs if MR._r_ok(c)]
        n_dropped = len(window_pairs) - len(valid_pairs)
        mr_st = MR.stats(window_pairs)

        # Build enriched close rows matching perf_report semantics (on B-031 valid records for R)
        close_rows_all = []
        for o, c in valid_pairs:
            rec = dict(c)
            if o:
                rec.setdefault("setup_type", o.get("setup_type"))
                rec.setdefault("market_regime", o.get("market_regime"))
                rec.setdefault("strategy", o.get("strategy"))
            rec["_bot"] = bool(o)
            close_rows_all.append(rec)

        daily = PR.daily_pnl(close_rows_all)
        eq_vals = PR.equity_curve(daily, start_balance)
        dd_vals = PR.drawdowns(eq_vals)
        rets = PR.daily_returns(daily, start_balance)
        end_bal = eq_vals[-1] if eq_vals else start_balance
        span_days = len(daily)
        cg = PR.cagr(start_balance, end_bal, span_days)
        mdd = PR.max_drawdown(eq_vals)
        ulcer = PR.ulcer_index(eq_vals)
        sh = PR.sharpe(rets)
        so = PR.sortino(rets)
        ca = PR.calmar(cg, mdd)
        notes = PR._notes(rets, mdd)

        # Cumulative R series by day (for clean downsampled chart)
        daily_r_map: dict[str, float] = {}
        daily_n_map: dict[str, int] = {}
        for rec in close_rows_all:
            ts = _safe_float(rec.get("ts"), 0.0) or 0.0
            if ts <= 0:
                continue
            day = dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d")
            daily_r_map[day] = daily_r_map.get(day, 0.0) + (float(rec.get("r") or 0.0))
            daily_n_map[day] = daily_n_map.get(day, 0) + 1

        cum_r = 0.0
        curve = []
        for idx, (day, pnl) in enumerate(daily):
            cum_r += daily_r_map.get(day, 0.0)
            curve.append({
                "day": day,
                "daily_pnl": round(pnl, 4),
                "equity": round(eq_vals[idx + 1], 4),
                "dd_pct": round(dd_vals[idx + 1], 3),
                "daily_r": round(daily_r_map.get(day, 0.0), 3),
                "cum_r": round(cum_r, 3),
                "n": daily_n_map.get(day, 0),
            })

        if len(curve) > MAX_EQUITY_POINTS:
            step = max(1, len(curve) // MAX_EQUITY_POINTS)
            sampled = curve[::step]
            if sampled[-1] is not curve[-1]:
                sampled.append(curve[-1])
            curve = sampled

        def _group_breakdown(key: str) -> list[dict[str, Any]]:
            buckets: dict[str, list[dict[str, Any]]] = {}
            for rec in close_rows_all:
                k = str(rec.get(key) or "NONE")
                buckets.setdefault(k, []).append(rec)
            rows_out = []
            for name, items in buckets.items():
                pnls = [float(x.get("pnl") or 0.0) for x in items]
                rs = [float(x.get("r") or 0.0) for x in items]
                wins = sum(1 for x in items if x.get("won") or float(x.get("pnl") or 0.0) > 0)
                pf_pnl, _, _ = PR.profit_factor(pnls)
                pf_r, _, _ = PR.profit_factor(rs)
                n_it = len(items)
                rows_out.append({
                    "name": name,
                    "n": n_it,
                    "wins": wins,
                    "wr": round(wins / n_it * 100.0, 1) if n_it else 0.0,
                    "pf_r": None if math.isinf(pf_r) else round(pf_r, 3),
                    "pf_pnl": None if math.isinf(pf_pnl) else round(pf_pnl, 3),
                    "exp_r": round(sum(rs) / n_it, 4) if n_it else 0.0,
                    "pnl": round(sum(pnls), 2),
                })
            rows_out.sort(key=lambda x: -x["n"])
            return rows_out

        # Rolling windows (7, 14, 30, all) on same bot_only selection
        rolling = {
            str(w): self._build_window_stats(selected_pairs, w, now)
            for w in (7, 14, 30, 0)
        }

        exp_r = _safe_float(mr_st.get("e_r"), 0.0) or 0.0
        total_pnl = _safe_float(mr_st.get("pnl"), 0.0) or 0.0
        n_valid = _safe_int(mr_st.get("n"), 0) or 0
        insolvent = bool(eq_vals) and min(eq_vals) <= 0.0
        r_pnl_mismatch = n_valid > 0 and ((exp_r > 0) != (total_pnl > 0))

        # Live strategy_stats.json snapshot
        strat_file = []
        if isinstance(strat_raw, dict):
            for k, v in sorted(strat_raw.items()):
                if not isinstance(v, dict):
                    continue
                n_s = _safe_int(v.get("n"), 0) or 0
                wins_s = _safe_int(v.get("wins"), 0) or 0
                sum_r = _safe_float(v.get("sum_r"), 0.0) or 0.0
                strat_file.append({
                    "strategy": str(k),
                    "n": n_s,
                    "n_bad_r": _safe_int(v.get("n_bad_r"), 0),
                    "wins": wins_s,
                    "wr": round(wins_s / n_s * 100.0, 1) if n_s else 0.0,
                    "sum_r": round(sum_r, 3),
                    "avg_r": round(sum_r / n_s, 4) if n_s else 0.0,
                })

        rep = {
            "_bucket": now_bucket,
            "instance": instance,
            "known": True,
            "stale": False,
            "as_of": mt,
            "as_of_human": _fmt_ts(mt),
            "days": days,
            "bot_only": bot_only,
            "r_band": list(MR.R_BAND),
            "counts": {
                "total_closed": len(pairs),
                "bot_closed": total_bot_pairs,
                "manual_closed": total_manual_pairs,
                "still_open_in_journal": still_open,
                "window_raw": len(window_pairs),
                "window_valid": n_valid,
                "n_dropped_b031": n_dropped,
                "small_sample": n_valid < 30,
            },
            "metrics": {
                "days_active": span_days,
                "trades": n_valid,
                "wins": _safe_int(mr_st.get("wins"), 0),
                "winrate": _safe_float(mr_st.get("wr"), 0.0),
                "pf_r": _safe_float(mr_st.get("pf_r"), 0.0),
                "pf_pnl": _safe_float(mr_st.get("pf_pnl"), 0.0),
                "exp_r": exp_r,
                "exp_pnl": round(total_pnl / n_valid, 4) if n_valid else 0.0,
                "pnl": total_pnl,
                "start_balance": round(start_balance, 2),
                "end_balance": round(end_bal, 2),
                "return_pct": round((end_bal / start_balance - 1.0) * 100.0, 2) if start_balance else 0.0,
                "cagr_pct": round(cg, 2),
                "sharpe": round(sh, 3),
                "sortino": round(so, 3),
                "calmar": round(ca, 3),
                "max_dd_pct": round(mdd, 2),
                "ulcer_pct": round(ulcer, 2),
                "avg_hold_min": _safe_float(mr_st.get("avg_hold_min")),
                "insolvent": insolvent,
                "r_pnl_mismatch": r_pnl_mismatch,
                "notes": notes,
            },
            "rolling": rolling,
            "curve": curve,
            "breakdowns": {
                "strategy": _group_breakdown("strategy"),
                "setup_type": _group_breakdown("setup_type"),
                "market_regime": _group_breakdown("market_regime"),
                "direction": _group_breakdown("direction"),
            },
            "strategy_stats_file": {
                "as_of": strat_mt,
                "rows": strat_file,
            },
        }
        with js.lock:
            js.perf_memo[cache_key] = rep
        out = dict(rep)
        out.pop("_bucket", None)
        return out

    def get_trades(
        self,
        instance: str,
        limit: int = DEFAULT_TRADES_LIMIT,
        offset: int = 0,
        symbol: str = "",
        strategy: str = "",
        bot_only: bool = True,
        outcome: str = "all",
    ) -> dict[str, Any]:
        js = self._journals[instance]
        exists, mt = js.sync()
        if not exists:
            return {"instance": instance, "known": False, "as_of": None, "total": 0, "items": []}

        pairs, _, _ = js.get_paired()
        sym_q = symbol.strip().upper()
        strat_q = strategy.strip().upper()
        out_q = outcome.strip().lower()

        filtered = []
        # Newest first
        for o, c in reversed(pairs):
            is_bot = o is not None
            if bot_only and not is_bot:
                continue
            pair_name = str(c.get("pair") or c.get("symbol") or (o or {}).get("pair") or (o or {}).get("symbol") or "")
            if sym_q and sym_q not in pair_name.upper():
                continue
            strat_name = str(c.get("strategy") or (o or {}).get("strategy") or "NONE")
            if strat_q and strat_q != "ALL" and strat_q != strat_name.upper():
                continue
            pnl = _safe_float(c.get("pnl"), 0.0) or 0.0
            won = bool(c.get("won")) if "won" in c else (pnl > 0)
            if out_q == "win" and not won:
                continue
            if out_q == "loss" and won:
                continue
            filtered.append((o, c, pair_name, strat_name, pnl, won, is_bot))

        total = len(filtered)
        page = filtered[offset : offset + limit]
        items = []
        for o, c, pair_name, strat_name, pnl, won, is_bot in page:
            ts = _safe_float(c.get("ts"))
            open_ts = _safe_float((o or {}).get("ts"))
            hold_min = round((ts - open_ts) / 60.0, 1) if (ts and open_ts and ts >= open_ts) else None
            r_val = _safe_float(c.get("r"))
            items.append({
                "ts": ts,
                "time": _fmt_ts(ts),
                "symbol": pair_name,
                "direction": str(c.get("direction") or (o or {}).get("direction") or ""),
                "source": "BOT" if is_bot else "MANUAL",
                "strategy": strat_name,
                "setup_type": str(c.get("setup_type") or (o or {}).get("setup_type") or "NONE"),
                "market_regime": str(c.get("market_regime") or (o or {}).get("market_regime") or "NONE"),
                "entry": _safe_float((o or {}).get("entry") or c.get("entry")),
                "exit": _safe_float(c.get("exit") or c.get("price")),
                "r": round(r_val, 3) if r_val is not None else None,
                "r_valid": MR._r_ok(c),
                "pnl": round(pnl, 4),
                "won": won,
                "reason": str(c.get("reason") or ""),
                "hold_min": hold_min,
            })

        return {
            "instance": instance,
            "known": True,
            "as_of": mt,
            "as_of_human": _fmt_ts(mt),
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    # -------------------------------------------------------------------------
    # Council & Learner tab
    # -------------------------------------------------------------------------
    def get_council(self, instance: str) -> dict[str, Any]:
        root = self._instance_root(instance)
        logs = root / "logs"

        agent_raw, ag_mt, ag_ok, _ = self._read_json(logs / "agent_state.json")
        chb_raw, chb_mt, chb_ok, _ = self._read_json(logs / "council_heartbeat.json")
        ccfg_raw, _, ccfg_ok, _ = self._read_json(logs / "council_config.json")
        cd_raw, cd_mt, cd_ok, _ = self._read_json(logs / "council_daemon.json")
        gaps_raw, gaps_mt, gaps_ok, _ = self._read_json(logs / "council_gaps.json")
        outbox_raw, ob_mt, ob_ok, _ = self._read_json(logs / "council_outbox.json")
        learner_raw, lr_mt, lr_ok, _ = self._read_json(logs / "learner.json")
        lessons_raw, ls_mt, ls_ok, _ = self._read_json(logs / "lessons.json")
        probe_raw, _, pr_ok, _ = self._read_json(logs / "model_probe.json")

        js = self._journals[instance]
        js.sync()
        recent_votes = js.get_agent_votes()[:80]

        # Daily spend/votes series from council_daemon.json
        daily_series = []
        if cd_ok and isinstance(cd_raw, dict):
            spend_map = cd_raw.get("spend") if isinstance(cd_raw.get("spend"), dict) else {}
            votes_map = cd_raw.get("votes") if isinstance(cd_raw.get("votes"), dict) else {}
            days = sorted(set(spend_map.keys()) | set(votes_map.keys()))[-30:]
            for d in days:
                daily_series.append({
                    "day": str(d),
                    "spend_usd": round(_safe_float(spend_map.get(d), 0.0) or 0.0, 5),
                    "votes": _safe_int(votes_map.get(d), 0),
                })

        # Outbox recent items (newest first)
        outbox_items = []
        if ob_ok and isinstance(outbox_raw, list):
            for it in reversed(outbox_raw[-MAX_OUTBOX_ITEMS:]):
                if not isinstance(it, dict):
                    continue
                outbox_items.append({
                    "ts": _safe_float(it.get("ts")),
                    "time": _fmt_ts(_safe_float(it.get("ts"))),
                    "mode": str(it.get("mode") or ""),
                    "kind": str(it.get("kind") or ""),
                    "key": str(it.get("key") or ""),
                    "question": str(it.get("question") or "")[:360],
                    "verdict": str(it.get("verdict") or ""),
                    "n_allow": _safe_int(it.get("n_allow"), 0),
                    "n_veto": _safe_int(it.get("n_veto"), 0),
                    "n_abstain": _safe_int(it.get("n_abstain"), 0),
                    "cost_usd": _safe_float(it.get("cost_usd"), 0.0),
                    "context": [str(x)[:200] for x in (it.get("context") or [])[:4]],
                })

        # Learner feature weights sorted by absolute magnitude
        learner_weights = []
        learner_meta: dict[str, Any] = {"known": lr_ok and isinstance(learner_raw, dict)}
        if lr_ok and isinstance(learner_raw, dict):
            w_map = learner_raw.get("w") if isinstance(learner_raw.get("w"), dict) else {}
            for feat, val in sorted(w_map.items(), key=lambda kv: -abs(_safe_float(kv[1], 0.0) or 0.0)):
                learner_weights.append({"feature": str(feat), "weight": round(_safe_float(val, 0.0) or 0.0, 5)})
            learner_meta.update({
                "bias": _safe_float(learner_raw.get("b")),
                "n_updates": _safe_int(learner_raw.get("n")),
                "ts": _safe_float(learner_raw.get("ts")),
                "ts_human": _fmt_ts(_safe_float(learner_raw.get("ts"))),
                "refit": learner_raw.get("refit") if isinstance(learner_raw.get("refit"), dict) else None,
            })

        # Lessons top positive & worst negative buckets
        lessons_buckets = []
        lessons_meta: dict[str, Any] = {"known": ls_ok and isinstance(lessons_raw, dict)}
        if ls_ok and isinstance(lessons_raw, dict):
            lessons_meta.update({
                "trades": _safe_int(lessons_raw.get("trades")),
                "unpaired": _safe_int(lessons_raw.get("unpaired")),
                "as_of": ls_mt,
                "as_of_human": _fmt_ts(ls_mt),
            })
            b_map = lessons_raw.get("buckets") if isinstance(lessons_raw.get("buckets"), dict) else {}
            for label, b in b_map.items():
                if not isinstance(b, dict):
                    continue
                lessons_buckets.append({
                    "bucket": str(label),
                    "n": _safe_int(b.get("n"), 0),
                    "wr": _safe_float(b.get("wr"), 0.0),
                    "avg_r": _safe_float(b.get("avg_r"), 0.0),
                    "pf": _safe_float(b.get("pf"), 0.0),
                    "pnl": _safe_float(b.get("pnl"), 0.0),
                })
            lessons_buckets.sort(key=lambda x: -(x["n"] or 0))

        as_of = max([m for m in (ag_mt, chb_mt, cd_mt, gaps_mt, ob_mt, lr_mt, ls_mt) if m is not None], default=None)
        return {
            "instance": instance,
            "as_of": as_of,
            "as_of_human": _fmt_ts(as_of),
            "agent_state": agent_raw if (ag_ok and isinstance(agent_raw, dict)) else None,
            "council_heartbeat": chb_raw if (chb_ok and isinstance(chb_raw, dict)) else None,
            "council_config": ccfg_raw if (ccfg_ok and isinstance(ccfg_raw, dict)) else None,
            "model_probe": probe_raw if (pr_ok and isinstance(probe_raw, dict)) else None,
            "daily_series": daily_series,
            "gaps": {
                "known": gaps_ok and isinstance(gaps_raw, dict),
                "as_of": gaps_mt,
                "as_of_human": _fmt_ts(gaps_mt),
                "items": list((gaps_raw or {}).get("gaps") or []) if isinstance(gaps_raw, dict) else [],
            },
            "outbox": outbox_items,
            "recent_votes": recent_votes,
            "learner": {"meta": learner_meta, "weights": learner_weights},
            "lessons": {"meta": lessons_meta, "buckets": lessons_buckets[:40]},
        }

    # -------------------------------------------------------------------------
    # Harness & Security tab
    # -------------------------------------------------------------------------
    def get_harness(self, instance: str) -> dict[str, Any]:
        root = self._instance_root(instance)
        logs = root / "logs"

        ops_q_raw, oq_mt, _, _ = self._read_json(logs / "ops_questions.json")
        ops_hist_raw, oh_mt, _, _ = self._read_json(logs / "ops_queue.json")
        rev_raw, rev_mt, rev_ok, _ = self._read_json(logs / "review_due.json")
        reg_raw, reg_mt, reg_ok, _ = self._read_json(logs / "regress_watch.json")
        drift_raw, dr_mt, dr_ok, _ = self._read_json(logs / "drift_probe.json")
        tg_raw, tg_mt, tg_ok, _ = self._read_json(logs / "telegram_bridge.json")

        ledger_rows, led_mt, _ = self._read_jsonl_tail(logs / "harness_ledger.jsonl", MAX_LEDGER_ITEMS)
        auto_rows, aut_mt, _ = self._read_jsonl_tail(logs / "autonomy.jsonl", MAX_AUTONOMY_ITEMS)

        # Repo-level security findings & bug manifest (shared codebase)
        sec_raw, sec_mt, sec_ok, _ = self._read_json(self.roots["testnet"] / "security" / "findings.json")
        bug_raw, bug_mt, bug_ok, _ = self._read_json(self.roots["testnet"] / "golden" / "bug_manifest.json")

        ops_questions = []
        if isinstance(ops_q_raw, list):
            for q in reversed(ops_q_raw):
                if isinstance(q, dict):
                    ops_questions.append({
                        "id": _safe_int(q.get("id")),
                        "ts": _safe_float(q.get("ts")),
                        "time": _fmt_ts(_safe_float(q.get("ts"))),
                        "question": str(q.get("question") or ""),
                        "why": str(q.get("why") or ""),
                        "options": [str(x) for x in (q.get("options") or [])],
                        "priority": str(q.get("priority") or "normal"),
                        "status": str(q.get("status") or "OPEN"),
                        "answer": str(q.get("answer") or ""),
                    })

        ops_history = []
        if isinstance(ops_hist_raw, list):
            for q in reversed(ops_hist_raw[-30:]):
                if isinstance(q, dict):
                    ops_history.append({
                        "id": _safe_int(q.get("id")),
                        "ts": _safe_float(q.get("ts")),
                        "time": _fmt_ts(_safe_float(q.get("ts"))),
                        "question": str(q.get("question") or ""),
                        "why": str(q.get("why") or "")[:360],
                        "priority": str(q.get("priority") or "normal"),
                        "status": str(q.get("status") or ""),
                        "answer": str(q.get("answer") or "")[:400],
                    })

        regress_notified = []
        regress_fixed = {}
        if reg_ok and isinstance(reg_raw, dict):
            regress_fixed = {
                str(k): _fmt_ts(_safe_float(v))
                for k, v in (reg_raw.get("fixed_at") or {}).items()
            }
            for k, v in (reg_raw.get("notified") or {}).items():
                if not isinstance(v, dict):
                    continue
                regress_notified.append({
                    "key": str(k),
                    "kind": str(v.get("kind") or ""),
                    "ts": _safe_float(v.get("ts")),
                    "time": _fmt_ts(_safe_float(v.get("ts"))),
                    "n": _safe_int(v.get("n")),
                    "text": str(v.get("text") or ""),
                })
            regress_notified.sort(key=lambda x: -(x["ts"] or 0.0))

        drift_items = []
        if dr_ok and isinstance(drift_raw, dict):
            for k, v in (drift_raw.get("notified") or {}).items():
                if not isinstance(v, dict):
                    continue
                drift_items.append({
                    "key": str(k),
                    "kind": str(v.get("kind") or ""),
                    "ts": _safe_float(v.get("ts")),
                    "time": _fmt_ts(_safe_float(v.get("ts"))),
                    "why": str(v.get("why") or ""),
                })
            drift_items.sort(key=lambda x: -(x["ts"] or 0.0))

        # Security audit summary
        security = {"known": False}
        if sec_ok and isinstance(sec_raw, dict):
            security = {
                "known": True,
                "audited_at": str(sec_raw.get("audited_at") or ""),
                "scope": str(sec_raw.get("scope") or ""),
                "findings": [
                    {
                        "id": str(f.get("id") or ""),
                        "title": str(f.get("title") or ""),
                        "severity": str(f.get("severity") or ""),
                        "status": str(f.get("status") or ""),
                        "bug": str(f.get("bug") or ""),
                        "boundary": str(f.get("boundary") or ""),
                        "guard": str(f.get("guard") or ""),
                    }
                    for f in (sec_raw.get("findings") or [])
                    if isinstance(f, dict)
                ],
                "controls": [
                    {"id": str(c.get("id") or ""), "what": str(c.get("what") or ""), "how": str(c.get("how") or "")}
                    for c in (sec_raw.get("controls") or [])
                    if isinstance(c, dict)
                ],
                "validations": [
                    {
                        "id": str(v.get("id") or ""),
                        "what": str(v.get("what") or ""),
                        "result": str(v.get("result") or ""),
                        "verdict": str(v.get("verdict") or ""),
                    }
                    for v in (sec_raw.get("validations") or [])
                    if isinstance(v, dict)
                ],
            }

        bug_manifest = {"known": False}
        if bug_ok and isinstance(bug_raw, dict):
            digest = str(bug_raw.get("digest") or "")
            bug_manifest = {
                "known": True,
                "n_classes": _safe_int(bug_raw.get("n_classes")),
                "n_tests": _safe_int(bug_raw.get("n_tests")),
                "digest_short": digest[:16],
                "n_files": len(bug_raw.get("files") or []),
                "as_of": bug_mt,
                "as_of_human": _fmt_ts(bug_mt),
            }

        # Telegram bridge summary (only counts/last_ts — no chat ids)
        tg_summary = {"known": tg_ok and isinstance(tg_raw, dict), "as_of": tg_mt, "as_of_human": _fmt_ts(tg_mt)}
        if tg_ok and isinstance(tg_raw, dict):
            sent = tg_raw.get("sent") if isinstance(tg_raw.get("sent"), dict) else {}
            tg_summary["sent_count"] = len(sent)

        as_of = max([m for m in (oq_mt, oh_mt, rev_mt, reg_mt, dr_mt, led_mt, aut_mt, sec_mt, bug_mt) if m is not None], default=None)
        return {
            "instance": instance,
            "as_of": as_of,
            "as_of_human": _fmt_ts(as_of),
            "ops_questions": ops_questions,
            "ops_history": ops_history,
            "review_due": {
                "known": rev_ok and isinstance(rev_raw, dict),
                "last_run": _fmt_ts(_safe_float((rev_raw or {}).get("last_run"))) if isinstance(rev_raw, dict) else None,
                "pushed": (rev_raw or {}).get("pushed") if isinstance(rev_raw, dict) else {},
            },
            "regress_watch": {
                "known": reg_ok,
                "as_of_human": _fmt_ts(reg_mt),
                "fixed_at": regress_fixed,
                "notified": regress_notified,
            },
            "drift_probe": {
                "known": dr_ok,
                "last_run": _fmt_ts(_safe_float((drift_raw or {}).get("last_run"))) if isinstance(drift_raw, dict) else None,
                "items": drift_items,
            },
            "security": security,
            "bug_manifest": bug_manifest,
            "telegram_bridge": tg_summary,
            "ledger": list(reversed(ledger_rows)),
            "autonomy": list(reversed(auto_rows)),
            "deadman": self.get_deadman_summary(),
        }

    # -------------------------------------------------------------------------
    # Whitelisted Markdown docs viewer
    # -------------------------------------------------------------------------
    def list_docs(self) -> dict[str, Any]:
        items = []
        for doc_id, (inst, rel_name, label) in DOC_WHITELIST.items():
            path = self.roots[inst] / rel_name
            try:
                st = path.stat()
                exists = True
                size = st.st_size
                mt = st.st_mtime
            except OSError:
                exists = False
                size = 0
                mt = None
            items.append({
                "id": doc_id,
                "label": label,
                "instance": inst,
                "exists": exists,
                "size_bytes": size,
                "as_of": mt,
                "as_of_human": _fmt_ts(mt),
            })
        return {"docs": items}

    def read_doc(self, doc_id: str) -> dict[str, Any] | None:
        spec = DOC_WHITELIST.get(doc_id)
        if spec is None:
            return None
        inst, rel_name, label = spec
        path = self.roots[inst] / rel_name
        try:
            st = path.stat()
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {"id": doc_id, "label": label, "exists": False, "content": "", "truncated": False}
        truncated = len(raw) > MAX_DOC_CHARS
        content = raw[:MAX_DOC_CHARS] if truncated else raw
        return {
            "id": doc_id,
            "label": label,
            "instance": inst,
            "exists": True,
            "size_bytes": st.st_size,
            "as_of": st.st_mtime,
            "as_of_human": _fmt_ts(st.st_mtime),
            "truncated": truncated,
            "content": content,
        }


# =============================================================================
# Hardened Read-Only HTTP Handler
# =============================================================================
def _is_allowed_host(host_header: str, bound_port: int) -> bool:
    """Strict Host validation (anti-DNS-rebinding): reject empty Host and wrong ports."""
    if not host_header or not host_header.strip():
        return False
    h = host_header.strip().lower()
    allowed = {
        f"127.0.0.1:{bound_port}",
        f"localhost:{bound_port}",
        f"[::1]:{bound_port}",
    }
    if bound_port == 80:
        allowed.update({"127.0.0.1", "localhost", "[::1]"})
    return h in allowed


def _is_allowed_origin(origin_header: str, bound_port: int) -> bool:
    if not origin_header:
        return True
    o = origin_header.strip().lower()
    allowed = {
        f"http://127.0.0.1:{bound_port}",
        f"http://localhost:{bound_port}",
        f"http://[::1]:{bound_port}",
    }
    return o in allowed


def make_handler(store: DataStore, static_dir: Path = STATIC_DIR):
    req_gate = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "ATBDashboard/1.0"
        sys_version = ""

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(SOCKET_TIMEOUT_SEC)

        def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover
            if os.getenv("ATB_DASHBOARD_VERBOSE", "0") == "1":
                super().log_message(fmt, *args)

        def _send_security_headers(self) -> None:
            for k, v in SECURITY_HEADERS:
                self.send_header(k, v)

        def _send_bytes(
            self,
            body: bytes,
            content_type: str,
            status: int = 200,
            head_only: bool = False,
            etag: str | None = None,
        ) -> None:
            if len(body) > MAX_RESPONSE_BYTES:
                err = json.dumps({"error": "Response exceeds safety limit", "status": 500}).encode("utf-8")
                self.send_response(500)
                self._send_security_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(err)))
                self.end_headers()
                if not head_only:
                    self.wfile.write(err)
                return
            if etag and status == 200:
                inm = (self.headers.get("If-None-Match") or "").strip()
                if inm == etag:
                    self.send_response(304)
                    self._send_security_headers()
                    self.send_header("ETag", etag)
                    self.end_headers()
                    return
            self.send_response(status)
            self._send_security_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if etag:
                self.send_header("ETag", etag)
            self.end_headers()
            if not head_only and body:
                self.wfile.write(body)

        def _etag_for(self, sanitized: Any) -> str:
            """Stable ETag excluding volatile wall-clock fields (keeps heartbeat_ts & bot.status)."""
            def _strip_volatile(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {
                        k: _strip_volatile(v)
                        for k, v in obj.items()
                        if k not in {"server_ts", "server_ts_human", "heartbeat_age_s"}
                    }
                if isinstance(obj, list):
                    return [_strip_volatile(x) for x in obj]
                return obj

            canon = json.dumps(_strip_volatile(sanitized), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
            return f'W/"{hashlib.sha256(canon).hexdigest()[:20]}"'

        def _send_json(self, payload: Any, status: int = 200, head_only: bool = False) -> None:
            sanitized = redact_obj(payload)
            body = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            etag = self._etag_for(sanitized) if status == 200 else None
            self._send_bytes(body, "application/json; charset=utf-8", status=status, head_only=head_only, etag=etag)

        def _send_error_json(self, status: int, message: str, head_only: bool = False) -> None:
            self._send_json({"error": message, "status": status}, status=status, head_only=head_only)

        def _reject_method(self) -> None:
            body = json.dumps({"error": "Method Not Allowed (read-only dashboard)", "status": 405}).encode("utf-8")
            self.send_response(405)
            self._send_security_headers()
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            self._reject_method()

        def do_PUT(self) -> None:
            self._reject_method()

        def do_DELETE(self) -> None:
            self._reject_method()

        def do_PATCH(self) -> None:
            self._reject_method()

        def do_OPTIONS(self) -> None:
            self._reject_method()

        def _check_host_and_origin(self, head_only: bool) -> bool:
            bound_port = int(self.server.server_address[1])
            host = self.headers.get("Host") or ""
            if not _is_allowed_host(host, bound_port):
                self._send_error_json(403, "Forbidden Host header", head_only=head_only)
                return False
            origin = self.headers.get("Origin") or ""
            if not _is_allowed_origin(origin, bound_port):
                self._send_error_json(403, "Forbidden Origin header", head_only=head_only)
                return False
            return True

        def _parse_target(self, qs: dict[str, list[str]], allow_both: bool = False) -> str | None:
            raw = (qs.get("t") or ["testnet"])[0].strip().lower()
            allowed = {"testnet", "live", "both"} if allow_both else {"testnet", "live"}
            return raw if raw in allowed else None

        def _dispatch(self, head_only: bool) -> None:
            if not self._check_host_and_origin(head_only=head_only):
                return

            parsed = urlparse(self.path)
            path = parsed.path or "/"
            qs = parse_qs(parsed.query, keep_blank_values=False)

            if is_suspicious_path(path):
                self._send_error_json(403, "Forbidden path", head_only=head_only)
                return

            # API routes (fixed whitelist)
            if path == "/api/health":
                self._send_json({"ok": True, "read_only": True, "version": "1.0"}, head_only=head_only)
                return

            if path == "/api/overview":
                target = self._parse_target(qs, allow_both=True)
                if not target:
                    self._send_error_json(400, "Invalid target (expected testnet|live|both)", head_only=head_only)
                    return
                self._send_json(store.get_overview(target), head_only=head_only)
                return

            if path == "/api/positions":
                target = self._parse_target(qs, allow_both=False)
                if not target:
                    self._send_error_json(400, "Invalid target (expected testnet|live)", head_only=head_only)
                    return
                self._send_json(store.get_positions(target), head_only=head_only)
                return

            if path == "/api/performance":
                target = self._parse_target(qs, allow_both=False)
                if not target:
                    self._send_error_json(400, "Invalid target (expected testnet|live)", head_only=head_only)
                    return
                days_val = _safe_int((qs.get("days") or ["30"])[0])
                if days_val is None or days_val not in ALLOWED_WINDOWS:
                    self._send_error_json(400, "Invalid days (expected 0|7|14|30|90)", head_only=head_only)
                    return
                bot_only_str = (qs.get("bot_only") or ["1"])[0].strip().lower()
                if bot_only_str not in {"0", "1", "true", "false"}:
                    self._send_error_json(400, "Invalid bot_only (expected 0|1)", head_only=head_only)
                    return
                bot_only = bot_only_str in {"1", "true"}
                self._send_json(store.get_performance(target, days=days_val, bot_only=bot_only), head_only=head_only)
                return

            if path == "/api/trades":
                target = self._parse_target(qs, allow_both=False)
                if not target:
                    self._send_error_json(400, "Invalid target (expected testnet|live)", head_only=head_only)
                    return
                limit = _safe_int((qs.get("limit") or [str(DEFAULT_TRADES_LIMIT)])[0])
                offset = _safe_int((qs.get("offset") or ["0"])[0])
                if limit is None or limit < 1 or limit > MAX_TRADES_LIMIT:
                    self._send_error_json(400, f"Invalid limit (1..{MAX_TRADES_LIMIT})", head_only=head_only)
                    return
                if offset is None or offset < 0:
                    self._send_error_json(400, "Invalid offset (>= 0)", head_only=head_only)
                    return
                bot_only_str = (qs.get("bot_only") or ["1"])[0].strip().lower()
                if bot_only_str not in {"0", "1", "true", "false"}:
                    self._send_error_json(400, "Invalid bot_only", head_only=head_only)
                    return
                outcome = (qs.get("outcome") or ["all"])[0].strip().lower()
                if outcome not in {"all", "win", "loss"}:
                    self._send_error_json(400, "Invalid outcome (all|win|loss)", head_only=head_only)
                    return
                symbol = (qs.get("symbol") or [""])[0][:40]
                strategy = (qs.get("strategy") or [""])[0][:40]
                self._send_json(
                    store.get_trades(
                        target,
                        limit=limit,
                        offset=offset,
                        symbol=symbol,
                        strategy=strategy,
                        bot_only=bot_only_str in {"1", "true"},
                        outcome=outcome,
                    ),
                    head_only=head_only,
                )
                return

            if path == "/api/council":
                target = self._parse_target(qs, allow_both=False)
                if not target:
                    self._send_error_json(400, "Invalid target (expected testnet|live)", head_only=head_only)
                    return
                self._send_json(store.get_council(target), head_only=head_only)
                return

            if path == "/api/harness":
                target = self._parse_target(qs, allow_both=False)
                if not target:
                    self._send_error_json(400, "Invalid target (expected testnet|live)", head_only=head_only)
                    return
                self._send_json(store.get_harness(target), head_only=head_only)
                return

            if path == "/api/docs":
                self._send_json(store.list_docs(), head_only=head_only)
                return

            if path.startswith("/api/docs/"):
                doc_id = path[len("/api/docs/") :].strip()
                if not doc_id or "/" in doc_id or doc_id not in DOC_WHITELIST:
                    self._send_error_json(404, "Unknown document id", head_only=head_only)
                    return
                doc = store.read_doc(doc_id)
                if doc is None:
                    self._send_error_json(404, "Unknown document id", head_only=head_only)
                    return
                self._send_json(doc, head_only=head_only)
                return

            # Static asset whitelist
            resolved = resolve_static_file(static_dir, path)
            if resolved is None:
                self._send_error_json(404, "Not Found", head_only=head_only)
                return
            file_path, content_type = resolved
            try:
                data = file_path.read_bytes()
            except OSError:
                self._send_error_json(404, "Not Found", head_only=head_only)
                return
            etag = f'W/"{hashlib.sha256(data).hexdigest()[:20]}"'
            self._send_bytes(data, content_type, status=200, head_only=head_only, etag=etag)

        def do_GET(self) -> None:
            if not req_gate.acquire(blocking=False):
                self._send_error_json(503, "Too many concurrent requests", head_only=False)
                return
            try:
                self._dispatch(head_only=False)
            finally:
                req_gate.release()

        def do_HEAD(self) -> None:
            if not req_gate.acquire(blocking=False):
                self._send_error_json(503, "Too many concurrent requests", head_only=True)
                return
            try:
                self._dispatch(head_only=True)
            finally:
                req_gate.release()

    return DashboardHandler


def create_server(
    port: int = DEFAULT_PORT,
    store: DataStore | None = None,
    static_dir: Path = STATIC_DIR,
    host: str = DEFAULT_HOST,
) -> ThreadingHTTPServer:
    """Create a loopback-only ThreadingHTTPServer (rejects non-loopback hosts)."""
    if host not in ALLOWED_BIND_HOSTS:
        raise ValueError(f"Dashboard chi duoc phep bind loopback ({sorted(ALLOWED_BIND_HOSTS)}), nhan: {host!r}")
    ds = store if store is not None else DataStore()
    handler_cls = make_handler(ds, static_dir=static_dir)
    ThreadingHTTPServer.allow_reuse_address = True
    return ThreadingHTTPServer((host, int(port)), handler_cls)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only local dashboard for autonomous-trading-bot")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Loopback port (default {DEFAULT_PORT})")
    args = parser.parse_args(argv)

    server = create_server(port=args.port, host=DEFAULT_HOST)
    actual_port = server.server_address[1]
    print(f"ATB Read-Only Dashboard listening on http://{DEFAULT_HOST}:{actual_port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
