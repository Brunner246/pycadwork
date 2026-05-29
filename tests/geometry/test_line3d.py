"""Unit tests for pycadwork.geometry.Line3D.

A Line3D is an infinite line in 3D space, defined by a reference point P0
and a unit direction d. The signed scalar parameter t along the line gives
points P(t) = P0 + t * d, so for any query point Q:

  - parameter_at(Q) = (Q - P0) . d   (signed scalar projection)
  - project_point(Q) = P0 + parameter_at(Q) * d   (foot of perpendicular)
  - distance_to_point(Q) = |Q - project_point(Q)|
"""

import math

import pytest

from pycadwork.geometry import Line3D, Point3D, Vector3D

EPS = 1e-9


def check_point(a: Point3D, b: Point3D, eps: float = EPS) -> None:
    assert abs(a.x - b.x) < eps
    assert abs(a.y - b.y) < eps
    assert abs(a.z - b.z) < eps


# ==========================================================================
# Factory construction
# ==========================================================================


class TestFactoryConstruction:
    def test_from_point_and_direction_normalizes(self):
        """A non-unit direction (0,0,5) must be normalized to (0,0,1)."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D(0.0, 0.0, 5.0))
        assert line.direction == Vector3D.unit_z()

    def test_from_point_and_direction_preserves_point(self):
        pt = Point3D(1.0, 2.0, 3.0)
        line = Line3D.from_point_and_direction(pt, Vector3D.unit_x())
        check_point(line.point, pt)

    def test_from_point_and_direction_zero_raises(self):
        with pytest.raises(ValueError):
            Line3D.from_point_and_direction(Point3D.origin(), Vector3D.zero())

    def test_from_two_points_direction_correct(self):
        """Line from (0,0,0) to (3,0,0): direction must be +X."""
        line = Line3D.from_two_points(Point3D.origin(), Point3D(3.0, 0.0, 0.0))
        assert line.direction == Vector3D.unit_x()

    def test_from_two_points_coincident_raises(self):
        p = Point3D(1.0, 2.0, 3.0)
        with pytest.raises(ValueError):
            Line3D.from_two_points(p, p)


# ==========================================================================
# Accessors
# ==========================================================================


class TestAccessors:
    def test_direction_is_unit_vector(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D(3.0, 4.0, 0.0))
        assert line.direction.magnitude() == pytest.approx(1.0)


# ==========================================================================
# Parametric evaluation
# ==========================================================================


class TestParametricEvaluation:
    def test_point_at_zero_returns_reference_point(self):
        line = Line3D.from_point_and_direction(Point3D(1.0, 2.0, 3.0), Vector3D.unit_x())
        check_point(line.point_at(0.0), Point3D(1.0, 2.0, 3.0))

    def test_point_at_advances_along_direction(self):
        """X-axis at origin, t=5 -> (5, 0, 0)."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        check_point(line.point_at(5.0), Point3D(5.0, 0.0, 0.0))

    def test_point_at_negative_goes_backwards(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        check_point(line.point_at(-2.0), Point3D(-2.0, 0.0, 0.0))

    def test_parameter_at_reference_point_is_zero(self):
        line = Line3D.from_point_and_direction(Point3D(1.0, 2.0, 3.0), Vector3D.unit_x())
        assert line.parameter_at(Point3D(1.0, 2.0, 3.0)) == pytest.approx(0.0)

    def test_parameter_at_round_trip(self):
        """parameter_at(point_at(t)) == t for the unit-direction case."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.parameter_at(line.point_at(7.5)) == pytest.approx(7.5)

    def test_parameter_at_behind_reference_is_negative(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.parameter_at(Point3D(-3.0, 0.0, 0.0)) == pytest.approx(-3.0)


# ==========================================================================
# Projection / closest point
# ==========================================================================


class TestProjection:
    def test_project_point_off_line(self):
        """X-axis, query (3,4,0) -> foot of perpendicular at (3,0,0)."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        check_point(line.project_point(Point3D(3.0, 4.0, 0.0)), Point3D(3.0, 0.0, 0.0))

    def test_project_point_on_line_returns_same_point(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        on = Point3D(7.5, 0.0, 0.0)
        check_point(line.project_point(on), on)

    def test_project_point_general_diagonal_line(self):
        """Line through origin along (1,1,0)/sqrt(2); query (1,0,0).

        Projection scalar = (1,0,0) . (1,1,0)/sqrt(2) = 1/sqrt(2).
        Foot = 1/sqrt(2) * (1,1,0)/sqrt(2) = (0.5, 0.5, 0).
        """
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D(1.0, 1.0, 0.0))
        check_point(line.project_point(Point3D(1.0, 0.0, 0.0)), Point3D(0.5, 0.5, 0.0))

    def test_closest_point_equals_project_point(self):
        """Infinite line: closest_point and project_point are the same."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        q = Point3D(3.0, 4.0, 5.0)
        check_point(line.closest_point(q), line.project_point(q))


# ==========================================================================
# Distance
# ==========================================================================


class TestDistance:
    def test_distance_zero_on_line(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.distance_to_point(Point3D(7.5, 0.0, 0.0)) == pytest.approx(0.0)

    def test_distance_perpendicular_offset(self):
        """X-axis; (3,4,0) is 4 units off the line."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.distance_to_point(Point3D(3.0, 4.0, 0.0)) == pytest.approx(4.0)

    def test_distance_3d_offset(self):
        """X-axis; (3,4,12) -> sqrt(4^2 + 12^2) = sqrt(160)."""
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.distance_to_point(Point3D(3.0, 4.0, 12.0)) == pytest.approx(math.sqrt(160.0))

    def test_distance_squared_avoids_sqrt(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.distance_squared_to_point(Point3D(3.0, 4.0, 12.0)) == pytest.approx(160.0)


# ==========================================================================
# Containment
# ==========================================================================


class TestContains:
    def test_contains_point_on_line(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.contains(Point3D(5.0, 0.0, 0.0))

    def test_does_not_contain_off_line_point(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert not line.contains(Point3D(0.0, 0.001, 0.0))

    def test_contains_respects_custom_tolerance(self):
        line = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        assert line.contains(Point3D(0.0, 0.001, 0.0), tolerance=0.01)


# ==========================================================================
# Comparison
# ==========================================================================


class TestComparison:
    def test_eq_same_line_built_from_different_reference_point(self):
        """X-axis through origin == X-axis through (5,0,0): same geometric line."""
        a = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        b = Line3D.from_point_and_direction(Point3D(5.0, 0.0, 0.0), Vector3D.unit_x())
        assert a == b

    def test_eq_opposite_direction_same_line(self):
        a = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        b = Line3D.from_point_and_direction(Point3D.origin(), -Vector3D.unit_x())
        assert a == b

    def test_ne_parallel_distinct_lines(self):
        """Two parallel X-axes at different Y are not the same line."""
        a = Line3D.from_point_and_direction(Point3D(0.0, 0.0, 0.0), Vector3D.unit_x())
        b = Line3D.from_point_and_direction(Point3D(0.0, 1.0, 0.0), Vector3D.unit_x())
        assert a != b

    def test_ne_intersecting_non_parallel_lines(self):
        a = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_x())
        b = Line3D.from_point_and_direction(Point3D.origin(), Vector3D.unit_y())
        assert a != b
