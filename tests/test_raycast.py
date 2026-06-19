"""Behaviour of :func:`pycadwork.cast_ray` against the in-memory fake.

The fake adapter intersects the ray with each element's world-axis box (grown
by ``radius``), so these assertions exercise the real ordering, conversion, and
result-shaping logic of :mod:`pycadwork.raycast` end to end.
"""

from __future__ import annotations

from pycadwork import AxisPoints, Beam, Point3D, RectSection, cast_ray


def _beam(x0: float, x1: float) -> Beam:
    """A 100x100 beam running along +X from ``x0`` to ``x1`` (box y,z in [0,100])."""
    return Beam.create_rectangular(
        RectSection(width=100.0, height=100.0),
        AxisPoints(Point3D(x0, 0, 0), Point3D(x1, 0, 0), Point3D(x0, 0, 1)),
    )


def test_ray_through_two_beams_is_ordered_nearest_first() -> None:
    near = _beam(0, 1000)
    far = _beam(2000, 3000)

    result = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50))

    assert result  # truthy when anything was hit
    assert len(result) == 2
    assert result.element_ids == [near.id, far.id]
    assert result.first is not None
    assert result.first.element.id == near.id


def test_first_hit_entry_and_distance_match_geometry() -> None:
    _beam(0, 1000)

    hit = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50)).first
    assert hit is not None

    assert hit.entry == Point3D(0, 50, 50)
    assert hit.exit == Point3D(1000, 50, 50)
    assert hit.distance == 100.0


def test_ray_that_misses_is_empty() -> None:
    _beam(0, 1000)

    result = cast_ray(Point3D(-100, 500, 50), Point3D(4000, 500, 50))

    assert result.is_empty
    assert not result
    assert result.first is None
    assert result.element_ids == []


def test_radius_widens_a_near_miss_into_a_hit() -> None:
    _beam(0, 1000)
    start, end = Point3D(-100, 150, 50), Point3D(4000, 150, 50)

    assert cast_ray(start, end).is_empty  # y=150 just outside the y<=100 box
    assert not cast_ray(start, end, radius=60).is_empty


def test_among_restricts_the_candidate_set() -> None:
    near = _beam(0, 1000)
    far = _beam(2000, 3000)

    result = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50), among=[near])

    assert result.element_ids == [near.id]
    assert far.id not in result.element_ids


def test_points_by_element_mirrors_the_hits() -> None:
    near = _beam(0, 1000)
    far = _beam(2000, 3000)

    result = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50))
    by_element = result.points_by_element()

    assert set(by_element) == {near.id, far.id}
    assert by_element[near.id] == [Point3D(0, 50, 50), Point3D(1000, 50, 50)]
    assert result.elements == [near, far]
