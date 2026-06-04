"""Drilling create + property round-trip."""

from __future__ import annotations

import math

from pycadwork import Drilling, Point3D, Segment


def test_create_drilling_sets_diameter_and_length():
    d = Drilling.create(12.0, Segment(Point3D(0, 0, 0), Point3D(0, 0, 200)))
    assert d.geometry.width == 12.0
    assert d.geometry.height == 12.0
    assert math.isclose(d.geometry.length, 200.0)
