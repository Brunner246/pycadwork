"""Test fixtures: swap in a FakeCadworkAdapter so tests need no cadwork process."""
from __future__ import annotations

import pytest

from pycadwork import cadwork_adapter as _adapter_module
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


@pytest.fixture(autouse=True)
def fake_cadwork(monkeypatch: pytest.MonkeyPatch) -> FakeCadworkAdapter:
    """Replace the active adapter with a fresh in-memory fake per test.

    Production call sites do ``from pycadwork.cadwork_adapter import cadwork``
    which captures the singleton at import time. To make the fake reach those
    captured references we swap the *sub-adapter slots* on the existing
    singleton — every call goes through ``cadwork.<sub>.method(...)`` so each
    lookup hits the patched fake. The ``cadwork_adapter.cadwork`` module
    attribute is also pointed at the fake for tests that look it up directly.
    ``monkeypatch`` reverts everything after the test.
    """
    fake = FakeCadworkAdapter()
    singleton = _adapter_module.cadwork
    monkeypatch.setattr(singleton, "elements", fake.elements)
    monkeypatch.setattr(singleton, "attributes", fake.attributes)
    monkeypatch.setattr(singleton, "geometry", fake.geometry)
    monkeypatch.setattr(singleton, "grouping", fake.grouping)
    monkeypatch.setattr(singleton, "display", fake.display)
    monkeypatch.setattr(singleton, "project", fake.project)
    monkeypatch.setattr(_adapter_module, "cadwork", fake)
    return fake
