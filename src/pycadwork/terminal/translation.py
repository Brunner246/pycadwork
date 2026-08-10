"""``build_command`` — the arg → ``/SLASH`` token mapping, per subcommand.

Each verb has a small builder that turns the parsed ``argparse`` namespace into a
:class:`~pycadwork.terminal.command.CadworkCommand`. Value-carrying options go
through the value objects in :mod:`pycadwork.terminal.values` so malformed input
raises :class:`ValueError` here (the CLI converts that to an argparse error).
Global options (``--log-file``) are appended to every command.
"""

from __future__ import annotations

import argparse

from pycadwork.terminal.command import CadworkCommand
from pycadwork.terminal.launcher import InvalidArgumentError
from pycadwork.terminal.values import (
    FrameSelection,
    Licence,
    UpdateTarget,
    UserType,
)


def build_command(args: argparse.Namespace) -> CadworkCommand:
    """Translate a parsed namespace into a :class:`CadworkCommand`."""
    builders = {
        "open": _open,
        "install": _install,
        "uninstall": _uninstall,
        "licence": _licence,
        "update": _update,
        "print": _print,
    }
    try:
        builder = builders[args.command]
    except KeyError:
        raise InvalidArgumentError(f"unknown command: {args.command!r}") from None
    return builder(args)


def _globals(args: argparse.Namespace) -> tuple[str, ...]:
    tokens: list[str] = []
    if getattr(args, "log_file", None):
        tokens.append(f"/LogFile={args.log_file}")
    return tuple(tokens)


def _open(args: argparse.Namespace) -> CadworkCommand:
    tokens: list[str] = []
    if args.exe:
        tokens.append(f"/EXE={args.exe}")
    if args.plugin:
        tokens.append(f"/PLUGIN={args.plugin}")
    if args.run_program:
        tokens.append(f"/RUNPROGRAM={args.run_program}")
    if args.no_gui:
        if not (args.plugin or args.run_program):
            raise InvalidArgumentError(
                "--no-gui requires --plugin or --run-program "
                "(cadwork /NO-GUI only applies when running a plugin)"
            )
        tokens.append("/NO-GUI")
    if args.usp:
        tokens.append(f"/USP={args.usp}")
    if args.catdir:
        tokens.append(f"/CATDIR={args.catdir}")
    if args.workdir:
        tokens.append(f"/WORKDIR={args.workdir}")
    return CadworkCommand(tokens=tuple(tokens) + _globals(args), file=args.file)


def _install(args: argparse.Namespace) -> CadworkCommand:
    tokens = ["/INSTALL"]
    if args.silent:
        tokens.append("/SILENT")
    if args.close:
        tokens.append("/CLOSE")
    if args.desktop_shortcut:
        tokens.append("/SHORTCUT_ON_DESKTOP")
    if args.target_dir:
        tokens.append(f"/TargetDir={args.target_dir}")
    if args.corporate:
        tokens.append("/MSI_Corporate")
    if args.user:
        tokens.append(UserType.from_choice(args.user).value)
    if args.pdfxchange is True:
        tokens.append("/INSTALL_PDFXCHANGE")
    elif args.pdfxchange is False:
        tokens.append("/NO_INSTALL_PDFXCHANGE")
    if args.no_shellnew:
        tokens.append("/NO_INSTALL_SHELLNEW")
    if args.no_icacls:
        tokens.append("/NO_ICACLS")
    return CadworkCommand(tokens=tuple(tokens) + _globals(args))


def _uninstall(args: argparse.Namespace) -> CadworkCommand:
    tokens = ["/UNINSTALL"]
    if args.silent:
        tokens.append("/SILENT")
    if args.purge:
        tokens.append("/PURGE")
    if args.close:
        tokens.append("/CLOSE")
    return CadworkCommand(tokens=tuple(tokens) + _globals(args))


def _licence(args: argparse.Namespace) -> CadworkCommand:
    action = args.licence_action
    if action == "get":
        tokens = ["/GET_LICENCE"]
    elif action == "set":
        tokens = [f"/SET_LICENCE={Licence(args.value)}"]
    elif action == "no-network":
        tokens = ["/NO_NETWORK_LICENCE"]
    else:  # pragma: no cover - argparse guards the choices
        raise InvalidArgumentError(f"unknown licence action: {action!r}")
    return CadworkCommand(tokens=tuple(tokens) + _globals(args))


def _update(args: argparse.Namespace) -> CadworkCommand:
    tokens = [f"/LIVEUPDATE={UpdateTarget.from_choice(args.target).value}"]
    if args.silent:
        tokens.append("/SILENT")
    if args.maximized:
        tokens.append("/MAXIMIZED")
    if args.no_cancel:
        tokens.append("/NoCancel")
    if args.skip_download:
        tokens.append("/SKIP_DOWNLOAD")
    return CadworkCommand(tokens=tuple(tokens) + _globals(args))


def _print(args: argparse.Namespace) -> CadworkCommand:
    tokens: list[str]
    if args.plotter is not None:
        _require_2d(args.file, "--plotter")
        tokens = ["/P", str(FrameSelection(args.plotter))]
    elif args.laser is not None:
        _require_2d(args.file, "--laser")
        if args.laser.strip().upper() == "PDF":
            tokens = ["/L", "PDF"]
        else:
            tokens = ["/L", str(FrameSelection(args.laser))]
    else:
        tokens = ["/PRINT"]
    return CadworkCommand(tokens=tuple(tokens) + _globals(args), file=args.file)


def _require_2d(file: str, option: str) -> None:
    if not file.lower().endswith(".2d"):
        raise InvalidArgumentError(
            f"{option} prints plotter/laser frames from a .2d file; got {file!r}"
        )
