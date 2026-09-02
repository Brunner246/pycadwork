"""The process seam — a narrow launcher port plus cadwork executable discovery.

Launching cadwork is the terminal runner's single side effect, so it goes through
a small :class:`ProcessLauncher` Protocol — the same port-and-fake shape as
:class:`pycadwork.versioning.Repository`. Production uses
:class:`SubprocessLauncher`; tests inject a recording fake and never spawn a
process. ``open`` locates ``3d.exe`` (and builds the child PATH / ``CADWORK_EXE``
overlay); Filemanager verbs still locate ``ci_start.exe``.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from pycadwork.terminal.registry import (
    CADWORK_DIR_VALUE,
    find_3d_in_registry,
    find_ci_start_in_registry,
    read_env_value,
)

#: Base name of the Filemanager launcher, as :func:`shutil.which` would find it.
EXECUTABLE_NAME = "ci_start"

#: Environment variable naming the Filemanager launcher explicitly.
EXECUTABLE_ENV_VAR = "CADWORK_CI_START"

#: Best-effort Filemanager install-location globs, newest ``exe_*`` preferred.
_COMMON_GLOBS: tuple[str, ...] = (
    r"C:\cadwork.dir\exe_*\ci_start.exe",
    r"C:\Program Files\cadwork.dir\exe_*\ci_start.exe",
)

#: Best-effort ``3d.exe`` globs, newest ``exe_*`` preferred.
_3D_GLOBS: tuple[str, ...] = (
    r"C:\cadwork.dir\exe_*\3d.x64\3d.exe",
    r"C:\Program Files\cadwork.dir\exe_*\3d.x64\3d.exe",
    r"D:\cadwork.dir\exe_*\3d.x64\3d.exe",
)

#: DLL / satellite folders prepended onto the child ``PATH``, relative to the
#: exe base (``…\exe_2026``). Missing entries are skipped.
_DLL_RELATIVE: tuple[Path, ...] = (
    Path("pclib.x64"),
    Path("pclib.x64") / "tcl" / "lib",
    Path("lxsdk.x64") / "bin",
    Path("lxsdk.x64") / "bin" / "dlls",
    Path("lxsdk.x64") / "bin" / "plugins" / "standard",
    Path("lxsdk.x64") / "bin" / "plugins" / "import",
    Path("lxsdk.x64") / "bin" / "plugins" / "export",
    Path("lxsdk.x64") / "bin" / "plugins" / "gui" / "dialogs",
    Path("lxsdk.x64") / "bin" / "plugins" / "gui" / "dockwindows",
    Path("lxsdk.x64") / "dlls",
    Path("lxsdk.x64") / "dlls" / "lexolights",
    Path("3d.x64"),
    Path("2dv.x64"),
)


class TerminalError(RuntimeError):
    """Base class for every terminal-runner failure."""


class InvalidArgumentError(TerminalError):
    """A parsed argument could not be translated to a cadwork command."""


class ExecutableNotFoundError(TerminalError):
    """``ci_start.exe`` or ``3d.exe`` could not be located to launch."""


@runtime_checkable
class ProcessLauncher(Protocol):
    """The narrow port the CLI depends on to run cadwork.

    Implementations run ``executable`` with ``argv`` and return its exit code.
    ``command_line``, when given, is the already-quoted CreateProcess string
    (cadwork parses ``/USP="D:\\…"`` from GetCommandLine, which Windows
    ``list2cmdline`` will not produce from an argv list). ``env`` is an overlay
    merged onto the current process environment.
    """

    def launch(
        self,
        executable: Path,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        command_line: str | None = None,
    ) -> int: ...


class SubprocessLauncher:
    """Launches cadwork via :func:`subprocess.run`, returning its exit code."""

    def launch(
        self,
        executable: Path,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        command_line: str | None = None,
    ) -> int:
        merged: dict[str, str] | None = None
        if env:
            merged = os.environ.copy()
            merged.update(env)
        if os.name == "nt" and command_line is not None:
            # String form: CreateProcess gets this text as-is, so cadwork sees
            # /USP="D:\…" rather than list2cmdline's unquoted /USP=D:\…
            result = subprocess.run(command_line, env=merged)
        else:
            result = subprocess.run([str(executable), *argv], env=merged)
        return result.returncode


def find_ci_start(explicit: str | None = None) -> Path:
    """Locate ``ci_start.exe``.

    Resolution order: an explicit ``--ci-start`` path, the
    :data:`EXECUTABLE_ENV_VAR` environment variable, ``ci_start`` on ``PATH``,
    the ``CADWORK.DIR`` registry value, then common install directories. Raises
    :class:`ExecutableNotFoundError` if an explicit/env path is missing or
    nothing can be found.
    """
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
        raise ExecutableNotFoundError(f"--ci-start path does not exist: {explicit}")

    env_value = os.environ.get(EXECUTABLE_ENV_VAR)
    if env_value:
        path = Path(env_value)
        if path.is_file():
            return path
        raise ExecutableNotFoundError(
            f"{EXECUTABLE_ENV_VAR} points to a missing file: {env_value}"
        )

    on_path = shutil.which(EXECUTABLE_NAME)
    if on_path:
        return Path(on_path)

    from_registry = find_ci_start_in_registry()
    if from_registry is not None:
        return from_registry

    for pattern in _COMMON_GLOBS:
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return Path(matches[0])

    raise ExecutableNotFoundError(
        "could not locate ci_start.exe — pass --ci-start PATH, set the "
        f"{EXECUTABLE_ENV_VAR} environment variable, install cadwork (so its "
        "CADWORK.DIR registry value is set), or put ci_start on PATH"
    )


def _three_d_under(base: Path) -> Path | None:
    """``3d.exe`` directly in ``base`` or in ``base\\3d.x64``."""
    direct = base / "3d.exe"
    if direct.is_file():
        return direct
    nested = base / "3d.x64" / "3d.exe"
    if nested.is_file():
        return nested
    return None


def exe_base_for(three_d: Path) -> Path:
    """The ``exe_YYYY`` folder that contains ``3d.x64\\3d.exe``."""
    parent = Path(three_d).parent
    if parent.name.lower() == "3d.x64":
        return parent.parent
    return parent


def _unique_paths(paths: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in paths:
        if not raw:
            continue
        key = os.path.normcase(raw)
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
    return out


def build_3d_runtime_env(exe_base: Path) -> dict[str, str]:
    """Child-process environment so this version's DLLs win over the registry.

    Mirrors ``launch_3d.ps1``: prepend this tree's satellite folders onto
    ``PATH``, set ``CADWORK_EXE`` / ``CADWORK_LIB``, and point TCL at this
    ``pclib`` when present. The parent process environment is not mutated.
    """
    base = Path(exe_base)
    pclib = base / "pclib.x64"
    extra = [str(base / rel) for rel in _DLL_RELATIVE if (base / rel).is_dir()]
    existing = os.environ.get("PATH", "").split(os.pathsep)
    env: dict[str, str] = {
        "CADWORK_EXE": str(base),
        "CADWORK_LIB": str(pclib),
        "PATH": os.pathsep.join(_unique_paths([*extra, *existing])),
    }
    tcl_lib = pclib / "TCL" / "LIB"
    if tcl_lib.is_dir():
        env["TCLLIBPATH"] = str(tcl_lib)
        tcl82 = tcl_lib / "TCL8.2"
        if tcl82.exists():
            env["TCL_LIBRARY"] = str(tcl82)
        tk82 = tcl_lib / "TK8.2"
        if tk82.exists():
            env["TK_LIBRARY"] = str(tk82)
    return env


def find_3d_exe(explicit: str | None = None) -> Path:
    """Locate ``3d.x64\\3d.exe``.

    Resolution order: ``--exe`` as an existing directory, ``--exe`` as a folder
    name under ``CADWORK.DIR``, the ``CADWORK_EXE`` registry value, then common
    install directories. Raises :class:`ExecutableNotFoundError` if an explicit
    path is missing or nothing can be found.
    """
    if explicit:
        stripped = explicit.strip()
        if not stripped:
            raise ExecutableNotFoundError("exe folder must be non-empty")
        path = Path(stripped).expanduser()
        if path.is_dir():
            found = _three_d_under(path)
            if found is not None:
                return found
            raise ExecutableNotFoundError(
                f"--exe path does not contain 3d.x64\\3d.exe: {explicit}"
            )
        if path.is_absolute() or len(path.parts) > 1:
            raise ExecutableNotFoundError(f"--exe path does not exist: {explicit}")
        cadwork_dir = read_env_value(CADWORK_DIR_VALUE)
        if cadwork_dir:
            named = Path(cadwork_dir) / stripped
            if named.is_dir():
                found = _three_d_under(named)
                if found is not None:
                    return found
        raise ExecutableNotFoundError(
            f"could not resolve exe folder {stripped!r} — pass a full path "
            r"such as D:\cadwork.dir\exe_2026"
        )

    from_registry = find_3d_in_registry()
    if from_registry is not None:
        return from_registry

    for pattern in _3D_GLOBS:
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return Path(matches[0])

    raise ExecutableNotFoundError(
        "could not locate 3d.exe — pass --exe DIR (the exe_YYYY folder), "
        "install cadwork (so its CADWORK_EXE registry value is set), or put "
        r"3d.x64\3d.exe under C:\cadwork.dir\exe_* or D:\cadwork.dir\exe_*"
    )
