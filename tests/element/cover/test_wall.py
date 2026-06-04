"""Wall: children, children_of, add_child/remove_child/replace_children, set_kind."""
from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    Drilling,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Segment,
    Wall,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode


def _stud(x: float) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
    )


def _wall_with_two_beams() -> tuple[Wall, Beam, Beam]:
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    a = _stud(0)
    b = _stud(600)
    cadwork.attributes.set_cover_kind([a.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([a.id, b.id], "WallA1")
    return Wall(a.id), a, b


def test_wall_children_returns_siblings_minus_self():
    wall, a, b = _wall_with_two_beams()
    child_ids = {c.id for c in wall.children}
    assert child_ids == {b.id}


def test_wall_children_of_filters_to_beams():
    wall, a, b = _wall_with_two_beams()
    beams = wall.children_of(Beam)
    assert {x.id for x in beams} == {b.id}
    assert all(isinstance(x, Beam) for x in beams)


def test_wall_add_child_promotes_element_into_group():
    wall, a, b = _wall_with_two_beams()
    new = _stud(1200)
    wall.add_child(new)
    assert new.attrs.group == "WallA1"
    assert new.id in {c.id for c in wall.children}


def test_wall_add_children_batched_accepts_mixed_types():
    wall, a, b = _wall_with_two_beams()
    new_beam = _stud(1200)
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    drilling = Drilling.create(10, Segment(Point3D(0, 0, 0), Point3D(0, 0, 100)))
    wall.add_children([new_beam, plate, drilling])
    assert {c.id for c in wall.children} == {b.id, new_beam.id, plate.id, drilling.id}


def test_wall_remove_child_clears_membership():
    wall, a, b = _wall_with_two_beams()
    wall.remove_child(b)
    assert b.attrs.group == ""
    assert b.id not in {c.id for c in wall.children}


def test_wall_replace_children_swaps_set():
    wall, a, b = _wall_with_two_beams()
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    drilling = Drilling.create(10, Segment(Point3D(0, 0, 0), Point3D(0, 0, 100)))
    wall.replace_children([plate, drilling])
    child_ids = {c.id for c in wall.children}
    assert child_ids == {plate.id, drilling.id}
    assert b.attrs.group == ""


def test_set_kind_rejects_a_non_wall_kind():
    wall, _, _ = _wall_with_two_beams()
    with pytest.raises(ValueError):
        wall.set_kind(CoverKind.FRAMED_ROOF)


def test_set_kind_accepts_a_wall_kind():
    wall, _, _ = _wall_with_two_beams()
    wall.set_kind(CoverKind.SOLID_WALL)
    assert wall.kind is CoverKind.SOLID_WALL


def test_subgroup_mode_uses_subgroup_for_membership():
    cadwork.grouping.set_element_grouping_type(GroupingMode.SUBGROUP)
    a = _stud(0)
    b = _stud(600)
    cadwork.attributes.set_cover_kind([a.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_subgroup([a.id, b.id], "WallSub")
    wall = Wall(a.id)
    assert {c.id for c in wall.children} == {b.id}
