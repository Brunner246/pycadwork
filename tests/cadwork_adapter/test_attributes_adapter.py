"""Real ``AttributesAdapter`` call-shape tests (cwapi3d controllers stubbed).

The autouse fake swaps the whole adapter, so a fake-based test cannot catch a
wrong cwapi3d *call shape* inside a real adapter method — those bugs only bite in
live cadwork. These tests stub the cwapi3d controller modules via ``sys.modules``
(the pattern from ``tests/detail/test_module_adapter.py``) and assert the seam
calls cwapi3d the way pybind11 expects.
"""

from __future__ import annotations

import sys
import types

import pytest

from pycadwork.cadwork_adapter._attributes import AttributesAdapter
from pycadwork.cadwork_adapter.types import ElementId


@pytest.fixture
def stub_controllers(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Stub ``attribute_controller`` / ``material_controller``, recording calls."""
    calls: list[tuple] = []

    attribute_controller = types.ModuleType("attribute_controller")
    attribute_controller.set_element_material = (  # type: ignore[attr-defined]
        lambda eids, mid: calls.append(("set_element_material", eids, mid))
    )
    material_controller = types.ModuleType("material_controller")
    material_controller.get_material_id = lambda name: 289  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "attribute_controller", attribute_controller)
    monkeypatch.setitem(sys.modules, "material_controller", material_controller)
    return calls


def test_set_material_name_passes_id_sequence_in_one_call(
    stub_controllers: list[tuple],
) -> None:
    """Regression: ``set_element_material`` takes a *sequence* of ids, not a scalar.

    cwapi3d's signature is ``(Sequence[int], int) -> None``. The old per-element
    loop invoked it with a scalar eid, raising a ``TypeError`` in live cadwork
    while realizing a detail (which aborted material, colour, grouping, and
    module-property application). It must resolve the name once and apply it to
    the whole id list in a single call.
    """
    AttributesAdapter().set_material_name([ElementId(1), ElementId(2)], "Gipsfaser")
    assert stub_controllers == [
        ("set_element_material", [ElementId(1), ElementId(2)], 289)
    ]
