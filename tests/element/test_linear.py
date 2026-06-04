"""LinearElement: axis_points / axis_frame / isinstance refinement.

Verifies that Beam, Drilling, Line share the LinearGeometry surface and
that the new composite value objects round-trip the construction args.
"""

from __future__ import annotations

import math

from pycadwork import (
    AxisFrame,
    AxisPoints,
    Beam,
    Drilling,
    Line,
    LinearElement,
    Point3D,
    RectSection,
    Segment,
    Vector3D,
)


def test_beam_is_a_linear_element():
    beam = Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 200)),
    )
    assert isinstance(beam, LinearElement)


def test_drilling_is_a_linear_element():
    d = Drilling.create(12.0, Segment(Point3D(0, 0, 0), Point3D(0, 0, 200)))
    assert isinstance(d, LinearElement)


def test_line_is_a_linear_element():
    line = Line.create(Segment(Point3D(0, 0, 0), Point3D(1000, 0, 0)))
    assert isinstance(line, LinearElement)


def test_axis_points_round_trips_construction_args():
    p1, p2, p3 = Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 200)
    beam = Beam.create_rectangular(RectSection(80.0, 200.0), AxisPoints(p1, p2, p3))

    ap = beam.geometry.axis_points
    assert isinstance(ap, AxisPoints)
    assert ap.p1 == p1
    assert ap.p2 == p2
    # p3 in cwapi3d's frame is the orthonormal "up" hint after construction;
    # we only assert it lies on the +z side of the start point.
    assert ap.p3.z > 0.0


def test_axis_frame_length_matches_length_property():
    beam = Beam.create_rectangular_from_vectors(
        RectSection(80.0, 200.0),
        AxisFrame(Point3D(10, 20, 30), Vector3D(1, 0, 0), Vector3D(0, 0, 1), 2500.0),
    )
    af = beam.geometry.axis_frame
    assert isinstance(af, AxisFrame)
    assert math.isclose(af.length, beam.geometry.length)
    assert math.isclose(af.length, 2500.0)
    assert af.origin == Point3D(10, 20, 30)


def test_linear_element_exposes_obb():
    beam = Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    obb = beam.geometry.obb
    # The OBB's frame axes must match the element's frame axes.
    assert obb.frame.axis_x == beam.geometry.frame.axis_x
    assert obb.frame.axis_y == beam.geometry.frame.axis_y
    assert obb.frame.axis_z == beam.geometry.frame.axis_z
