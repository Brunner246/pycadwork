"""discover_covers: scan-the-model loop, encapsulated."""
from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Roof,
    Slab,
    Wall,
    discover_covers,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode


def _stud(x: float = 0.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
    )


def _panel() -> Plate:
    return Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


def test_discover_returns_one_aggregate_per_grouping_bucket_with_a_parent():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall_parent, stud, sheathing = _stud(0), _stud(600), _panel()
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall_parent.id, stud.id, sheathing.id], "WallX")

    covers = discover_covers()
    assert len(covers) == 1
    cover = covers[0]
    assert isinstance(cover, Wall)
    assert cover.id == wall_parent.id
    assert {c.id for c in cover.children} == {stud.id, sheathing.id}


def test_discover_typed_per_cover_kind():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    # one wall bucket
    w = _stud(0)
    cadwork.attributes.set_cover_kind([w.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([w.id], "W")
    # one slab bucket
    f = _panel()
    cadwork.attributes.set_cover_kind([f.id], CoverKind.FRAMED_FLOOR)
    cadwork.attributes.set_group([f.id], "F")
    # one roof bucket
    r = _stud(2000)
    cadwork.attributes.set_cover_kind([r.id], CoverKind.FRAMED_ROOF)
    cadwork.attributes.set_group([r.id], "R")

    by_id = {c.id: c for c in discover_covers()}
    assert isinstance(by_id[w.id], Wall)
    assert isinstance(by_id[f.id], Slab)
    assert isinstance(by_id[r.id], Roof)


def test_discover_accepts_custom_id_subset():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall_parent, stud = _stud(0), _stud(600)
    other = _stud(2000)
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall_parent.id, stud.id, other.id], "X")

    # Only feed the wall parent + stud; the "other" element is excluded.
    covers = discover_covers([wall_parent.id, stud.id])
    assert len(covers) == 1
    # children is a live property reading the model, so it still sees `other`.
    assert {c.id for c in covers[0].children} == {stud.id, other.id}


def test_discover_skips_buckets_without_a_cover_parent():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    # Two beams sharing a group but no wall/roof/floor flag — not a cover.
    a, b = _stud(0), _stud(600)
    cadwork.attributes.set_group([a.id, b.id], "NotACover")

    assert discover_covers() == []


def test_discover_ignores_unaffiliated_elements():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    loose = _stud(0)  # no group set
    parent, child = _stud(700), _stud(1400)
    cadwork.attributes.set_cover_kind([parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([parent.id, child.id], "RealWall")

    covers = discover_covers()
    assert len(covers) == 1
    assert covers[0].id == parent.id
    assert loose.id not in {c.id for c in covers[0].children}


def test_discover_uses_subgroup_in_subgroup_mode():
    cadwork.grouping.set_element_grouping_type(GroupingMode.SUBGROUP)
    parent, child = _stud(0), _stud(600)
    cadwork.attributes.set_cover_kind([parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_subgroup([parent.id, child.id], "WallSub")
    # Make sure the group field is empty so the test fails if discover_covers
    # reads from group instead of subgroup.
    assert cadwork.attributes.get_group(parent.id) == ""

    covers = discover_covers()
    assert len(covers) == 1
    assert covers[0].id == parent.id
    assert {c.id for c in covers[0].children} == {child.id}
