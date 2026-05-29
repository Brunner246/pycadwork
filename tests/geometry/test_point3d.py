"""Unit tests for pycadwork.geometry.Point3D.

A Point3D represents an absolute position in 3D space.  Unlike Vector3D,
a point does not have a magnitude; instead it participates in these
fundamental operations:

  Point + Vector  ->  Point   (translate a position by a displacement)
  Point - Vector  ->  Point   (translate in the opposite direction)
  Point - Point   ->  Vector  (displacement between two positions)

Test groups
-----------
Construction
  Default constructor yields the origin (0,0,0).
  Component-wise constructor stores x/y/z exactly.
  origin() factory returns Point3D(0,0,0).

Arithmetic with Vector3D
  operator+ / operator- translate the point; verify component results.
  operator+= / operator-= modify the point in place.

Point difference -> Vector
  P1 - P2 produces the displacement vector from P2 to P1.
  A point minus itself yields the zero vector.

Comparison
  == / != use an internal epsilon of 1e-10 per component.

Distance
  distance_to() is the Euclidean distance, always non-negative.
  distance_squared_to() avoids the sqrt -- faster for comparisons.
  Both are symmetric and return 0 for the same point.

String output
  repr/str emits "Point3D(x, y, z)".
"""

import pytest

from pycadwork.geometry import Point3D, Vector3D


# ==========================================================================
# Construction
# ==========================================================================


class TestConstruction:
    def test_default_constructor_is_origin(self):
        p = Point3D()
        assert p.x == 0.0
        assert p.y == 0.0
        assert p.z == 0.0

    def test_component_constructor_stores_values(self):
        p = Point3D(1.0, 2.0, 3.0)
        assert p.x == 1.0
        assert p.y == 2.0
        assert p.z == 3.0

    def test_origin_factory_returns_000(self):
        assert Point3D.origin() == Point3D(0.0, 0.0, 0.0)


# ==========================================================================
# Arithmetic with Vector3D
# ==========================================================================


class TestArithmetic:
    def test_point_plus_vector_displaces(self):
        """P(1,2,3) + V(1,1,1) = P(2,3,4)."""
        p = Point3D(1.0, 2.0, 3.0)
        v = Vector3D(1.0, 1.0, 1.0)
        q = p + v
        assert q.x == pytest.approx(2.0)
        assert q.y == pytest.approx(3.0)
        assert q.z == pytest.approx(4.0)

    def test_point_minus_vector_displaces_opposite(self):
        p = Point3D(3.0, 3.0, 3.0)
        v = Vector3D(1.0, 2.0, 3.0)
        q = p - v
        assert q.x == pytest.approx(2.0)
        assert q.y == pytest.approx(1.0)
        assert q.z == pytest.approx(0.0)

    def test_iadd_modifies_in_place(self):
        p = Point3D(1.0, 1.0, 1.0)
        p += Vector3D(2.0, 3.0, 4.0)
        assert p.x == pytest.approx(3.0)
        assert p.y == pytest.approx(4.0)
        assert p.z == pytest.approx(5.0)

    def test_isub_modifies_in_place(self):
        p = Point3D(5.0, 5.0, 5.0)
        p -= Vector3D(1.0, 2.0, 3.0)
        assert p.x == pytest.approx(4.0)
        assert p.y == pytest.approx(3.0)
        assert p.z == pytest.approx(2.0)

    def test_arithmetic_does_not_modify_vector_operand(self):
        p = Point3D(0.0, 0.0, 0.0)
        v = Vector3D(1.0, 2.0, 3.0)
        _ = p + v
        _ = p - v
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0


# ==========================================================================
# Point difference -> Vector
# ==========================================================================


class TestPointDifference:
    def test_point_minus_point_yields_displacement(self):
        """The vector from P1=(1,2,3) to P2=(4,6,8) is (3,4,5)."""
        p1 = Point3D(1.0, 2.0, 3.0)
        p2 = Point3D(4.0, 6.0, 8.0)
        v = p2 - p1
        assert v.x == pytest.approx(3.0)
        assert v.y == pytest.approx(4.0)
        assert v.z == pytest.approx(5.0)

    def test_point_minus_itself_is_zero_vector(self):
        p = Point3D(7.0, 8.0, 9.0)
        v = p - p
        assert v.is_zero()

    def test_displacement_round_trip(self):
        """P1 + (P2 - P1) == P2."""
        p1 = Point3D(1.0, 2.0, 3.0)
        p2 = Point3D(5.0, -1.0, 7.0)
        recovered = p1 + (p2 - p1)
        assert recovered == p2


# ==========================================================================
# Comparison
# ==========================================================================


class TestComparison:
    def test_eq_identical(self):
        assert Point3D(1.0, 2.0, 3.0) == Point3D(1.0, 2.0, 3.0)

    def test_eq_within_epsilon(self):
        """Component-wise |a - b| < 1e-10."""
        tiny = 5e-11
        assert Point3D(0.0, 0.0, 0.0) == Point3D(tiny, tiny, tiny)

    def test_eq_beyond_epsilon_compares_unequal(self):
        just_over = 2e-10
        assert not (Point3D(0.0, 0.0, 0.0) == Point3D(just_over, 0.0, 0.0))

    def test_ne_clearly_different(self):
        assert Point3D(1.0, 0.0, 0.0) != Point3D(0.0, 1.0, 0.0)


# ==========================================================================
# Distance
# ==========================================================================


class TestDistance:
    def test_pythagorean_triple_3_4_0(self):
        """|(0,0,0) - (3,4,0)| = 5."""
        a = Point3D(0.0, 0.0, 0.0)
        b = Point3D(3.0, 4.0, 0.0)
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_3d_pythagorean_triple(self):
        """|(0,0,0) - (1,2,2)| = 3."""
        assert Point3D.origin().distance_to(Point3D(1.0, 2.0, 2.0)) == pytest.approx(3.0)

    def test_symmetric(self):
        a = Point3D(1.0, 2.0, 3.0)
        b = Point3D(4.0, 5.0, 6.0)
        assert a.distance_to(b) == pytest.approx(b.distance_to(a))

    def test_point_to_itself_is_zero(self):
        p = Point3D(5.0, 6.0, 7.0)
        assert p.distance_to(p) == pytest.approx(0.0)

    def test_distance_squared_to(self):
        """|delta|^2 = 3^2 + 3^2 + 3^2 = 27."""
        a = Point3D(1.0, 2.0, 3.0)
        b = Point3D(4.0, 5.0, 6.0)
        assert a.distance_squared_to(b) == pytest.approx(27.0)

    def test_distance_squared_consistent_with_distance(self):
        a = Point3D(2.0, 3.0, 4.0)
        b = Point3D(6.0, 6.0, 4.0)
        d = a.distance_to(b)
        assert a.distance_squared_to(b) == pytest.approx(d * d)


# ==========================================================================
# String output
# ==========================================================================


class TestStringOutput:
    def test_repr_starts_with_point3d(self):
        s = repr(Point3D(1.0, 2.0, 3.0))
        assert "Point3D(" in s

    def test_repr_contains_all_components(self):
        s = repr(Point3D(1.0, 2.0, 3.0))
        assert "1" in s
        assert "2" in s
        assert "3" in s
