"""build_3d_runtime_env — PATH prepend and CADWORK_EXE/LIB/TCL overlay."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pycadwork.terminal.launcher import build_3d_runtime_env, exe_base_for


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
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
    monkeypatch.setenv("PATH", r"C:\Windows\system32")

    env = build_3d_runtime_env(base)
    assert env["CADWORK_EXE"] == str(base)
    assert env["CADWORK_LIB"] == str(pclib)
    parts = env["PATH"].split(os.pathsep)
    assert parts[0] == str(pclib)
    assert str(base / "lxsdk.x64" / "bin") in parts
    assert str(three_d) in parts
    assert parts[-1] == r"C:\Windows\system32"
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


def test_runtime_env_sets_tcl_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    tcl_lib = _mkdir(base / "pclib.x64" / "TCL" / "LIB")
    tcl82 = _mkdir(tcl_lib / "TCL8.2")
    tk82 = _mkdir(tcl_lib / "TK8.2")
    monkeypatch.setenv("PATH", "existing")
    env = build_3d_runtime_env(base)
    assert env["TCLLIBPATH"] == str(tcl_lib)
    assert env["TCL_LIBRARY"] == str(tcl82)
    assert env["TK_LIBRARY"] == str(tk82)


def test_runtime_env_does_not_mutate_parent_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "exe_2026"
    _mkdir(base / "pclib.x64")
    monkeypatch.setenv("PATH", "before")
    build_3d_runtime_env(base)
    assert os.environ["PATH"] == "before"
