"""Restore the built-in step catalog after every Gherkin test."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from pycadwork.gherkin import reset_steps


@pytest.fixture(autouse=True)
def _restore_gherkin_steps() -> Iterator[None]:
    reset_steps()
    yield
    reset_steps()
