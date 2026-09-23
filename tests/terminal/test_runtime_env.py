"""build_3d_runtime_env — PATH prepend and CADWORK_EXE/LIB/TCL overlay."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pycadwork.terminal.launcher import build_3d_runtime_env, exe_base_for


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _script(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# dummy\n", encoding="utf-8")
    return path


def test_exe_base_for_strips_3d_x64(tmp_path: Path) -> None:
    three_d = tmp_path / "exe_2026" / "3d.x64" / "3d.exe"
    assert exe_base_for(three_d) == tmp_path / "exe_2026"


def test_runtime_env_sets_exe_and_lib_and_prepends_existing_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    pclib = _mkdir(base / "pclib.x64")
    three_d = _mkdir(base / "3d.x64")
    _mkdir(base / "lxsdk.x64" / "bin")
    monkeypatch.setenv("PATH", "existing")

    env = build_3d_runtime_env(base)
    assert env["CADWORK_EXE"] == str(base)
    assert env["CADWORK_LIB"] == str(pclib)
    parts = env["PATH"].split(os.pathsep)
    assert parts[0] == str(pclib)
    assert str(base / "lxsdk.x64" / "bin") in parts
    assert str(three_d) in parts
    assert parts[-1] == "existing"
    assert "TCLLIBPATH" not in env


def test_runtime_env_skips_missing_optional_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    _mkdir(base / "3d.x64")
    monkeypatch.setenv("PATH", "")
    env = build_3d_runtime_env(base)
    parts = [p for p in env["PATH"].split(os.pathsep) if p]
    assert parts == [str(base / "3d.x64")]
    assert str(base / "2dv.x64") not in parts
    assert str(base / "pclib.x64") not in parts


def test_runtime_env_sets_tcl_8_6_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    tcl_lib = _mkdir(base / "pclib.x64" / "tcl" / "lib")
    tcl86 = tcl_lib / "tcl8.6"
    tk86 = tcl_lib / "tk8.6"
    _script(tcl86 / "init.tcl")
    _script(tk86 / "tk.tcl")
    monkeypatch.setenv("PATH", "existing")
    env = build_3d_runtime_env(base)
    assert Path(env["TCLLIBPATH"]) == tcl_lib
    assert Path(env["TCL_LIBRARY"]) == tcl86
    assert Path(env["TK_LIBRARY"]) == tk86


def test_runtime_env_sets_tcl_8_2_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    tcl_lib = _mkdir(base / "pclib.x64" / "TCL" / "LIB")
    tcl82 = tcl_lib / "TCL8.2"
    tk82 = tcl_lib / "TK8.2"
    _script(tcl82 / "init.tcl")
    _script(tk82 / "tk.tcl")
    monkeypatch.setenv("PATH", "existing")
    env = build_3d_runtime_env(base)
    assert Path(env["TCLLIBPATH"]) == tcl_lib
    assert Path(env["TCL_LIBRARY"]) == tcl82
    assert Path(env["TK_LIBRARY"]) == tk82


def test_runtime_env_prefers_tcl_8_6_over_8_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    tcl_lib = _mkdir(base / "pclib.x64" / "tcl" / "lib")
    _script(tcl_lib / "TCL8.2" / "init.tcl")
    _script(tcl_lib / "TK8.2" / "tk.tcl")
    tcl86 = tcl_lib / "tcl8.6"
    tk86 = tcl_lib / "tk8.6"
    _script(tcl86 / "init.tcl")
    _script(tk86 / "tk.tcl")
    monkeypatch.setenv("PATH", "existing")
    env = build_3d_runtime_env(base)
    assert Path(env["TCL_LIBRARY"]) == tcl86
    assert Path(env["TK_LIBRARY"]) == tk86


def test_runtime_env_skips_tcl_library_without_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    tcl_lib = _mkdir(base / "pclib.x64" / "tcl" / "lib")
    _mkdir(tcl_lib / "tcl8.6")
    monkeypatch.setenv("PATH", "existing")
    env = build_3d_runtime_env(base)
    assert Path(env["TCLLIBPATH"]) == tcl_lib
    assert "TCL_LIBRARY" not in env
    assert "TK_LIBRARY" not in env


def test_runtime_env_does_not_mutate_parent_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    _mkdir(base / "pclib.x64")
    monkeypatch.setenv("PATH", "before")
    build_3d_runtime_env(base)
    assert os.environ["PATH"] == "before"
