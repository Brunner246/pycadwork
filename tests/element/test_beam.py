"""Beam create + property round-trip against the FakeCadworkAdapter."""
from __future__ import annotations

import math

from pycadwork import (
    AxisFrame,
    AxisPoints,
    Beam,
    CrossSection,
    Point3D,
    RectSection,
    Vector3D,
)


def test_create_rectangular_round_trips_geometry():
    p1, p2, p3 = Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 200)
    beam = Beam.create_rectangular(RectSection(80.0, 200.0), AxisPoints(p1, p2, p3))

    assert isinstance(beam, Beam)
    assert beam.id >= 1
    assert beam.geometry.width == 80.0
    assert beam.geometry.height == 200.0
    assert math.isclose(beam.geometry.length, 3000.0)
    assert beam.geometry.start_point == p1
    assert beam.geometry.end_point == p2
    assert beam.cross_section is CrossSection.RECTANGULAR


def test_create_circular_reports_circular_cross_section():
    beam = Beam.create_circular(
        50.0, AxisPoints(Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 0, 1))
    )
    assert beam.cross_section is CrossSection.CIRCULAR


def test_create_rectangular_from_vectors_sets_length():
    beam = Beam.create_rectangular_from_vectors(
        RectSection(80.0, 200.0),
        AxisFrame(Point3D(10, 20, 30), Vector3D(1, 0, 0), Vector3D(0, 0, 1), 2500.0),
    )
    assert math.isclose(beam.geometry.length, 2500.0)


def test_name_and_group_setters_are_persistent():
    beam = Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    beam.attrs.set_name("Stud-01")
    beam.attrs.set_group("WallA1")
    assert beam.attrs.name == "Stud-01"
    assert beam.attrs.group == "WallA1"
