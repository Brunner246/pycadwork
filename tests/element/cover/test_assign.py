"""CoverAssigner: attach loose elements to the cover they spatially sit in."""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    CoverAssigner,
    Point3D,
    RectSection,
    Wall,
    from_id,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode


def _box(x0: float, y0: float, z0: float, dx: float, dy: float, dz: float) -> Beam:
    """An axis-aligned beam spanning [x0,x0+dx] x [y0,y0+dy] x [z0,z0+dz].

    Built along +X with +Z as the third point so its local frame coincides with
    the world axes — the OBB then equals the world AABB, keeping overlap maths
    predictable.
    """
    return Beam.create_rectangular(
        RectSection(dy, dz),
        AxisPoints(
            Point3D(x0, y0, z0),
            Point3D(x0 + dx, y0, z0),
            Point3D(x0, y0, z0 + 1.0),
        ),
    )


def _wall(box: Beam, group: str) -> Wall:
    cadwork.attributes.set_cover_kind([box.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([box.id], group)
    wall = from_id(box.id)
    assert isinstance(wall, Wall)
    return wall


def _covers() -> tuple[Wall, Wall]:
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall_a = _wall(_box(0.0, 0.0, 0.0, 1000.0, 200.0, 3000.0), "WallA")
    wall_b = _wall(_box(2000.0, 0.0, 0.0, 1000.0, 200.0, 3000.0), "WallB")
    return wall_a, wall_b


def test_loose_element_assigned_to_overlapping_cover():
    wall_a, wall_b = _covers()
    stud = _box(100.0, 0.0, 100.0, 80.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a, wall_b]).assign([stud])

    assert len(report) == 1
    assert report[0].cover.id == wall_a.id
    assert stud.attrs.group == "WallA"


def test_element_overlapping_two_covers_picks_largest_overlap():
    wall_a, wall_b = _covers()
    # Spans both walls but overlaps WallA far more (x[500,1000] vs x[2000,2100]).
    spanning = _box(500.0, 0.0, 100.0, 1600.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a, wall_b]).assign([spanning])

    assert report[0].cover.id == wall_a.id
    assert spanning.attrs.group == "WallA"


def test_partial_overlap_still_assigns():
    wall_a, wall_b = _covers()
    # Pokes out past WallB's far face but still overlaps it (x[2500,3000]).
    poking = _box(2500.0, 0.0, 100.0, 1000.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a, wall_b]).assign([poking])

    assert report[0].cover.id == wall_b.id


def test_non_overlapping_element_left_unassigned():
    wall_a, wall_b = _covers()
    far = _box(5000.0, 0.0, 100.0, 80.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a, wall_b]).assign([far])

    assert report == []
    assert far.attrs.group == ""


def test_clean_single_overlap_is_not_marked():
    wall_a, wall_b = _covers()
    stud = _box(100.0, 0.0, 100.0, 80.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a, wall_b]).assign([stud])

    assert report[0].uncertain is False
    assert stud.attrs.user_attribute(1) == ""


def test_ambiguous_overlap_is_marked():
    wall_a, wall_b = _covers()
    # Spans both walls (x[500,2100]) -> assigned to the bigger overlap, but
    # marked because more than one cover overlapped.
    spanning = _box(500.0, 0.0, 100.0, 1600.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a, wall_b]).assign([spanning])

    assert report[0].cover.id == wall_a.id
    assert report[0].uncertain is True
    assert spanning.attrs.user_attribute(1) == "uncertain-cover"


def test_soft_match_within_tolerance_is_marked():
    wall_a, wall_b = _covers()
    # Sits just past WallA's far face (x[1010,1090]); only a positive tolerance
    # reaches it, so the match is soft and must be marked.
    grazing = _box(1010.0, 0.0, 100.0, 80.0, 200.0, 2000.0)

    report = CoverAssigner([wall_a], tolerance=50.0).assign([grazing])

    assert report[0].cover.id == wall_a.id
    assert report[0].uncertain is True
    assert grazing.attrs.user_attribute(1) == "uncertain-cover"


def test_mark_attribute_index_and_value_are_configurable():
    wall_a, wall_b = _covers()
    spanning = _box(500.0, 0.0, 100.0, 1600.0, 200.0, 2000.0)

    CoverAssigner([wall_a, wall_b], mark_attribute_index=7, mark_value="REVIEW").assign(
        [spanning]
    )

    assert spanning.attrs.user_attribute(7) == "REVIEW"
