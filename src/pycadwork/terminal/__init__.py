"""pycadwork.terminal — a modern CLI wrapper over cadwork's ``/SLASH`` args.

cadwork's ``ci_start.exe`` takes an uncommon slash-based command line
(``/INSTALL /SILENT``, ``/SET_LICENCE="..."``, ``file.2d /P A``). This package
exposes a state-of-the-art ``cadwork <verb> [--options]`` CLI that parses modern
arguments, translates them into the exact ``/SLASH`` tokens, and launches cadwork
(``--dry-run`` prints the line instead)::

    cadwork open house.3d --plugin ExportBTL --exe exe_2026
    cadwork install --silent --desktop-shortcut --dry-run

It runs on a *host* Python that launches cadwork — it imports no cwapi3d and is
independent of the cadwork adapter seam. The programmatic surface below lets other
tools build/inspect a command without spawning a process.
"""

from __future__ import annotations

from pycadwork.terminal.cli import build_parser, main
from pycadwork.terminal.command import CadworkCommand
from pycadwork.terminal.launcher import (
    ExecutableNotFoundError,
    InvalidArgumentError,
    ProcessLauncher,
    SubprocessLauncher,
    TerminalError,
    find_ci_start,
)
from pycadwork.terminal.registry import find_ci_start_in_registry, read_env_value
from pycadwork.terminal.translation import build_command
from pycadwork.terminal.values import (
    FrameSelection,
    Licence,
    UpdateTarget,
    UserType,
)

__all__ = [
    "CadworkCommand",
    "ExecutableNotFoundError",
    "FrameSelection",
    "InvalidArgumentError",
    "Licence",
    "ProcessLauncher",
    "SubprocessLauncher",
    "TerminalError",
    "UpdateTarget",
    "UserType",
    "build_command",
    "build_parser",
    "find_ci_start",
    "find_ci_start_in_registry",
    "main",
    "read_env_value",
]
