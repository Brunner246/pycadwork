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


def test_read_env_value_absent_name_is_none() -> None:
    # Safe everywhere: None off Windows; OSError -> None on Windows.
    assert registry.read_env_value("pycadwork-no-such-value-xyz") is None
