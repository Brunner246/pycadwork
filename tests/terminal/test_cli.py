"""main() end to end with a fake launcher (no process ever spawned)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.terminal.cli import main
from tests._fakes.launcher import FakeLauncher


def test_launch_passes_translated_argv_and_returns_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = FakeLauncher(exit_code=7)
    monkeypatch.setattr(
        "pycadwork.terminal.cli.find_ci_start", lambda explicit: Path("ci_start.exe")
    )
    code = main(
        ["open", "house.3d", "--plugin", "ExportBTL", "--exe", "exe_2026"],
        launcher=launcher,
    )
    assert code == 7
    assert launcher.calls == [
        (Path("ci_start.exe"), ["house.3d", "/EXE=exe_2026", "/PLUGIN=ExportBTL"])
    ]


def test_dry_run_prints_and_does_not_launch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    launcher = FakeLauncher()
    code = main(
        ["install", "--silent", "--desktop-shortcut", "--dry-run"], launcher=launcher
    )
    assert code == 0
    assert launcher.calls == []
    out = capsys.readouterr().out.strip()
    assert out == "ci_start.exe /INSTALL /SILENT /SHORTCUT_ON_DESKTOP"


def test_no_command_prints_help_and_returns_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main([], launcher=FakeLauncher())
    assert code == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_invalid_value_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["licence", "set", "garbage"], launcher=FakeLauncher())
    assert exc.value.code == 2
    assert "licence" in capsys.readouterr().err.lower()


def test_unknown_option_exits_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["install", "--nope"], launcher=FakeLauncher())
    assert exc.value.code == 2


def test_missing_executable_returns_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pycadwork.terminal.launcher import ExecutableNotFoundError

    def _boom(explicit):
        raise ExecutableNotFoundError("nope")

    monkeypatch.setattr("pycadwork.terminal.cli.find_ci_start", _boom)
    code = main(["update"], launcher=FakeLauncher())
    assert code == 2
    assert "nope" in capsys.readouterr().err
