"""Ghi file NGUYEN TU (tmp -> fsync -> os.replace) — MOT noi duy nhat cho file trang thai.

Vi sao (21/10, sau khi ra soat repo `ghgrab`): ben do co `Config::validate_path` +
`Config::save` (tao thu muc cha, kiem tra quyen ghi) TRUOC khi ghi cau hinh. Doi chieu
lai thi du an nay con vai cho ghi TRUC TIEP file trang thai quan trong:

    logs/entries_pause.json   cong tam dung vao lenh   <- entries_gate._write
    .env + logs/.live_flipped key API + moc doi LIVE    <- state_sync.go_live
    logs/state.json           nhip supervisor           <- run_forever._touch
    logs/deadman.json         watchdog                  <- tools/deadman.save_state
    logs/ops/*.md             artifact quyet dinh        <- tools/ops_artifact

Mat dien / bi kill giua luc ghi ⇒ file BI CAT NGANG. Voi `.env` thi bot **khong khoi dong
duoc**; voi `entries_pause.json` thi `entries_gate.read()` tra `{}` ⇒ bot **tu mo lai vao
lenh** trong khi nguoi van hanh tuong dang tam dung — dung lop loi "im lang" cua du an.

Cach lam: ghi ra file tam CUNG THU MUC, `flush` + `os.fsync` (du lieu xuong dia TRUOC khi
doi ten), roi `os.replace` (nguyen tu tren cung volume). Windows hay tra `PermissionError`
khi AV/indexer dang mo file ⇒ retry vai lan voi delay ngan; that bai thi **file cu GIU
NGUYEN** va nem OSError ra ngoai (khong bao gio de lai file nua voi).

    import atomic
    atomic.write_text_atomic("logs/x.json", text)
    atomic.write_json_atomic("logs/x.json", {"a": 1})
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

#: So lan thu lai khi `os.replace` bi khoa (Windows: AV/indexer/process khac dang mo file).
RETRIES = 5
#: Delay co so (giay); lan thu i nghi `delay * (i + 1)`.
DELAY = 0.05


def replace_retry(tmp, dst, *, retries: int = RETRIES, delay: float = DELAY) -> None:
    """`os.replace(tmp, dst)` + retry khi bi khoa. Het luot -> nem loi cuoi cung."""
    last: Exception | None = None
    for i in range(max(1, int(retries))):
        try:
            os.replace(tmp, dst)
            return
        except FileNotFoundError:
            raise
        except OSError as e:              # PermissionError (Win) / WinError 32 ...
            last = e
            if i + 1 < max(1, int(retries)):
                time.sleep(max(0.0, float(delay)) * (i + 1))
    assert last is not None
    raise last


def write_text_atomic(path, text: str, *, encoding: str = "utf-8",
                      retries: int = RETRIES, delay: float = DELAY) -> Path:
    """Ghi `text` vao `path` NGUYEN TU. Loi -> file cu giu nguyen + nem OSError.

    File tam luon nam CUNG THU MUC voi dich (khac volume thi `os.replace` khong nguyen tu).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix="." + p.name + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        replace_retry(tmp, p, retries=retries, delay=delay)
        return p
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json_atomic(path, obj, *, indent: int | None = 1, ensure_ascii: bool = False,
                      retries: int = RETRIES, delay: float = DELAY) -> Path:
    """`json.dumps` (giu chu Viet: `ensure_ascii=False`) roi ghi nguyen tu."""
    return write_text_atomic(path, json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent),
                             retries=retries, delay=delay)
