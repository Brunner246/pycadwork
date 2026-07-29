"""The ``cadwork`` CLI — argparse front end over cadwork's ``/SLASH`` command line.

``build_parser`` wires the curated subcommands (``open``, ``install``,
``uninstall``, ``licence``, ``update``, ``print``); ``main`` parses, translates
via :func:`pycadwork.terminal.translation.build_command`, and either prints the
command line (``--dry-run``) or launches ``ci_start.exe`` through an injected
:class:`~pycadwork.terminal.launcher.ProcessLauncher`. The ``launcher`` parameter
is the test seam — production defaults to :class:`SubprocessLauncher`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pycadwork.terminal.launcher import (
    ExecutableNotFoundError,
    InvalidArgumentError,
    ProcessLauncher,
    SubprocessLauncher,
    find_ci_start,
)
from pycadwork.terminal.translation import build_command
from pycadwork.terminal.values import UPDATE_CHOICES, USER_CHOICES


def _common_options() -> argparse.ArgumentParser:
    """Options shared by every verb (placed after the verb on the line)."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--ci-start",
        metavar="PATH",
        help="path to ci_start.exe (else CADWORK_CI_START, PATH, or common dirs)",
    )
    common.add_argument(
        "--log-file",
        metavar="PATH",
        help="write cadwork installation logging to this file (/LogFile)",
    )
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="print the cadwork command line instead of launching it",
    )
    return common


def build_parser() -> argparse.ArgumentParser:
    """Construct the full ``cadwork`` argument parser."""
    common = _common_options()
    parser = argparse.ArgumentParser(
        prog="cadwork",
        description="Modern CLI wrapper over cadwork's ci_start.exe command line.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    _add_open(subparsers, common)
    _add_install(subparsers, common)
    _add_uninstall(subparsers, common)
    _add_licence(subparsers, common)
    _add_update(subparsers, common)
    _add_print(subparsers, common)

    return parser


def _add_open(subparsers, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "open",
        parents=[common],
        help="open a model file, optionally running a plugin",
    )
    p.add_argument("file", help="the model file to open (.3d / .3dc)")
    p.add_argument("--exe", metavar="DIR", help="cadwork version folder (/EXE)")
    p.add_argument(
        "--plugin",
        metavar="NAME",
        help="plugin folder name in API.x64 to run after open (/PLUGIN)",
    )
    p.add_argument(
        "--run-program",
        metavar="PATH",
        help=(
            "path to a .py or .dll plugin to run after open from any directory "
            "(/RUNPROGRAM); does not need to be registered in API.x64"
        ),
    )
    p.add_argument(
        "--no-gui",
        action="store_true",
        help=(
            "run headless with no GUI window (/NO-GUI); requires --plugin or "
            "--run-program"
        ),
    )
    p.add_argument("--usp", metavar="DIR", help="userprofile folder (/USP)")
    p.add_argument("--catdir", metavar="DIR", help="catalog folder (/CATDIR)")
    p.add_argument("--workdir", metavar="DIR", help="projects folder (/WORKDIR)")


def _add_install(subparsers, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "install", parents=[common], help="install cadwork on this PC"
    )
    p.add_argument("--silent", action="store_true", help="suppress errors (/SILENT)")
    p.add_argument(
        "--close", action="store_true", help="close ci_start after install (/CLOSE)"
    )
    p.add_argument(
        "--desktop-shortcut",
        action="store_true",
        help="create a desktop shortcut (/SHORTCUT_ON_DESKTOP)",
    )
    p.add_argument(
        "--target-dir", metavar="DIR", help="copy folders to this dir (/TargetDir)"
    )
    p.add_argument(
        "--corporate",
        action="store_true",
        help="skip LOCAL_MACHINE registry entries (/MSI_Corporate)",
    )
    p.add_argument("--user", choices=USER_CHOICES, help="set the user type (/USER_*)")
    p.add_argument(
        "--pdfxchange",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="install the PDF Xchange printer driver (/[NO_]INSTALL_PDFXCHANGE)",
    )
    p.add_argument(
        "--no-shellnew",
        action="store_true",
        help="skip right-click shortcuts (/NO_INSTALL_SHELLNEW)",
    )
    p.add_argument(
        "--no-icacls",
        action="store_true",
        help="do not change update-folder access (/NO_ICACLS)",
    )


def _add_uninstall(subparsers, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "uninstall", parents=[common], help="uninstall cadwork on this PC"
    )
    p.add_argument("--silent", action="store_true", help="suppress errors (/SILENT)")
    p.add_argument(
        "--purge",
        action="store_true",
        help="delete cadwork.dir with no confirmation (/PURGE)",
    )
    p.add_argument(
        "--close", action="store_true", help="close ci_start afterwards (/CLOSE)"
    )


def _add_licence(subparsers, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "licence", parents=[common], help="query or set the default licence"
    )
    actions = p.add_subparsers(dest="licence_action", metavar="<action>", required=True)
    actions.add_parser(
        "get", parents=[common], help="print the default licence (/GET_LICENCE)"
    )
    set_p = actions.add_parser(
        "set", parents=[common], help="set the default licence (/SET_LICENCE)"
    )
    set_p.add_argument(
        "value", help='licence string, e.g. "WEB Licence:00.000.0#1;PASSWORD"'
    )
    actions.add_parser(
        "no-network",
        parents=[common],
        help="use the USB-stick licence (/NO_NETWORK_LICENCE)",
    )


def _add_update(subparsers, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "update", parents=[common], help="live-update installed modules"
    )
    p.add_argument(
        "target",
        nargs="?",
        choices=UPDATE_CHOICES,
        default="all",
        help="what to update (default: all)",
    )
    p.add_argument(
        "--silent", action="store_true", help="update automatically (/SILENT)"
    )
    p.add_argument(
        "--maximized", action="store_true", help="always show the dialog (/MAXIMIZED)"
    )
    p.add_argument(
        "--no-cancel", action="store_true", help="hide the Cancel button (/NoCancel)"
    )
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="use local ZIP files (/SKIP_DOWNLOAD)",
    )


