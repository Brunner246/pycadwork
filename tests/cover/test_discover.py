"""discover_covers: filter the model down to its typed cover elements."""

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
from pycadwork.cadwork_adapter.types import CoverKind

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


def test_discover_returns_flagged_covers_typed():
    # one wall bucket
    w = _stud(0)
    cadwork.attributes.set_cover_kind([w.id], CoverKind.FRAMED_WALL)
    # one slab bucket
    f = _panel()
    cadwork.attributes.set_cover_kind([f.id], CoverKind.FRAMED_FLOOR)
    # one roof bucket
    r = _stud(2000)
    cadwork.attributes.set_cover_kind([r.id], CoverKind.FRAMED_ROOF)

    by_id = {c.id: c for c in discover_covers()}
    assert isinstance(by_id[w.id], Wall)
    assert isinstance(by_id[f.id], Slab)
    assert isinstance(by_id[r.id], Roof)


def test_discover_exposes_children_as_a_live_view():
    wall_parent, stud, sheathing = _stud(0), _stud(600), _panel()
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall_parent.id, stud.id, sheathing.id], "WallX")

    covers = discover_covers()
    assert len(covers) == 1
    cover = covers[0]
    assert isinstance(cover, Wall)
    assert cover.id == wall_parent.id
    assert {c.id for c in cover.children} == {stud.id, sheathing.id}


def test_discover_accepts_custom_id_subset():
    wall_parent, stud = _stud(0), _stud(600)
    other = _stud(2000)
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall_parent.id, stud.id, other.id], "X")

    # Only feed the wall parent + stud; the "other" element is excluded.
    covers = discover_covers([wall_parent.id, stud.id])
    assert len(covers) == 1
    # children is a live property reading the model, so it still sees `other`.
    assert {c.id for c in covers[0].children} == {stud.id, other.id}


def test_discover_skips_elements_without_cover_flag():
    # Plain beams with no wall/roof/floor flag are not covers.
    a, b = _stud(0), _stud(600)
    cadwork.attributes.set_group([a.id, b.id], "NotACover")

    assert discover_covers() == []
