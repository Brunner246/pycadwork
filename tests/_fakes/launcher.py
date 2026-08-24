"""In-memory fake of the :class:`~pycadwork.terminal.ProcessLauncher` Protocol.

Records the ``(executable, argv)`` of every launch and returns a settable exit
code, so the CLI's launch path is testable with no ``ci_start.exe`` and no spawned
process. Also records the environment overlay and quoted command-line string.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FakeLauncher:
    """Records launches instead of spawning a process."""

    exit_code: int = 0
    calls: list[tuple[Path, list[str]]] = field(default_factory=list)
    envs: list[dict[str, str]] = field(default_factory=list)
    command_lines: list[str | None] = field(default_factory=list)

    def launch(
        self,
        executable: Path,
        argv: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        command_line: str | None = None,
    ) -> int:
        self.calls.append((executable, list(argv)))
        self.envs.append(dict(env) if env else {})
        self.command_lines.append(command_line)
        return self.exit_code

    @property
    def last_argv(self) -> list[str]:
        return self.calls[-1][1]

    @property
    def last_env(self) -> dict[str, str]:
        return self.envs[-1]

    @property
    def last_command_line(self) -> str | None:
        return self.command_lines[-1]