def _add_print(subparsers, common: argparse.ArgumentParser) -> None:
    p = subparsers.add_parser(
        "print", parents=[common], help="print a .2d (frames) or .txt file"
    )
    p.add_argument("file", help="the file to print")
    target = p.add_mutually_exclusive_group()
    target.add_argument(
        "--plotter", metavar="FRAMES", help='plotter frames: "A" or "1-2;5;7" (/P)'
    )
    target.add_argument(
        "--laser", metavar="FRAMES", help='laser frames: "A", "PDF", or a spec (/L)'
    )


def main(
    argv: Sequence[str] | None = None,
    launcher: ProcessLauncher | None = None,
) -> int:
    """Parse ``argv``, translate, and launch cadwork (or print with ``--dry-run``).

    On a real launch the resolved command line is echoed to ``stderr`` (so
    ``stdout`` stays clean for piping) and a non-zero exit code is reported.
    Returns cadwork's exit code, ``0`` for a dry run, or ``2`` on a usage error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 2

    try:
        command = build_command(args)
    except (ValueError, InvalidArgumentError) as exc:
        parser.error(str(exc))  # raises SystemExit(2)

    if args.dry_run:
        print(command.render_display())
        return 0

    try:
        executable = find_ci_start(args.ci_start)
    except ExecutableNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    launcher = launcher or SubprocessLauncher()
    argv_out = command.render_argv()
    print(f"launching: {executable} {' '.join(argv_out)}", file=sys.stderr)
    exit_code = launcher.launch(executable, argv_out)
    if exit_code != 0:
        print(f"ci_start.exe exited with code {exit_code}", file=sys.stderr)
    return exit_code
