"""main() end to end with a fake launcher (no process ever spawned)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pycadwork.terminal.cli import main
from tests._fakes.launcher import FakeLauncher

_3D = Path(r"D:\cadwork.dir\exe_2026\3d.x64\3d.exe")
_RUNTIME = {
    "CADWORK_EXE": r"D:\cadwork.dir\exe_2026",
    "CADWORK_LIB": r"D:\cadwork.dir\exe_2026\pclib.x64",
    "PATH": r"D:\cadwork.dir\exe_2026\pclib.x64;C:\Windows\system32",
}
_OPEN_PREFIX = ["/Console", "/AlwaysIgnoreMultiOpenProtectDlg"]


def _stub_3d(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pycadwork.terminal.cli.find_3d_exe", lambda explicit: _3D
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.build_3d_runtime_env", lambda base: dict(_RUNTIME)
    )


def test_launch_passes_translated_argv_and_returns_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = FakeLauncher(exit_code=7)
    _stub_3d(monkeypatch)
    code = main(
        ["open", "house.3d", "--plugin", "ExportBTL", "--exe", "exe_2026"],
        launcher=launcher,
    )
    assert code == 7
    assert launcher.calls == [
        (_3D, ["house.3d", *_OPEN_PREFIX, "/PLUGIN=ExportBTL"])
    ]
    err = capsys.readouterr().err
    assert "launching:" in err  # echoed to stderr, not stdout
    assert "3d.exe exited with code 7" in err


def test_successful_launch_is_quiet_on_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stub_3d(monkeypatch)
    code = main(["open", "house.3d"], launcher=FakeLauncher(exit_code=0))
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout stays clean
    assert "launching:" in captured.err


def test_open_merges_runtime_env_onto_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = FakeLauncher()
    _stub_3d(monkeypatch)
    code = main(["open", "house.3d"], launcher=launcher)
    assert code == 0
    assert launcher.last_env["CADWORK_EXE"] == _RUNTIME["CADWORK_EXE"]
    assert launcher.last_env["PATH"] == _RUNTIME["PATH"]


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


def test_open_dry_run_prints_3d_exe(
    capsys: pytest.CaptureFixture[str],
) -> None:
    launcher = FakeLauncher()
    code = main(
        ["open", "house.3d", "--plugin", "ExportBTL", "--dry-run"], launcher=launcher
    )
    assert code == 0
    assert launcher.calls == []
    out = capsys.readouterr().out.strip()
    assert out == (
        '3d.exe "house.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg '
        "/PLUGIN=ExportBTL"
    )


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


def test_open_rejects_ci_start_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["open", "house.3d", "--ci-start", "ci_start.exe"], launcher=FakeLauncher())
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


def test_missing_3d_exe_returns_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pycadwork.terminal.launcher import ExecutableNotFoundError

    def _boom(explicit):
        raise ExecutableNotFoundError("no 3d")

    monkeypatch.setattr("pycadwork.terminal.cli.find_3d_exe", _boom)
    code = main(["open", "house.3d"], launcher=FakeLauncher())
    assert code == 2
    assert "no 3d" in capsys.readouterr().err


def test_filemanager_verb_still_uses_ci_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = FakeLauncher()
    ci = Path(r"D:\cadwork.dir\ci_start.exe")
    monkeypatch.setattr(
        "pycadwork.terminal.cli.find_ci_start", lambda explicit: ci
    )
    code = main(["update", "all"], launcher=launcher)
    assert code == 0
    assert launcher.calls == [(ci, ["/LIVEUPDATE=ALL"])]


def test_open_usp_passes_env_and_quoted_command_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    launcher = FakeLauncher()
    _stub_3d(monkeypatch)
    usp_dir = tmp_path / "userprofil_2026_charts"
    usp_dir.mkdir()
    usp = os.path.normpath(str(usp_dir.resolve()))
    file = r"C:\Users\MichaelBrunner\Downloads\test_elements_walls.3d"
    writes: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "pycadwork.terminal.cli.apply_env_values",
        lambda values: writes.append(tuple(values.items())),
    )
    code = main(
        ["open", file, "--exe", "exe_2026", "--usp", usp],
        launcher=launcher,
    )
    assert code == 0
    assert launcher.last_argv == [file, *_OPEN_PREFIX, f"/USP={usp}"]
    assert launcher.last_env["CADWORK_USP"] == usp
    assert launcher.last_env["CADWORK_EXE"] == _RUNTIME["CADWORK_EXE"]
    assert "CISTART_USP" not in launcher.last_env
    command_line = launcher.last_command_line
    assert command_line is not None
    assert f'/USP="{usp}"' in command_line
    assert f'"{file}"' in command_line
    err = capsys.readouterr().err
    assert f'/USP="{usp}"' in err  # stderr matches what cadwork will see
    assert writes == []  # injected launcher must not touch HKCU


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
        r'"D:\cadwork.dir\exe_2026\3d.x64\3d.exe" '
        r'"C:\Users\x\file.3d" '
        rf'/USP="{usp}"'
    )
    code = SubprocessLauncher().launch(
        Path(r"D:\cadwork.dir\exe_2026\3d.x64\3d.exe"),
        [r"C:\Users\x\file.3d", f"/USP={usp}"],
        env={"CADWORK_USP": usp, "CADWORK_EXE": r"D:\cadwork.dir\exe_2026"},
        command_line=command_line,
    )
    assert code == 0
    assert recorded["args"] == command_line
    assert isinstance(recorded["args"], str)
    env = recorded["env"]
    assert isinstance(env, dict)
    assert env["CADWORK_USP"] == usp
    assert env["CADWORK_EXE"] == r"D:\cadwork.dir\exe_2026"


def test_open_usp_live_writes_registry_before_launch_and_restores_after(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    usp_dir = tmp_path / "usp"
    usp_dir.mkdir()
    usp = os.path.normpath(str(usp_dir.resolve()))
    writes: list[dict[str, str]] = []
    restored: list[dict] = []
    launched_after_writes: list[int] = []

    class RecordingLauncher:
        def launch(self, executable, argv, *, env=None, command_line=None) -> int:
            launched_after_writes.append(len(writes))
            return 0

    _stub_3d(monkeypatch)
    monkeypatch.setattr(
        "pycadwork.terminal.cli.SubprocessLauncher", lambda: RecordingLauncher()
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.image_pids", lambda name: frozenset()
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.read_env_value", lambda name: "OLD"
    )

    def _apply(values):
        writes.append(dict(values))

    monkeypatch.setattr("pycadwork.terminal.cli.apply_env_values", _apply)
    monkeypatch.setattr(
        "pycadwork.terminal.cli.restore_values",
        lambda previous: restored.append(dict(previous)),
    )

    code = main(["open", "house.3d", "--usp", str(usp_dir)])
    assert code == 0
    assert launched_after_writes == [1]  # pin happens before launch
    assert writes == [{"CADWORK_USP": usp}]
    assert restored == [{"CADWORK_USP": "OLD"}]


def test_open_errors_if_3d_already_running(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    launched: list[object] = []

    class RecordingLauncher:
        def launch(self, *args, **kwargs) -> int:
            launched.append(1)
            return 0

    _stub_3d(monkeypatch)
    monkeypatch.setattr(
        "pycadwork.terminal.cli.SubprocessLauncher", lambda: RecordingLauncher()
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.image_pids", lambda name: frozenset({99})
    )
    applied: list[object] = []
    monkeypatch.setattr(
        "pycadwork.terminal.cli.apply_env_values", lambda values: applied.append(values)
    )

    code = main(["open", "house.3d"])
    assert code == 2
    assert launched == []
    assert applied == []
    assert "already running" in capsys.readouterr().err


def test_open_usp_errors_if_registry_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    from pycadwork.terminal.registry import RegistryWriteError

    usp_dir = tmp_path / "usp"
    usp_dir.mkdir()
    launched: list[object] = []
    restored: list[dict] = []

    class RecordingLauncher:
        def launch(self, *args, **kwargs) -> int:
            launched.append(1)
            return 0

    _stub_3d(monkeypatch)
    monkeypatch.setattr(
        "pycadwork.terminal.cli.SubprocessLauncher", lambda: RecordingLauncher()
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.image_pids", lambda name: frozenset()
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.read_env_value", lambda name: None
    )
    monkeypatch.setattr(
        "pycadwork.terminal.cli.restore_values",
        lambda previous: restored.append(dict(previous)),
    )

    def _boom(values):
        raise RegistryWriteError("could not write HKCU cadwork ENV values: CADWORK_USP")

    monkeypatch.setattr("pycadwork.terminal.cli.apply_env_values", _boom)

    code = main(["open", "house.3d", "--usp", str(usp_dir)])
    assert code == 2
    assert launched == []
    assert restored == [{"CADWORK_USP": None}]
    assert "could not write" in capsys.readouterr().err
