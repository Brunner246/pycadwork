"""In-memory fake of the :class:`~pycadwork.terminal.ProcessLauncher` Protocol.

Records the ``(executable, argv)`` of every launch and returns a settable exit
code, so the CLI's launch path is testable with no ``ci_start.exe`` and no spawned
process.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FakeLauncher:
    """Records launches instead of spawning a process."""

    exit_code: int = 0
    calls: list[tuple[Path, list[str]]] = field(default_factory=list)

    def launch(self, executable: Path, argv: Sequence[str]) -> int:
        self.calls.append((executable, list(argv)))
        return self.exit_code

    @property
    def last_argv(self) -> list[str]:
        return self.calls[-1][1]
