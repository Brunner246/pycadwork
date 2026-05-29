"""CoverBuilder: batch-attach to a pre-built cover.

The builder no longer makes the cover — it only batches children into an
existing typed ``Wall`` / ``Slab`` / ``Roof``. The caller flags the cover
with the right ``CoverKind`` and sets its group/subgroup key first.
"""
from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    CoverBuilder,
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


def _beam(y: float = 0.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, y, 0), Point3D(0, y + 3000, 0), Point3D(0, y, 1)),
    )


def _plate() -> Plate:
    return Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


def _wall_cover(key: str = "WallA", mode: GroupingMode = GroupingMode.GROUP) -> Wall:
    cadwork.grouping.set_element_grouping_type(mode)
    cover = _beam(0)
    if mode is GroupingMode.GROUP:
        cover.attrs.set_group(key)
    else:
        cover.attrs.set_subgroup(key)
    cadwork.attributes.set_cover_kind([cover.id], CoverKind.FRAMED_WALL)
    return Wall(cover.id)


def test_imperative_add_child_without_builder():
    wall = _wall_cover()
    new_beam = _beam(700)
    new_plate = _plate()
    wall.add_child(new_beam)
    wall.add_child(new_plate)
    assert {c.id for c in wall.children} == {new_beam.id, new_plate.id}


def test_builder_adds_children_via_add_and_add_all():
    wall = _wall_cover()
    b1, b2, p = _beam(700), _beam(1400), _plate()
    result = CoverBuilder(wall).add(b1).add_all([b2, p]).build()
    assert result.id == wall.id
    assert {c.id for c in wall.children} == {b1.id, b2.id, p.id}


def test_builder_filters_out_cover_id_from_added_elements():
    wall = _wall_cover()
    result = CoverBuilder(wall).add(wall).build()
    assert result.id == wall.id
    assert wall.children == []


def test_builder_raises_when_cover_has_no_group_key():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    cover = _beam(0)
    cadwork.attributes.set_cover_kind([cover.id], CoverKind.FRAMED_WALL)
    wall = Wall(cover.id)

    with pytest.raises(ValueError, match="set_group"):
        CoverBuilder(wall).add(_beam(700)).build()


def test_builder_works_in_subgroup_mode():
    wall = _wall_cover(key="WallSub", mode=GroupingMode.SUBGROUP)
    b1, b2 = _beam(700), _beam(1400)
    CoverBuilder(wall).add_all([b1, b2]).build()

    assert b1.attrs.subgroup == "WallSub"
    assert b2.attrs.subgroup == "WallSub"
    assert b1.attrs.group == ""
    assert b2.attrs.group == ""


def test_aggregate_add_children_batched():
    wall = _wall_cover()
    b1, b2 = _beam(700), _beam(1400)
    drilling = Drilling.create(10, Segment(Point3D(0, 0, 0), Point3D(0, 0, 100)))
    wall.add_children([b1, b2, drilling])
    assert {c.id for c in wall.children} == {b1.id, b2.id, drilling.id}
