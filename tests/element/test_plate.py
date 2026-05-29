"""Plate create + property round-trip."""
from __future__ import annotations

from pycadwork import AxisPoints, PanelSection, Plate, Point3D


def test_create_rectangular_panel_round_trips():
    plate = Plate.create_rectangular(
        PanelSection(600.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    assert isinstance(plate, Plate)
    assert plate.geometry.width == 600.0
    assert plate.geometry.height == 18.0
