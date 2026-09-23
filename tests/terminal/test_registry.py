"""The cadwork ENV registry reader (best-effort, degrades to None)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.terminal import registry


def test_find_ci_start_in_registry_returns_existing_exe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "ci_start.exe"
    exe.write_text("")
    monkeypatch.setattr(registry, "read_env_value", lambda name: str(tmp_path))
    assert registry.find_ci_start_in_registry() == exe


def test_find_ci_start_in_registry_none_when_exe_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry, "read_env_value", lambda name: str(tmp_path))
    assert registry.find_ci_start_in_registry() is None


def test_find_ci_start_in_registry_none_when_value_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry, "read_env_value", lambda name: None)
    assert registry.find_ci_start_in_registry() is None


def test_find_3d_in_registry_returns_existing_exe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "3d.x64" / "3d.exe"
    exe.parent.mkdir()
    exe.write_text("")
    monkeypatch.setattr(registry, "read_env_value", lambda name: str(tmp_path))
    assert registry.find_3d_in_registry() == exe


def test_find_3d_in_registry_none_when_exe_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(registry, "read_env_value", lambda name: str(tmp_path))
    assert registry.find_3d_in_registry() is None


def test_find_3d_in_registry_none_when_value_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry, "read_env_value", lambda name: None)
    assert registry.find_3d_in_registry() is None


def test_read_env_value_absent_name_is_none() -> None:
    # Safe everywhere: None off Windows; OSError -> None on Windows.
    assert registry.read_env_value("pycadwork-no-such-value-xyz") is None


def test_override_env_values_restores_absent_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: dict[str, str] = {}

    def _read(name: str) -> str | None:
        return store.get(name)

    def _write(name: str, value: str) -> bool:
        store[name] = value
        return True

    def _delete(name: str) -> bool:
        store.pop(name, None)
        return True

    monkeypatch.setattr(registry, "read_env_value", _read)
    monkeypatch.setattr(registry, "write_env_value", _write)
    monkeypatch.setattr(registry, "delete_env_value", _delete)

    name = "PYCADWORK_IT_PROBE"
    assert registry.read_env_value(name) is None
    with registry.override_env_values({name: "hello"}):
        assert registry.read_env_value(name) == "hello"
    assert registry.read_env_value(name) is None


def test_apply_env_values_raises_when_a_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry, "write_env_value", lambda name, value: name != "B")
    with pytest.raises(registry.RegistryWriteError, match="B"):
        registry.apply_env_values({"A": "1", "B": "2"})


def test_image_pids_parses_tasklist_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "os", type("O", (), {"name": "nt"})())

    def _tasklist(args, **kwargs):
        return '"3d.exe","42","Console","1","10,000 K"\n"3d.exe","99","Console","1","1 K"\n'

    monkeypatch.setattr(registry.subprocess, "check_output", _tasklist)
    assert registry.image_pids("3d.exe") == frozenset({42, 99})


def test_pids_running_filters_by_executable_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exe_2026 = Path(r"D:\cadwork.dir\exe_2026\3d.x64\3d.exe")
    exe_2027 = Path(r"D:\cadwork.dir\exe_2027\3d.x64\3d.exe")
    paths = {1: exe_2026, 2: exe_2027, 3: None}
    monkeypatch.setattr(registry, "image_pids", lambda name: frozenset(paths))
    monkeypatch.setattr(registry, "image_path", lambda pid: paths[pid])
    # 3 cannot be queried, so it is conservatively treated as a match.
    assert registry.pids_running(exe_2026) == frozenset({1, 3})
    assert registry.pids_running(exe_2027) == frozenset({2, 3})
