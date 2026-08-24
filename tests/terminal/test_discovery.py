"""find_ci_start / find_3d_exe resolution order and failure."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.terminal.launcher import (
    EXECUTABLE_ENV_VAR,
    ExecutableNotFoundError,
    exe_base_for,
    find_3d_exe,
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
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.find_3d_in_registry", lambda: None
    )
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.read_env_value", lambda name: None
    )
    monkeypatch.setattr("pycadwork.terminal.launcher.glob.glob", lambda pattern: [])


def _plant_3d(base: Path) -> Path:
    exe = base / "3d.x64" / "3d.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_text("")
    return exe


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


def test_find_3d_explicit_directory(tmp_path: Path) -> None:
    base = tmp_path / "exe_2026"
    exe = _plant_3d(base)
    assert find_3d_exe(str(base)) == exe
    assert exe_base_for(exe) == base


def test_find_3d_explicit_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(ExecutableNotFoundError, match="does not exist"):
        find_3d_exe(str(tmp_path / "absent"))


def test_find_3d_explicit_dir_without_binary_raises(tmp_path: Path) -> None:
    base = tmp_path / "exe_2026"
    base.mkdir()
    with pytest.raises(ExecutableNotFoundError, match="3d.x64"):
        find_3d_exe(str(base))


def test_find_3d_folder_name_under_cadwork_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cadwork_dir = tmp_path / "cadwork.dir"
    exe = _plant_3d(cadwork_dir / "exe_2026")
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.read_env_value",
        lambda name: str(cadwork_dir) if name == "CADWORK.DIR" else None,
    )
    assert find_3d_exe("exe_2026") == exe


def test_find_3d_unresolved_name_raises() -> None:
    with pytest.raises(ExecutableNotFoundError, match="could not resolve"):
        find_3d_exe("exe_2026")


def test_find_3d_falls_back_to_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = _plant_3d(tmp_path / "exe_2026")
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.find_3d_in_registry", lambda: exe
    )
    assert find_3d_exe() == exe


def test_find_3d_falls_back_to_install_dir_glob(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pycadwork.terminal.launcher.glob.glob",
        lambda pattern: [
            r"C:\cadwork.dir\exe_2025\3d.x64\3d.exe",
            r"C:\cadwork.dir\exe_2026\3d.x64\3d.exe",
        ],
    )
    assert find_3d_exe() == Path(r"C:\cadwork.dir\exe_2026\3d.x64\3d.exe")


def test_find_3d_nothing_found_raises() -> None:
    with pytest.raises(ExecutableNotFoundError, match="could not locate 3d.exe"):
        find_3d_exe()
