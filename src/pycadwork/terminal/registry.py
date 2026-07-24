"""Read cadwork's per-user ENV registry block (Windows only).

cadwork records its installed paths under
``HKEY_CURRENT_USER\\Software\\cadwork Informatik\\ENV`` — ``CADWORK.DIR`` (the
``cadwork.dir`` root that holds ``ci_start.exe``), plus the EXE / userprofile /
catalog / projects folders. The terminal runner reads ``CADWORK.DIR`` from here
to locate ``ci_start.exe`` on machines where it is not on ``PATH``.

Everything degrades to ``None`` off Windows, when the key/value is absent, or on
any registry error — the caller then falls back to its other discovery steps, so
this is always a best-effort hint, never a hard dependency.
"""

from __future__ import annotations

from pathlib import Path

#: The per-user cadwork environment key, relative to ``HKEY_CURRENT_USER``.
ENV_KEY = r"Software\cadwork Informatik\ENV"

#: Value naming the ``cadwork.dir`` root (note the literal dot in the name).
CADWORK_DIR_VALUE = "CADWORK.DIR"


def read_env_value(name: str) -> str | None:
    """Return ``HKCU\\...\\cadwork Informatik\\ENV\\<name>``, or ``None``.

    ``None`` is returned off Windows (no ``winreg``), when the key or value is
    missing, or when the value is not a non-empty string.
    """
    try:
        import winreg
    except ImportError:  # not Windows
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    return value if isinstance(value, str) and value else None


def find_ci_start_in_registry() -> Path | None:
    """``<CADWORK.DIR>\\ci_start.exe`` from the registry, if it exists."""
    cadwork_dir = read_env_value(CADWORK_DIR_VALUE)
    if not cadwork_dir:
        return None
    candidate = Path(cadwork_dir) / "ci_start.exe"
    return candidate if candidate.is_file() else None
