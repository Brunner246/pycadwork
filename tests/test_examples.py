"""Execute every example module against the fake adapter.

The ``examples/`` package teaches the public API; this test guarantees the
examples never silently drift from it. The ``autouse`` ``fake_cadwork`` fixture
(``tests/conftest.py``) installs the in-memory adapter for every test, so each
example's ``run()`` executes against the fake with no extra wiring. A renamed or
removed public export breaks the matching example here immediately.
"""

from __future__ import annotations

import importlib

import pytest

from examples import MODULES


@pytest.mark.parametrize("module_name", MODULES)
def test_example_runs(module_name: str) -> None:
    """Each example's ``run()`` completes without raising under the fake adapter."""
    module = importlib.import_module(f"examples.{module_name}")
    module.run()
