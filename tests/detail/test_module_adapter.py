"""The ModuleAdapter setter table maps each field to the right cwapi3d setter.

This isolates the one place real method names matter: the translation runs
against a stub recorder (no cadwork), so a field wired to the wrong setter — or
a ``Distribution(count=...)`` that calls the distance setter instead of
``use_number`` — fails here.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter._module import ModuleAdapter
from pycadwork.detail.properties import (
    CuttingElement,
    Distribution,
    ModuleProperties,
    NamedFlag,
)


class _Recorder:
    """Stand-in for a live element_module_properties object; records every call.

    ``__getattr__`` hands back a recording callable for any name, so every
    ``hasattr``-guarded setter in the adapter fires and is captured.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __getattr__(self, name: str):
        def record(value: object) -> None:
            self.calls.append((name, value))

        return record

    def values(self, setter: str) -> list[object]:
        return [v for n, v in self.calls if n == setter]

    def names(self) -> set[str]:
        return {n for n, _ in self.calls}


def _apply(props: ModuleProperties) -> _Recorder:
    rec = _Recorder()
    ModuleAdapter._apply_to(rec, props)
    return rec


def test_independent_bool_maps_to_its_setter():
    rec = _apply(ModuleProperties(auxiliary=True, no_collision_control=True))
    assert rec.values("set_auxiliary") == [True]
    assert rec.values("set_no_collision_control") == [True]
    assert rec.values("set_stretch_with_top_of_wall") == [False]


def test_distribution_by_count_uses_number_not_distance():
    rec = _apply(
        ModuleProperties(distribute_in_axis=Distribution(active=True, count=5))
    )
    assert rec.values("set_distribute_in_axis_direction") == [True]
    assert rec.values("set_distribute_in_axis_direction_use_number") == [True]
    assert rec.values("set_distribute_in_axis_direction_number") == [5]
    # The distance setter must NOT be touched in count mode.
    assert "set_distribute_in_axis_direction_distance" not in rec.names()


def test_distribution_by_distance_uses_distance_setter():
    rec = _apply(
        ModuleProperties(distribute_in_axis=Distribution(active=True, distance=625.0))
    )
    assert rec.values("set_distribute_in_axis_direction_distance") == [625.0]
    assert "set_distribute_in_axis_direction_use_number" not in rec.names()


def test_distribution_by_max_distance_uses_max_setter():
    rec = _apply(
        ModuleProperties(
            distribute_in_axis=Distribution(active=True, max_distance=800.0)
        )
    )
    assert rec.values("set_distribute_in_axis_direction_use_max_distance") == [True]
    assert rec.values("set_distribute_in_axis_direction_max_distance") == [800.0]


def test_perpendicular_distribution_maps_to_perpendicular_setters():
    rec = _apply(
        ModuleProperties(
            distribute_perpendicular=Distribution(active=True, count=3)
        )
    )
    assert rec.values("set_distribute_perpendicular_to_axis_direction") == [True]
    assert rec.values("set_distribute_perpendicular_to_axis_direction_number") == [3]


def test_cutting_element_sets_active_and_priority():
    rec = _apply(
        ModuleProperties(cutting_element=CuttingElement(active=True, priority=2))
    )
    assert rec.values("set_cutting_element") == [True]
    assert rec.values("set_cutting_element_priority") == [2]


def test_cutting_element_priority_skipped_when_inactive():
    rec = _apply(ModuleProperties(cutting_element=CuttingElement(active=False)))
    assert rec.values("set_cutting_element") == [False]
    assert "set_cutting_element_priority" not in rec.names()


def test_named_flag_sets_active_and_name():
    rec = _apply(
        ModuleProperties(unique_layername=NamedFlag(active=True, name="EXT"))
    )
    assert rec.values("set_unique_layername") == [True]
    assert rec.values("set_layername") == ["EXT"]


def test_named_flag_name_skipped_when_inactive():
    rec = _apply(ModuleProperties(unique_layername=NamedFlag(active=False)))
    assert rec.values("set_unique_layername") == [False]
    assert "set_layername" not in rec.names()
