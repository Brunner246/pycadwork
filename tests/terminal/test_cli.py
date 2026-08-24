"""main() end to end with a fake launcher (no process ever spawned)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.terminal.cli import main
from tests._fakes.launcher import FakeLauncher


def test_launch_passes_translated_argv_and_returns_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
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
    err = capsys.readouterr().err
    assert "launching:" in err  # echoed to stderr, not stdout
    assert "exited with code 7" in err  # non-zero exit reported


def test_successful_launch_is_quiet_on_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "pycadwork.terminal.cli.find_ci_start", lambda explicit: Path("ci_start.exe")
    )
    code = main(["open", "house.3d"], launcher=FakeLauncher(exit_code=0))
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout stays clean
    assert "launching:" in captured.err


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


def test_open_usp_passes_env_and_quoted_command_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = FakeLauncher()
    exe = Path(r"D:\cadwork.dir\ci_start.exe")
    monkeypatch.setattr(
        "pycadwork.terminal.cli.find_ci_start", lambda explicit: exe
    )
    usp = r"D:\cadwork\userprofil_2026_charts"
    file = r"C:\Users\MichaelBrunner\Downloads\test_elements_walls.3d"
    code = main(
        ["open", file, "--exe", "exe_2026", "--usp", usp],
        launcher=launcher,
    )
    assert code == 0
    assert launcher.last_argv == [file, "/EXE=exe_2026", f"/USP={usp}"]
    assert launcher.last_env == {"CADWORK_USP": usp, "CISTART_USP": usp}
    command_line = launcher.last_command_line
    assert command_line is not None
    assert f'/USP="{usp}"' in command_line
    assert f'"{file}"' in command_line
    err = capsys.readouterr().err
    assert f'/USP="{usp}"' in err  # stderr matches what cadwork will see


def test_windows_subprocess_uses_command_string_not_list2cmdline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from pycadwork.terminal.launcher import SubprocessLauncher

    recorded: dict[str, object] = {}

    def _run(args, **kwargs):
        recorded["args"] = args
        recorded["env"] = kwargs.get("env")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("pycadwork.terminal.launcher.os.name", "nt")
    monkeypatch.setattr("pycadwork.terminal.launcher.subprocess.run", _run)
    usp = r"D:\cadwork\userprofil_2026_charts"
    command_line = (
        r'"D:\cadwork.dir\ci_start.exe" '
        r'"C:\Users\x\file.3d" '
        rf'/USP="{usp}"'
    )
    code = SubprocessLauncher().launch(
        Path(r"D:\cadwork.dir\ci_start.exe"),
        [r"C:\Users\x\file.3d", f"/USP={usp}"],
        env={"CADWORK_USP": usp},
        command_line=command_line,
    )
    assert code == 0
    assert recorded["args"] == command_line
    assert isinstance(recorded["args"], str)
    env = recorded["env"]
    assert isinstance(env, dict)
    assert env["CADWORK_USP"] == usp
