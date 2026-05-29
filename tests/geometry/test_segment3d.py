"""Unit tests for pycadwork.geometry.Segment3D.

A Segment3D is a bounded line segment with two endpoints p1 and p2. The
parameter t maps t=0 -> p1, t=1 -> p2 (unclamped via point_at / parameter_at).
The closest_point operation clamps t to [0, 1] -- this is the key behavioral
difference from Line3D.
"""

import math

import pytest

from pycadwork.geometry import Line3D, Point3D, Segment3D, Vector3D

EPS = 1e-9


def check_point(a: Point3D, b: Point3D, eps: float = EPS) -> None:
    assert abs(a.x - b.x) < eps
    assert abs(a.y - b.y) < eps
    assert abs(a.z - b.z) < eps


# ==========================================================================
# Factory construction
# ==========================================================================


class TestFactoryConstruction:
    def test_from_two_points_preserves_endpoints(self):
        seg = Segment3D.from_two_points(Point3D(1.0, 2.0, 3.0), Point3D(4.0, 5.0, 6.0))
        check_point(seg.p1, Point3D(1.0, 2.0, 3.0))
        check_point(seg.p2, Point3D(4.0, 5.0, 6.0))

    def test_from_two_points_coincident_raises(self):
        p = Point3D(1.0, 2.0, 3.0)
        with pytest.raises(ValueError):
            Segment3D.from_two_points(p, p)

    def test_from_point_and_vector_builds_endpoint(self):
        seg = Segment3D.from_point_and_vector(Point3D(1.0, 0.0, 0.0), Vector3D(2.0, 0.0, 0.0))
        check_point(seg.p2, Point3D(3.0, 0.0, 0.0))

    def test_from_point_and_vector_zero_raises(self):
        with pytest.raises(ValueError):
            Segment3D.from_point_and_vector(Point3D.origin(), Vector3D.zero())


# ==========================================================================
# Derived quantities
# ==========================================================================


class TestDerivedQuantities:
    def test_length_canonical(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.length() == pytest.approx(2.0)

    def test_length_squared(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(3.0, 4.0, 0.0))
        assert seg.length_squared() == pytest.approx(25.0)

    def test_direction_is_unit_p1_to_p2(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(0.0, 5.0, 0.0))
        assert seg.direction() == Vector3D.unit_y()

    def test_midpoint(self):
        seg = Segment3D.from_two_points(Point3D(0.0, 0.0, 0.0), Point3D(2.0, 4.0, 6.0))
        check_point(seg.midpoint(), Point3D(1.0, 2.0, 3.0))


# ==========================================================================
# Parametric evaluation (unclamped)
# ==========================================================================


class TestParametricEvaluation:
    def test_point_at_zero_returns_p1(self):
        seg = Segment3D.from_two_points(Point3D(1.0, 2.0, 3.0), Point3D(4.0, 5.0, 6.0))
        check_point(seg.point_at(0.0), seg.p1)

    def test_point_at_one_returns_p2(self):
        seg = Segment3D.from_two_points(Point3D(1.0, 2.0, 3.0), Point3D(4.0, 5.0, 6.0))
        check_point(seg.point_at(1.0), seg.p2)

    def test_point_at_half_returns_midpoint(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 4.0, 6.0))
        check_point(seg.point_at(0.5), Point3D(1.0, 2.0, 3.0))

    def test_point_at_extrapolates_outside_unit_interval(self):
        """point_at is unclamped: t=2 on a 0..2 segment yields (4, 0, 0)."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        check_point(seg.point_at(2.0), Point3D(4.0, 0.0, 0.0))

    def test_parameter_at_unclamped_before_p1(self):
        """Query at (-2, 0, 0) on a [0..2] segment -> t = -1.0 (unclamped)."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.parameter_at(Point3D(-2.0, 0.0, 0.0)) == pytest.approx(-1.0)

    def test_parameter_at_unclamped_after_p2(self):
        """Query at (4, 0, 0) on a [0..2] segment -> t = 2.0 (unclamped)."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.parameter_at(Point3D(4.0, 0.0, 0.0)) == pytest.approx(2.0)

    def test_parameter_at_endpoint_perpendicular_projection(self):
        """(5, 3, 0) projects to t=2.5 on [(0,0,0), (2,0,0)] segment."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.parameter_at(Point3D(5.0, 3.0, 0.0)) == pytest.approx(2.5)


