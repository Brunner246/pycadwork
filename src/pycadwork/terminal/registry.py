"""cadwork's per-user ENV registry block (Windows only).

cadwork records its installed paths under
``HKEY_CURRENT_USER\\Software\\cadwork Informatik\\ENV`` — ``CADWORK.DIR`` (the
``cadwork.dir`` root that holds ``ci_start.exe``), plus the EXE / userprofile /
catalog / projects folders. The terminal runner reads ``CADWORK.DIR`` and
``CADWORK_EXE`` from here to locate ``ci_start.exe`` / ``3d.exe`` on machines
where they are not on ``PATH``.

3d resolves the userprofile from this registry block (``CADWORK_USP``), not from
the process environment and not from ``/USP`` on a file-open command line. A
live ``open --usp`` therefore has to write those values for the duration of
the 3d process, then put them back.

Everything degrades to ``None`` / no-op off Windows, when the key/value is
absent, or on any registry error — the caller then falls back to its other
discovery steps, so this is always a best-effort hint, never a hard dependency.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

#: The per-user cadwork environment key, relative to ``HKEY_CURRENT_USER``.
ENV_KEY = r"Software\cadwork Informatik\ENV"

#: Value naming the ``cadwork.dir`` root (note the literal dot in the name).
CADWORK_DIR_VALUE = "CADWORK.DIR"

#: Value naming the installed exe folder (the parent of ``3d.x64``).
CADWORK_EXE_VALUE = "CADWORK_EXE"


class RegistryWriteError(RuntimeError):
    """HKCU cadwork ENV values could not be written."""


def _winreg():
    try:
        import winreg
    except ImportError:
        return None
    return winreg


def read_env_value(name: str) -> str | None:
    """Return ``HKCU\\...\\cadwork Informatik\\ENV\\<name>``, or ``None``.

    ``None`` is returned off Windows (no ``winreg``), when the key or value is
    missing, or when the value is not a non-empty string.
    """
    winreg = _winreg()
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENV_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    return value if isinstance(value, str) and value else None


def write_env_value(name: str, value: str) -> bool:
    """Set ``HKCU\\...\\ENV\\<name>`` to ``value``. Returns False if it cannot."""
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, ENV_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    except OSError:
        return False
    return True


def apply_env_values(values: Mapping[str, str]) -> None:
    """Write every pair in ``values``. Raises if any write fails."""
    failed = [
        name for name, value in values.items() if not write_env_value(name, value)
    ]
    if failed:
        raise RegistryWriteError(
            "could not write HKCU cadwork ENV values: " + ", ".join(failed)
        )


def delete_env_value(name: str) -> bool:
    """Delete ``HKCU\\...\\ENV\\<name>``. Returns False if it cannot."""
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, ENV_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, name)
    except OSError:
        return False
    return True


def image_pids(image_name: str) -> frozenset[int]:
    """PIDs of running processes named ``image_name`` (empty off Windows)."""
    if os.name != "nt":
        return frozenset()
    try:
        out = subprocess.check_output(
            [
                "tasklist",
                "/FI",
                f"IMAGENAME eq {image_name}",
                "/FO",
                "CSV",
                "/NH",
            ],
            text=True,
            errors="replace",
        )
    except OSError:
        return frozenset()
    pids: set[int] = set()
    for line in out.splitlines():
        parts = line.split(",")
        if len(parts) < 2:
            continue
        pid_s = parts[1].strip().strip('"')
        if pid_s.isdigit():
            pids.add(int(pid_s))
    return frozenset(pids)


#: ``OpenProcess`` access right that suffices for ``QueryFullProcessImageNameW``.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def image_path(pid: int) -> Path | None:
    """Full executable path of ``pid`` (``None`` off Windows or on any failure)."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                return None
        finally:
            kernel32.CloseHandle(handle)
    except OSError, AttributeError:
        return None
    return Path(buffer.value) if buffer.value else None


def _path_key(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.normpath(os.fspath(path)))


def pids_running(executable: Path) -> frozenset[int]:
    """PIDs of running processes whose image is exactly ``executable``.

    A PID whose path cannot be read is included — conservatively, it *might* be
    this executable (e.g. an elevated process we cannot query).
    """
    wanted = _path_key(executable)
    matches: set[int] = set()
    for pid in image_pids(Path(executable).name):
        path = image_path(pid)
        if path is None or _path_key(path) == wanted:
            matches.add(pid)
    return frozenset(matches)


def restore_values(previous: Mapping[str, str | None]) -> None:
    """Write ``previous`` back; ``None`` values are deleted."""
    for name, old in previous.items():
        if old is None:
            delete_env_value(name)
        else:
            write_env_value(name, old)


@contextmanager
def override_env_values(values: Mapping[str, str]) -> Iterator[None]:
    """Temporarily write ``values`` into the cadwork ENV key, then restore.

    Missing names are deleted on the way out. Failures to write are ignored so a
    launch still proceeds (3d will then keep the previous profile).
    """
    previous = {name: read_env_value(name) for name in values}
    try:
        for name, value in values.items():
            write_env_value(name, value)
        yield
    finally:
        restore_values(previous)


def find_ci_start_in_registry() -> Path | None:
    """``<CADWORK.DIR>\\ci_start.exe`` from the registry, if it exists."""
    cadwork_dir = read_env_value(CADWORK_DIR_VALUE)
    if not cadwork_dir:
        return None
    candidate = Path(cadwork_dir) / "ci_start.exe"
    return candidate if candidate.is_file() else None


def find_3d_in_registry() -> Path | None:
    """``<CADWORK_EXE>\\3d.x64\\3d.exe`` from the registry, if it exists."""
    exe_base = read_env_value(CADWORK_EXE_VALUE)
    if not exe_base:
        return None
    candidate = Path(exe_base) / "3d.x64" / "3d.exe"
    return candidate if candidate.is_file() else None
