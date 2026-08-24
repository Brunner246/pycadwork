"""arg → /SLASH translation, driven through the real parser."""

from __future__ import annotations

import os
from pathlib import Path

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
            [
                "house.3d",
                "/Console",
                "/AlwaysIgnoreMultiOpenProtectDlg",
                "/PLUGIN=ExportBTL",
            ],
        ),
        (
            ["open", "m.3dc", "--workdir", r"C:\My Docs"],
            [
                "m.3dc",
                "/Console",
                "/AlwaysIgnoreMultiOpenProtectDlg",
                r"/WORKDIR=C:\My Docs",
            ],
        ),
        (
            [
                "open",
                r".\Downloads\test_elements_walls.3d",
                "--exe",
                "exe_2026",
                "--run-program",
                r"C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py",
            ],
            [
                r".\Downloads\test_elements_walls.3d",
                "/Console",
                "/AlwaysIgnoreMultiOpenProtectDlg",
                r"/RUNPROGRAM=C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py",
            ],
        ),
        (
            [
                "open",
                "house.3d",
                "--run-program",
                r"C:\my_plugins\export.py",
                "--no-gui",
            ],
            [
                "house.3d",
                "/Console",
                "/AlwaysIgnoreMultiOpenProtectDlg",
                r"/RUNPROGRAM=C:\my_plugins\export.py",
                "/NO-GUI",
            ],
        ),
        (
            ["open", "house.3d", "--plugin", "MyExport", "--no-gui"],
            [
                "house.3d",
                "/Console",
                "/AlwaysIgnoreMultiOpenProtectDlg",
                "/PLUGIN=MyExport",
                "/NO-GUI",
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
        '3d.exe "house.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg '
        '/WORKDIR="C:\\My Docs"'
    )


def _win(path: Path) -> str:
    return os.path.normpath(str(path.resolve()))


def test_usp_argv_stays_unquoted_but_command_line_quotes_drive_paths(
    tmp_path: Path,
) -> None:
    """Windows list2cmdline will not quote /USP=D:\\… — cadwork needs the quotes
    in the CreateProcess string. render_argv must stay unquoted so those quotes
    are not escaped to \\".
    """
    usp_dir = tmp_path / "userprofil_2026_charts"
    usp_dir.mkdir()
    usp = _win(usp_dir)
    file = r"C:\Users\x\test_elements_walls.3d"
    command = _command(["open", file, "--exe", "exe_2026", "--usp", usp])
    assert command.render_argv() == [
        file,
        "/Console",
        "/AlwaysIgnoreMultiOpenProtectDlg",
        f"/USP={usp}",
    ]
    display = command.render_display()
    assert f'/USP="{usp}"' in display
    assert command.render_command_line(r"D:\cadwork.dir\exe_2026\3d.x64\3d.exe") == (
        '"D:\\cadwork.dir\\exe_2026\\3d.x64\\3d.exe" '
        f'"C:\\Users\\x\\test_elements_walls.3d" '
        f'/Console /AlwaysIgnoreMultiOpenProtectDlg /USP="{usp}"'
    )
    assert command.environment() == {"CADWORK_USP": usp}


def test_usp_forward_slashes_become_backslashes(tmp_path: Path) -> None:
    usp_dir = tmp_path / "userprofil_charts"
    usp_dir.mkdir()
    (usp_dir / "3d").mkdir()
    command = _command(["open", "house.3d", "--usp", usp_dir.as_posix()])
    expected = _win(usp_dir)
    assert command.render_argv() == [
        "house.3d",
        "/Console",
        "/AlwaysIgnoreMultiOpenProtectDlg",
        f"/USP={expected}",
    ]
    if os.name == "nt":
        assert "/" not in expected
    assert command.environment() == {"CADWORK_USP": expected}


def test_usp_trailing_3d_is_stripped_to_the_profile_root(tmp_path: Path) -> None:
    usp_dir = tmp_path / "userprofil_charts"
    usp_dir.mkdir()
    three_d = usp_dir / "3d"
    three_d.mkdir()
    command = _command(["open", "house.3d", "--usp", str(three_d)])
    expected = _win(usp_dir)
    assert command.environment() == {"CADWORK_USP": expected}
    assert command.render_argv()[-1] == f"/USP={expected}"


def test_usp_missing_directory_is_value_error() -> None:
    args = build_parser().parse_args(
        ["open", "house.3d", "--usp", r"D:\no-such-userprofil-xyz"]
    )
    with pytest.raises(ValueError, match="does not exist"):
        build_command(args)


def test_catdir_sets_catalog_environment(tmp_path: Path) -> None:
    cat = tmp_path / "cadwork.cat"
    cat.mkdir()
    command = _command(["open", "house.3d", "--catdir", cat.as_posix()])
    expected = _win(cat)
    assert command.environment() == {"CADWORK_CAT": expected}


def test_exe_is_not_a_3d_slash_flag() -> None:
    command = _command(["open", "house.3d", "--exe", "exe_2026"])
    assert command.render_argv() == [
        "house.3d",
        "/Console",
        "/AlwaysIgnoreMultiOpenProtectDlg",
    ]
    assert command.executable_display == "3d.exe"


def test_display_quotes_licence_value() -> None:
    command = _command(["licence", "set", "WEB Licence:00.000.0#1;PW"])
    assert command.render_display() == (
        'ci_start.exe /SET_LICENCE="WEB Licence:00.000.0#1;PW"'
    )


def test_print_frames_require_a_2d_file() -> None:
    args = build_parser().parse_args(["print", "notes.txt", "--plotter", "A"])
    with pytest.raises(InvalidArgumentError):
        build_command(args)


def test_no_gui_requires_plugin_or_run_program() -> None:
    args = build_parser().parse_args(["open", "house.3d", "--no-gui"])
    with pytest.raises(InvalidArgumentError, match="--no-gui requires"):
        build_command(args)


def test_licence_set_rejects_malformed_value() -> None:
    args = build_parser().parse_args(["licence", "set", "garbage"])
    with pytest.raises(ValueError):
        build_command(args)
