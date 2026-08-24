"""``CadworkCommand`` — the translated cadwork command line, ready to run.

The translation layer builds one of these from parsed CLI arguments: an ordered
tuple of ``/SLASH`` tokens plus an optional leading positional file (cadwork wants
the filename first, e.g. ``file.2d /P A``). It renders three ways:

* :meth:`render_argv` — one argv element per token, *unquoted*. Useful for tests
  and as a non-Windows ``subprocess.run`` sequence. Do not embed cadwork's
  ``KEY="VALUE"`` quotes here: Windows ``list2cmdline`` would escape them to
  ``\\"`` and cadwork would not see ``/USP="…"``.
* :meth:`render_command_line` — the CreateProcess string cadwork actually
  parses (quoted file, quoted ``KEY="VALUE"`` when the value has a space,
  backslash, or colon). :meth:`render_display` is this with
  :attr:`executable_display`.
* :attr:`env` — extra process-environment *and* HKCU ENV pairs
  (``CADWORK_USP`` …). 3d resolves the userprofile from the registry
  (``get_3d_userprofil_path``), not from ``/USP``. The CLI writes those
  registry values for the 3d session.
"""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike

#: Display name of the Filemanager launcher in the human-readable rendering.
EXECUTABLE_DISPLAY_NAME = "ci_start.exe"

#: Display name of the 3d binary for ``open --dry-run``.
THREE_D_DISPLAY_NAME = "3d.exe"

#: Characters in a value that make the display rendering wrap it in quotes.
#: cadwork's help always writes ``/USP="D:\\…"``; a drive-letter colon is enough.
_QUOTE_TRIGGERS = (" ", "\t", "\\", ":")


def _needs_quote(value: str) -> bool:
    return any(trigger in value for trigger in _QUOTE_TRIGGERS)


def _quote_if_needed(value: str) -> str:
    if _needs_quote(value):
        return f'"{value}"'
    return value


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
    env: tuple[tuple[str, str], ...] = ()
    executable_display: str = EXECUTABLE_DISPLAY_NAME

    def render_argv(self) -> list[str]:
        """The unquoted argument vector (tests / non-Windows ``subprocess.run``)."""
        argv: list[str] = []
        if self.file is not None:
            argv.append(self.file)
        argv.extend(self.tokens)
        return argv

    def render_command_line(
        self, executable: str | PathLike[str] = EXECUTABLE_DISPLAY_NAME
    ) -> str:
        """The quoted command line cadwork parses via GetCommandLine.

        ``executable`` is quoted when it contains a space, tab, backslash, or
        colon (a Windows path does). The file is always quoted, matching the
        ``"%1"`` file-association form. ``KEY=VALUE`` tokens use cadwork's
        ``KEY="VALUE"`` form when the value needs it.
        """
        parts: list[str] = [_quote_if_needed(str(executable))]
        if self.file is not None:
            parts.append(f'"{self.file}"')
        parts.extend(_display_token(token) for token in self.tokens)
        return " ".join(parts)

    def render_display(self) -> str:
        """The human-readable command line for ``--dry-run`` and errors."""
        return self.render_command_line(self.executable_display)

    def environment(self) -> dict[str, str]:
        """Process-environment overlay to apply when launching cadwork."""
        return dict(self.env)