# ==========================================================================
# Closest point (clamped)
# ==========================================================================


class TestClosestPoint:
    def test_orthogonal_query_inside_returns_foot(self):
        """(1, 3, 0) on [(0,0,0), (2,0,0)] -> foot (1, 0, 0)."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        check_point(seg.closest_point(Point3D(1.0, 3.0, 0.0)), Point3D(1.0, 0.0, 0.0))

    def test_query_past_p1_clamps_to_p1(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        check_point(seg.closest_point(Point3D(-5.0, 3.0, 0.0)), Point3D.origin())

    def test_query_past_p2_clamps_to_p2(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        check_point(seg.closest_point(Point3D(5.0, 3.0, 0.0)), Point3D(2.0, 0.0, 0.0))

    def test_query_exactly_at_p1_returns_p1(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        check_point(seg.closest_point(Point3D.origin()), Point3D.origin())

    def test_query_on_segment_returns_itself(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        on = Point3D(1.0, 0.0, 0.0)
        check_point(seg.closest_point(on), on)


# ==========================================================================
# Distance (clamped)
# ==========================================================================


class TestDistance:
    def test_distance_uses_clamped_foot_past_p2(self):
        """(5, 1, 0) past p2=(2,0,0): distance is hypot(3, 1), NOT 1 (the line distance)."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.distance_to_point(Point3D(5.0, 1.0, 0.0)) == pytest.approx(math.hypot(3.0, 1.0))

    def test_distance_uses_clamped_foot_past_p1(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.distance_to_point(Point3D(-4.0, 3.0, 0.0)) == pytest.approx(5.0)

    def test_distance_inside_uses_perpendicular(self):
        """(1, 4, 0) directly above midpoint -> distance 4."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.distance_to_point(Point3D(1.0, 4.0, 0.0)) == pytest.approx(4.0)

    def test_distance_zero_on_segment(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.distance_to_point(Point3D(1.0, 0.0, 0.0)) == pytest.approx(0.0)

    def test_distance_squared_avoids_sqrt(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.distance_squared_to_point(Point3D(5.0, 1.0, 0.0)) == pytest.approx(10.0)


# ==========================================================================
# Containment
# ==========================================================================


class TestContains:
    def test_contains_point_on_segment(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.contains(Point3D(1.0, 0.0, 0.0))

    def test_does_not_contain_off_segment(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert not seg.contains(Point3D(1.0, 0.001, 0.0))

    def test_does_not_contain_collinear_but_outside_segment(self):
        """Point on the infinite line but past p2 is NOT on the bounded segment."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert not seg.contains(Point3D(5.0, 0.0, 0.0))

    def test_contains_respects_custom_tolerance(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert seg.contains(Point3D(1.0, 0.001, 0.0), tolerance=0.01)


# ==========================================================================
# Bridge to infinite line
# ==========================================================================


class TestToLine:
    def test_to_line_returns_line_through_endpoints(self):
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        line = seg.to_line()
        assert isinstance(line, Line3D)
        assert line.contains(seg.p1)
        assert line.contains(seg.p2)

    def test_to_line_unclamped_projection_can_lie_outside_segment(self):
        """Past-p2 query: segment clamps to p2, but the line foot extrapolates."""
        seg = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        line = seg.to_line()
        query = Point3D(5.0, 3.0, 0.0)
        check_point(line.project_point(query), Point3D(5.0, 0.0, 0.0))
        check_point(seg.closest_point(query), Point3D(2.0, 0.0, 0.0))


# ==========================================================================
# Comparison
# ==========================================================================


class TestComparison:
    def test_eq_same_endpoints_same_order(self):
        a = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        b = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        assert a == b

    def test_eq_endpoints_swapped(self):
        """Segments are direction-insensitive for equality."""
        a = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        b = Segment3D.from_two_points(Point3D(2.0, 0.0, 0.0), Point3D.origin())
        assert a == b

    def test_ne_different_endpoints(self):
        a = Segment3D.from_two_points(Point3D.origin(), Point3D(2.0, 0.0, 0.0))
        b = Segment3D.from_two_points(Point3D.origin(), Point3D(3.0, 0.0, 0.0))
        assert a != b
