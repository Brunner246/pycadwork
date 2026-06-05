"""MEP leaf types: create + property round-trip + dispatch."""

from __future__ import annotations

import math

import pytest

from pycadwork import CircularMep, Point3D, RectangularMep, from_id


def test_create_circular_mep_sets_diameter_and_length():
    m = CircularMep.create(80.0, [Point3D(0, 0, 0), Point3D(0, 0, 1000)])
    assert m.diameter == 80.0
    assert m.geometry.diameter == 80.0
    assert m.geometry.radius == 40.0
    assert math.isclose(m.geometry.length, 1000.0)


def test_circular_geometry_suppresses_rectangular_width_height():
    m = CircularMep.create(80.0, [Point3D(0, 0, 0), Point3D(0, 0, 1000)])
    with pytest.raises(AttributeError):
        _ = m.geometry.width
    with pytest.raises(AttributeError):
        _ = m.geometry.height


def test_circular_diameter_is_writable():
    m = CircularMep.create(80.0, [Point3D(0, 0, 0), Point3D(0, 0, 1000)])
    m.geometry.diameter = 120.0
    assert m.diameter == 120.0
    assert m.geometry.radius == 60.0


def test_create_rectangular_mep_sets_width_depth_and_length():
    m = RectangularMep.create(200.0, 100.0, [Point3D(0, 0, 0), Point3D(0, 0, 1500)])
    assert m.geometry.width == 200.0
    assert m.geometry.height == 100.0
    assert math.isclose(m.geometry.length, 1500.0)


def test_from_id_dispatches_to_mep_types():
    circular = CircularMep.create(50.0, [Point3D(0, 0, 0), Point3D(0, 0, 500)])
    rectangular = RectangularMep.create(
        120.0, 60.0, [Point3D(0, 0, 0), Point3D(0, 0, 500)]
    )
    assert isinstance(from_id(circular.id), CircularMep)
    assert isinstance(from_id(rectangular.id), RectangularMep)


def test_multi_point_path_spans_first_to_last_point():
    m = CircularMep.create(
        40.0,
        [Point3D(0, 0, 0), Point3D(0, 0, 1000), Point3D(0, 0, 2500)],
    )
    assert math.isclose(m.geometry.length, 2500.0)


def test_create_rejects_path_with_fewer_than_two_points():
    with pytest.raises(ValueError):
        CircularMep.create(40.0, [Point3D(0, 0, 0)])
    with pytest.raises(ValueError):
        RectangularMep.create(120.0, 60.0, [])
