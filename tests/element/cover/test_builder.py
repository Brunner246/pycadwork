"""CoverBuilder: assemble typed cover aggregates from a set of elements.

The builder buckets the given elements by their active group/subgroup key and
turns each bucket holding a wall/floor/roof element into a typed cover.
``.only(...)`` narrows the result to chosen cover types.
"""

from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    CoverBuilder,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Roof,
    Slab,
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


def _flag_and_group(
    cover: Beam | Plate,
    kind: CoverKind,
    key: str,
    *,
    members: list[Beam | Plate] | None = None,
    mode: GroupingMode = GroupingMode.GROUP,
) -> None:
    """Flag ``cover`` with ``kind`` and put it (plus ``members``) into ``key``."""
    cadwork.attributes.set_cover_kind([cover.id], kind)
    ids = [cover.id] + [m.id for m in (members or [])]
    if mode is GroupingMode.GROUP:
        cadwork.attributes.set_group(ids, key)
    else:
        cadwork.attributes.set_subgroup(ids, key)


def test_builder_aggregates_by_grouping():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall_parent, stud, sheathing = _beam(0), _beam(600), _plate()
    _flag_and_group(
        wall_parent, CoverKind.FRAMED_WALL, "WallX", members=[stud, sheathing]
    )

    covers = (
        CoverBuilder([wall_parent, stud, sheathing]).aggregate_by_grouping().build()
    )
    assert len(covers) == 1
    cover = covers[0]
    assert isinstance(cover, Wall)
    assert cover.id == wall_parent.id
    assert {c.id for c in cover.children} == {stud.id, sheathing.id}


def test_builder_one_aggregate_per_bucket_typed():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    w, f, r = _beam(0), _plate(), _beam(2000)
    _flag_and_group(w, CoverKind.FRAMED_WALL, "W")
    _flag_and_group(f, CoverKind.FRAMED_FLOOR, "F")
    _flag_and_group(r, CoverKind.FRAMED_ROOF, "R")

    by_id = {c.id: c for c in CoverBuilder([w, f, r]).aggregate_by_grouping().build()}
    assert isinstance(by_id[w.id], Wall)
    assert isinstance(by_id[f.id], Slab)
    assert isinstance(by_id[r.id], Roof)


def test_builder_skips_bucket_without_cover_parent():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    a, b = _beam(0), _beam(600)
    cadwork.attributes.set_group([a.id, b.id], "NotACover")

    assert CoverBuilder([a, b]).aggregate_by_grouping().build() == []


def test_builder_skips_ungrouped_elements():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    loose = _beam(0)  # flagged as a cover but no group key
    cadwork.attributes.set_cover_kind([loose.id], CoverKind.FRAMED_WALL)

    assert CoverBuilder([loose]).aggregate_by_grouping().build() == []


def test_builder_only_filters_by_type():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    w, f, r = _beam(0), _plate(), _beam(2000)
    _flag_and_group(w, CoverKind.FRAMED_WALL, "W")
    _flag_and_group(f, CoverKind.FRAMED_FLOOR, "F")
    _flag_and_group(r, CoverKind.FRAMED_ROOF, "R")

    covers = CoverBuilder([w, f, r]).aggregate_by_grouping().only(Wall).build()
    assert {c.id for c in covers} == {w.id}
    assert all(isinstance(c, Wall) for c in covers)


def test_builder_works_in_subgroup_mode():
    cadwork.grouping.set_element_grouping_type(GroupingMode.SUBGROUP)
    parent, child = _beam(0), _beam(600)
    _flag_and_group(
        parent,
        CoverKind.FRAMED_WALL,
        "WallSub",
        members=[child],
        mode=GroupingMode.SUBGROUP,
    )
    # Group field is empty, so the test fails if the builder reads group.
    assert parent.attrs.group == ""

    covers = CoverBuilder([parent, child]).aggregate_by_grouping().build()
    assert len(covers) == 1
    assert covers[0].id == parent.id
    assert {c.id for c in covers[0].children} == {child.id}


def test_builder_requires_strategy():
    with pytest.raises(ValueError, match="no assembly strategy"):
        CoverBuilder([_beam(0)]).build()
