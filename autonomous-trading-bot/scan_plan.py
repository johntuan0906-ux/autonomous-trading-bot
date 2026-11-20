"""Chia danh sach cap thanh TUNG DOT (round-robin) + do tre khoi dong (19/11, B-068).

Vi sao: 2 instance dung CHUNG 1 IP, moi vong quet 40 cap voi `SCAN_WORKERS=8` ⇒ tai trong
weight 1 phut sat tran ⇒ ban IP (`-1003`), va **moi request trong luc bi chan lam ban DAI
them** (do that 19/11: 11:18 -> 11:59 -> 20:30, ca ngay LIVE khong quet duoc).

Cach chong khong phai "nghi khi bi chan" (da co B-044) ma la **dung cham tran ngay tu dau**:
chia cap thanh N dot, moi vong chi quet 1 dot (cac vong sau quay vong) ⇒ weight moi vong
giam ~N lan ma van phu het danh sach sau N vong.

Thuan (khong I/O) de test duoc offline.
"""
from __future__ import annotations


def pick_scan_batch(symbols, batch: int, round_idx: int,
                    must_include=()) -> list:
    """Chon `batch` cap cho vong `round_idx` (quay vong), luon kem `must_include`.

    - `batch <= 0` hoac `batch >= len(symbols)` ⇒ tra TOAN BO (giu hanh vi cu).
    - `must_include` (vi the dang mo) luon nam trong ket qua, KHONG bi cat boi batch.
    - Khong trung lap trong 1 ket qua; thu tu on dinh (must_include truoc).
    """
    syms = list(symbols or ())
    if not syms:
        return []
    must = []
    seen = set()
    for s in (must_include or ()):
        s = str(s)
        if s in syms and s not in seen:
            must.append(s)
            seen.add(s)
    try:
        b = int(batch)
    except (TypeError, ValueError):
        b = 0
    if b <= 0 or b >= len(syms):
        return must + [s for s in syms if s not in seen]
    n = len(syms)
    start = (int(round_idx or 0) * b) % n
    out = list(must)
    for i in range(b):
        s = syms[(start + i) % n]
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def warmup_seconds(configured, *, first_round: bool, just_unbanned: bool) -> float:
    """So giay phai cho TRUOC khi quet (0 = quet ngay).

    Do that: ngay sau restart / ngay sau khi ban het han, tai trong IP cua cua so 1 phut
    dang sat tran ⇒ quet ngay la cham `-1003` va bi cong gio. Cho 1 nhip de cua so reset.
    """
    try:
        base = max(0.0, float(configured or 0.0))
    except (TypeError, ValueError):
        base = 0.0
    if base <= 0:
        return 0.0
    if first_round:
        return base
    if just_unbanned:
        return base / 2.0        # ban vua het: doi mot nhip ngan la du
    return 0.0
