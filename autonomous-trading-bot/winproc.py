"""Helper Windows: chay tien trinh con KHONG hien cua so console.

Vi sao can: bot chay duoi `pythonw.exe` (KHONG co console). Moi tien trinh con
ma Windows spawn tu mot tien trinh khong-console se **TU MO mot cua so console
moi** -> nguoi dung thay cua so den nhay len giua man hinh (da gap that 12/10:
`git.exe` pop-up moi 30 phut vi `state_sync.py` chay `git commit/push` tu
supervisor, va `taskkill/tasklist` cua watchdog).

Cach dung:

    import winproc
    subprocess.run(["git", "status"], **winproc.hide_kwargs())

`hide_kwargs()` tra {} tren OS khac Windows nen goi o dau cung an toan.
"""
from __future__ import annotations

import subprocess
import sys

#: Co Windows "khong tao console" (0x08000000). Lay tu subprocess neu co.
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def hide_kwargs() -> dict:
    """kwargs bo sung cho `subprocess.run/Popen` de con KHONG hien cua so.

    - `creationflags=CREATE_NO_WINDOW`: khong cap console moi cho tien trinh con.
    - `startupinfo` voi `SW_HIDE`: ep cua so con an (phong khi con tu mo cua so
      rieng, vd `cmd.exe` ben trong).
    """
    if sys.platform != "win32":
        return {}
    kw: dict = {"creationflags": CREATE_NO_WINDOW}
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        kw["startupinfo"] = si
    except Exception:  # noqa: BLE001  (nen tang khong ho tro)
        pass
    return kw


def run_hidden(cmd: list, **kwargs):
    """`subprocess.run` + an cua so. Moi tham so khac truyen nguyen."""
    return subprocess.run(cmd, **hide_kwargs(), **kwargs)


def popen_hidden(cmd: list, **kwargs):
    """`subprocess.Popen` + an cua so."""
    return subprocess.Popen(cmd, **hide_kwargs(), **kwargs)
