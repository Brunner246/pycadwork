"""Roof: kind narrowing + membership."""

from __future__ import annotations

import pytest

from pycadwork import AxisPoints, Beam, Point3D, RectSection, Roof
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind


def test_roof_kind_narrowing():
    rafter = Beam.create_rectangular(
        RectSection(60, 220),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 4000, 0), Point3D(0, 0, 1)),
    )
    cadwork.attributes.set_cover_kind([rafter.id], CoverKind.FRAMED_ROOF)
    roof = Roof(rafter.id)
    assert roof.kind is CoverKind.FRAMED_ROOF

    with pytest.raises(ValueError):
        roof.set_kind(CoverKind.SOLID_WALL)

    roof.set_kind(CoverKind.SOLID_ROOF)
    assert roof.kind is CoverKind.SOLID_ROOF
