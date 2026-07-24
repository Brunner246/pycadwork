"""``CadworkCommand`` — the translated cadwork command line, ready to run.

The translation layer builds one of these from parsed CLI arguments: an ordered
tuple of ``/SLASH`` tokens plus an optional leading positional file (cadwork wants
the filename first, e.g. ``file.2d /P A``). It renders two ways:

* :meth:`render_argv` — one argv element per token, *unquoted*. This is what goes
  to :func:`subprocess.run`, which applies the OS-correct quoting itself, so a
  value with spaces (``/USP=C:\\My Documents``) reaches cadwork as one argument.
* :meth:`render_display` — the human-readable line for ``--dry-run`` and error
  messages, quoting the file and any ``KEY=VALUE`` value that needs it, matching
  how the cadwork docs write these commands (``/SET_LICENCE="..."``).
"""

from __future__ import annotations

from dataclasses import dataclass

#: Display name of the cadwork launcher in the human-readable rendering.
EXECUTABLE_DISPLAY_NAME = "ci_start.exe"

#: Characters in a value that make the display rendering wrap it in quotes.
_QUOTE_TRIGGERS = (" ", "\t", "\\", ":")


def _needs_quote(value: str) -> bool:
    return any(trigger in value for trigger in _QUOTE_TRIGGERS)


def _display_token(token: str) -> str:
    key, sep, value = token.partition("=")
    if sep and _needs_quote(value):
        return f'{key}="{value}"'
    return token


@dataclass(frozen=True, slots=True)
class CadworkCommand:
    """An ordered cadwork command line: an optional file then ``/SLASH`` tokens."""

    tokens: tuple[str, ...] = ()
    file: str | None = None

    def render_argv(self) -> list[str]:
        """The argument vector for :func:`subprocess.run` (no manual quoting)."""
        argv: list[str] = []
        if self.file is not None:
            argv.append(self.file)
        argv.extend(self.tokens)
        return argv

    def render_display(self) -> str:
        """The human-readable command line for ``--dry-run`` and errors."""
        parts: list[str] = [EXECUTABLE_DISPLAY_NAME]
        if self.file is not None:
            parts.append(f'"{self.file}"')
        parts.extend(_display_token(token) for token in self.tokens)
        return " ".join(parts)
