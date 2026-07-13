"""find_ci_start resolution order and failure."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.terminal.launcher import (
    EXECUTABLE_ENV_VAR,
    ExecutableNotFoundError,
    find_ci_start,
)


@pytest.fixture(autouse=True)
def _no_ambient_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize env / PATH / registry / install-dir lookups unless opted in."""
    monkeypatch.delenv(EXECUTABLE_ENV_VAR, raising=False)
    monkeypatch.setattr("pycadwork.terminal.launcher.shutil.which", lambda name: None)
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.find_ci_start_in_registry", lambda: None
    )
    monkeypatch.setattr("pycadwork.terminal.launcher.glob.glob", lambda pattern: [])


def test_explicit_path_wins(tmp_path: Path) -> None:
    exe = tmp_path / "ci_start.exe"
    exe.write_text("")
    assert find_ci_start(str(exe)) == exe


def test_explicit_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(ExecutableNotFoundError):
        find_ci_start(str(tmp_path / "absent.exe"))


def test_env_var_used_when_no_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "ci_start.exe"
    exe.write_text("")
    monkeypatch.setenv(EXECUTABLE_ENV_VAR, str(exe))
    assert find_ci_start() == exe


def test_env_var_missing_file_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(EXECUTABLE_ENV_VAR, str(tmp_path / "absent.exe"))
    with pytest.raises(ExecutableNotFoundError):
        find_ci_start()


def test_falls_back_to_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.shutil.which",
        lambda name: r"C:\tools\ci_start.exe",
    )
    assert find_ci_start() == Path(r"C:\tools\ci_start.exe")


def test_falls_back_to_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "ci_start.exe"
    exe.write_text("")
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.find_ci_start_in_registry", lambda: exe
    )
    assert find_ci_start() == exe


def test_path_wins_over_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.shutil.which",
        lambda name: r"C:\tools\ci_start.exe",
    )
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.find_ci_start_in_registry",
        lambda: Path(r"D:\cadwork.dir\ci_start.exe"),
    )
    assert find_ci_start() == Path(r"C:\tools\ci_start.exe")


def test_falls_back_to_install_dir_glob(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.glob.glob",
        lambda pattern: [
            r"C:\cadwork.dir\exe_2025\ci_start.exe",
            r"C:\cadwork.dir\exe_2026\ci_start.exe",
        ],
    )
    # newest exe_* preferred (reverse-sorted)
    assert find_ci_start() == Path(r"C:\cadwork.dir\exe_2026\ci_start.exe")


def test_nothing_found_raises() -> None:
    with pytest.raises(ExecutableNotFoundError):
        find_ci_start()
