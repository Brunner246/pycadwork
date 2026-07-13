"""arg → /SLASH translation, driven through the real parser."""

from __future__ import annotations

import pytest

from pycadwork.terminal.cli import build_parser
from pycadwork.terminal.launcher import InvalidArgumentError
from pycadwork.terminal.translation import build_command


def _command(argv: list[str]):
    args = build_parser().parse_args(argv)
    return build_command(args)


@pytest.mark.parametrize(
    ("argv", "expected_argv"),
    [
        (
            ["open", "house.3d", "--plugin", "ExportBTL", "--exe", "exe_2026"],
            ["house.3d", "/EXE=exe_2026", "/PLUGIN=ExportBTL"],
        ),
        (
            ["open", "m.3dc", "--usp", r"\\SRV\up", "--workdir", r"C:\My Docs"],
            ["m.3dc", r"/USP=\\SRV\up", r"/WORKDIR=C:\My Docs"],
        ),
        (
            [
                "open",
                r".\Downloads\test_elements_walls.3d",
                "--exe",
                r"D:\cadwork.dir\exe_2026",
                "--run-program",
                r"C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py",
            ],
            [
                r".\Downloads\test_elements_walls.3d",
                r"/EXE=D:\cadwork.dir\exe_2026",
                r"/RUNPROGRAM=C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py",
            ],
        ),
        (
            ["install", "--silent", "--desktop-shortcut"],
            ["/INSTALL", "/SILENT", "/SHORTCUT_ON_DESKTOP"],
        ),
        (
            ["install", "--user", "holz", "--no-pdfxchange", "--corporate"],
            ["/INSTALL", "/MSI_Corporate", "/USER_HOLZ", "/NO_INSTALL_PDFXCHANGE"],
        ),
        (
            ["install", "--pdfxchange"],
            ["/INSTALL", "/INSTALL_PDFXCHANGE"],
        ),
        (
            ["uninstall", "--silent", "--purge", "--close"],
            ["/UNINSTALL", "/SILENT", "/PURGE", "/CLOSE"],
        ),
        (["licence", "get"], ["/GET_LICENCE"]),
        (
            ["licence", "set", "WEB Licence:00.000.0#1;PW"],
            ["/SET_LICENCE=WEB Licence:00.000.0#1;PW"],
        ),
        (["licence", "no-network"], ["/NO_NETWORK_LICENCE"]),
        (["update"], ["/LIVEUPDATE=ALL"]),
        (["update", "2d", "--silent"], ["/LIVEUPDATE=2D", "/SILENT"]),
        (
            ["update", "all-force", "--maximized", "--no-cancel", "--skip-download"],
            ["/LIVEUPDATE=ALL+", "/MAXIMIZED", "/NoCancel", "/SKIP_DOWNLOAD"],
        ),
        (["print", "plan.2d", "--plotter", "A"], ["plan.2d", "/P", "A"]),
        (["print", "plan.2d", "--plotter", "1-2;5;7"], ["plan.2d", "/P", "1-2;5;7"]),
        (["print", "plan.2d", "--laser", "PDF"], ["plan.2d", "/L", "PDF"]),
        (["print", "notes.txt"], ["notes.txt", "/PRINT"]),
    ],
)
def test_render_argv(argv: list[str], expected_argv: list[str]) -> None:
    assert _command(argv).render_argv() == expected_argv


def test_log_file_is_appended_globally() -> None:
    argv = ["install", "--silent", "--log-file", r"C:\log.txt"]
    assert _command(argv).render_argv() == [
        "/INSTALL",
        "/SILENT",
        r"/LogFile=C:\log.txt",
    ]


def test_dry_run_display_quotes_file_and_pathy_values() -> None:
    command = _command(
        ["open", "house.3d", "--exe", "exe_2026", "--workdir", r"C:\My Docs"]
    )
    assert command.render_display() == (
        'ci_start.exe "house.3d" /EXE=exe_2026 /WORKDIR="C:\\My Docs"'
    )


def test_display_quotes_licence_value() -> None:
    command = _command(["licence", "set", "WEB Licence:00.000.0#1;PW"])
    assert command.render_display() == (
        'ci_start.exe /SET_LICENCE="WEB Licence:00.000.0#1;PW"'
    )


def test_print_frames_require_a_2d_file() -> None:
    args = build_parser().parse_args(["print", "notes.txt", "--plotter", "A"])
    with pytest.raises(InvalidArgumentError):
        build_command(args)


def test_licence_set_rejects_malformed_value() -> None:
    args = build_parser().parse_args(["licence", "set", "garbage"])
    with pytest.raises(ValueError):
        build_command(args)
