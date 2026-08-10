"""OrientedElement: Plate's axis_frame / thickness alias / obb."""

from __future__ import annotations

import math

from pycadwork import (
    AxisFrame,
    AxisPoints,
    OrientedElement,
    PanelSection,
    Plate,
    Point3D,
    Vector3D,
)


def test_plate_is_an_oriented_element():
    plate = Plate.create_rectangular(
        PanelSection(600.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(2000, 0, 0), Point3D(0, 1, 0)),
    )
    assert isinstance(plate, OrientedElement)


def test_thickness_aliases_backend_height():
    plate = Plate.create_rectangular(
        PanelSection(600.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(2000, 0, 0), Point3D(0, 1, 0)),
    )
    assert plate.geometry.thickness == plate.geometry.height == 18.0


def test_axis_frame_length_matches_length_property():
    plate = Plate.create_rectangular_from_vectors(
        PanelSection(600.0, 18.0),
        AxisFrame(Point3D(5, 5, 5), Vector3D(1, 0, 0), Vector3D(0, 0, 1), 2500.0),
    )
    af = plate.geometry.axis_frame
    assert isinstance(af, AxisFrame)
    assert math.isclose(af.length, plate.geometry.length)
    assert af.origin == Point3D(5, 5, 5)
