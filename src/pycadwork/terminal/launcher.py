"""The process seam — a narrow launcher port plus ci_start.exe discovery.

Launching cadwork is the terminal runner's single side effect, so it goes through
a small :class:`ProcessLauncher` Protocol — the same port-and-fake shape as
:class:`pycadwork.versioning.Repository`. Production uses
:class:`SubprocessLauncher`; tests inject a recording fake and never spawn a
process. Executable discovery mirrors the only other executable-wrapping code in
the package (``pycadwork.versioning._git``), which locates ``git`` with
:func:`shutil.which`.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from pycadwork.terminal.registry import find_ci_start_in_registry

#: Base name of the cadwork launcher, as :func:`shutil.which` would find it.
EXECUTABLE_NAME = "ci_start"

#: Environment variable naming the launcher explicitly.
EXECUTABLE_ENV_VAR = "CADWORK_CI_START"

#: Best-effort install-location globs, newest ``exe_*`` preferred.
_COMMON_GLOBS: tuple[str, ...] = (
    r"C:\cadwork.dir\exe_*\ci_start.exe",
    r"C:\Program Files\cadwork.dir\exe_*\ci_start.exe",
)


class TerminalError(RuntimeError):
    """Base class for every terminal-runner failure."""


class InvalidArgumentError(TerminalError):
    """A parsed argument could not be translated to a cadwork command."""


class ExecutableNotFoundError(TerminalError):
    """``ci_start.exe`` could not be located to launch."""


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
