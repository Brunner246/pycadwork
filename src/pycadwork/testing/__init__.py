"""Shipped test doubles — importable by dependent packages, not test-only.

The in-memory :class:`FakeCadworkAdapter` lets any project built on pycadwork
run its suite with no cadwork process, using the seam documented in
:mod:`pycadwork.cadwork_adapter`::

    from pycadwork.testing import FakeCadworkAdapter

    monkeypatch.setattr(pycadwork.cadwork_adapter, "cadwork", FakeCadworkAdapter())

Install the (dependency-free) extra to make the intent explicit::

    pip install "pycadwork[testing]"

The sub-adapters are exported too, so a downstream test can swap a single slot
(``cadwork.attributes``) rather than the whole facade — which is what
``tests/conftest.py`` does, since production call sites capture the singleton at
import time.
"""

from __future__ import annotations

from pycadwork.testing.cadwork_adapter import (
    FakeAttributesAdapter,
    FakeBimAdapter,
    FakeCadworkAdapter,
    FakeCollisionAdapter,
    FakeDisplayAdapter,
    FakeElementsAdapter,
    FakeFileAdapter,
    FakeGeometryAdapter,
    FakeGroupingAdapter,
    FakeMaterialAdapter,
    FakeModuleAdapter,
    FakeOperationsAdapter,
    FakeProjectAdapter,
    FakeState,
    FakeVisualizationAdapter,
)

__all__ = [
    "FakeAttributesAdapter",
    "FakeBimAdapter",
    "FakeCadworkAdapter",
    "FakeCollisionAdapter",
    "FakeDisplayAdapter",
    "FakeElementsAdapter",
    "FakeFileAdapter",
    "FakeGeometryAdapter",
    "FakeGroupingAdapter",
    "FakeMaterialAdapter",
    "FakeModuleAdapter",
    "FakeOperationsAdapter",
    "FakeProjectAdapter",
    "FakeState",
    "FakeVisualizationAdapter",
]
