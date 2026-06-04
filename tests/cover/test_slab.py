"""Slab: kind narrowing + membership."""

from __future__ import annotations

import pytest

from pycadwork import AxisPoints, Beam, PanelSection, Plate, Point3D, RectSection, Slab
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind


def test_slab_membership_and_kind_narrowing():
    deck = Plate.create_rectangular(
        PanelSection(2400, 22),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    joist = Beam.create_rectangular(
        RectSection(60, 220),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 1)),
    )
    cadwork.attributes.set_cover_kind([deck.id], CoverKind.FRAMED_FLOOR)
    cadwork.attributes.set_group([deck.id, joist.id], "Floor1")

    slab = Slab(deck.id)
    assert slab.kind is CoverKind.FRAMED_FLOOR
    assert {c.id for c in slab.children} == {joist.id}

    with pytest.raises(ValueError):
        slab.set_kind(CoverKind.FRAMED_WALL)

    slab.set_kind(CoverKind.SOLID_FLOOR)
    assert slab.kind is CoverKind.SOLID_FLOOR
