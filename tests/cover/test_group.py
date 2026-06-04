"""Group: siblings-by-grouping-key view, mode-aware."""
from __future__ import annotations

from pycadwork import AxisPoints, Beam, Point3D, RectSection
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import GroupingMode
from pycadwork.cover.group import Group


def _beam(name: str) -> Beam:
    b = Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    b.attrs.name = name
    return b


def test_group_collects_by_group_key_in_group_mode():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    a, b, c = _beam("a"), _beam("b"), _beam("c")
    a.attrs.group = "WallA"
    b.attrs.group = "WallA"
    c.attrs.group = "WallB"

    members = Group.of(a).members()
    member_ids = {m.id for m in members}
    assert member_ids == {a.id, b.id}


def test_group_collects_by_subgroup_in_subgroup_mode():
    cadwork.grouping.set_element_grouping_type(GroupingMode.SUBGROUP)
    a, b, c = _beam("a"), _beam("b"), _beam("c")
    a.attrs.subgroup = "WallA"
    b.attrs.subgroup = "WallA"
    c.attrs.subgroup = "WallB"

    members = Group.of(a).members()
    member_ids = {m.id for m in members}
    assert member_ids == {a.id, b.id}


def test_members_of_filters_by_type():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    a, b = _beam("a"), _beam("b")
    a.attrs.group = "WallA"
    b.attrs.group = "WallA"

    beams = Group.of(a).members_of(Beam)
    assert {x.id for x in beams} == {a.id, b.id}
