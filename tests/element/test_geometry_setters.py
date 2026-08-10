"""Dimension setters: width / height / length / thickness write the real
dimension back through the adapter and read back via the matching property.
"""

from __future__ import annotations

from pycadwork import AxisPoints, PanelSection, Plate, Point3D, RectSection
from pycadwork import Beam


def _beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


def test_width_setter_round_trips():
    beam = _beam()
    beam.geometry.width = 120.0
    assert beam.geometry.width == 120.0


def test_height_setter_round_trips():
    beam = _beam()
    beam.geometry.height = 240.0
    assert beam.geometry.height == 240.0


def test_length_setter_round_trips():
    beam = _beam()
    beam.geometry.length = 3000.0
    assert beam.geometry.length == 3000.0


def test_thickness_setter_aliases_height():
    plate = Plate.create_rectangular(
        PanelSection(600.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    plate.geometry.thickness = 27.0
    assert plate.geometry.thickness == 27.0
    # thickness is the semantic alias for the backend's height channel.
    assert plate.geometry.height == 27.0
