"""Unit tests for pycadwork.geometry.Vector3D.

A Vector3D has direction and magnitude.  It differs from Point3D in that
translation does not apply to vectors -- only rotation/scaling.

Test groups
-----------
Construction
  Default constructor yields the zero vector (0,0,0).
  Component-wise constructor stores x/y/z exactly.
  Two-point constructor computes the displacement vector P2 - P1.

Static factory helpers
  zero(), unit_x(), unit_y(), unit_z() return the expected constant vectors.

Arithmetic operators
  +, -, unary -, *, / (scalar on both sides), compound assignments.
  Division by a near-zero scalar must raise ValueError.

Comparison
  == / != use an internal epsilon of 1e-10.

Dot product  (a . b = |a||b|cos theta)
  Perpendicular unit vectors -> 0.
  Parallel unit vectors -> 1.
  General case verified by hand.

Cross product  (a x b = |a||b|sin theta . n)
  Right-hand rule: unit_x x unit_y = unit_z.
  Anti-commutativity: a x b = -(b x a).
  Parallel vectors -> zero vector.
  General case verified by hand.

Magnitude
  magnitude() of a unit vector is 1.
  3-4-0 Pythagorean triple -> magnitude 5.

Normalisation
  normalized() returns a unit vector without modifying the original.
  normalize() modifies in place.
  Both raise ValueError for the zero vector.
  is_normalized() / is_zero() query helpers.

Angle
  angle_to() uses arccos(a.b / |a||b|), clamped for numerical safety.
  Perpendicular -> pi/2, parallel -> 0, anti-parallel -> pi.

Projection
  project_onto() decomposes this vector along another.
  Projecting onto a perpendicular axis gives the zero vector.

String output
  repr/str emits "Vector3D(x, y, z)".
"""

import math

import pytest

from pycadwork.geometry import Point3D, Vector3D


def approx_eq(a: float, b: float, eps: float = 1e-9) -> bool:
    return abs(a - b) < eps


# ==========================================================================
# Construction
# ==========================================================================


class TestConstruction:
    def test_default_constructor_produces_the_zero_vector(self):
        """The zero vector is the additive identity: v + zero = v."""
        v = Vector3D()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_component_constructor_stores_values(self):
        v = Vector3D(1.0, 2.0, 3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_two_point_constructor_computes_displacement(self):
        """The vector from P1=(1,2,3) to P2=(4,6,9) is (3,4,6)."""
        from_pt = Point3D(1.0, 2.0, 3.0)
        to_pt = Point3D(4.0, 6.0, 9.0)
        v = Vector3D.from_two_points(from_pt, to_pt)
        assert v.x == pytest.approx(3.0)
        assert v.y == pytest.approx(4.0)
        assert v.z == pytest.approx(6.0)


# ==========================================================================
# Static factory helpers
# ==========================================================================


class TestStaticFactories:
    def test_zero_is_the_zero_vector(self):
        v = Vector3D.zero()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_unit_x_is_1_0_0(self):
        v = Vector3D.unit_x()
        assert v.x == 1.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_unit_y_is_0_1_0(self):
        v = Vector3D.unit_y()
        assert v.x == 0.0
        assert v.y == 1.0
        assert v.z == 0.0

    def test_unit_z_is_0_0_1(self):
        v = Vector3D.unit_z()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 1.0


# ==========================================================================
# Arithmetic operators
# ==========================================================================


class TestArithmetic:
    def test_add_component_wise(self):
        a = Vector3D(1.0, 2.0, 3.0)
        b = Vector3D(4.0, 5.0, 6.0)
        c = a + b
        assert c.x == pytest.approx(5.0)
        assert c.y == pytest.approx(7.0)
        assert c.z == pytest.approx(9.0)

    def test_sub_component_wise(self):
        a = Vector3D(4.0, 5.0, 6.0)
        b = Vector3D(1.0, 2.0, 3.0)
        c = a - b
        assert c.x == pytest.approx(3.0)
        assert c.y == pytest.approx(3.0)
        assert c.z == pytest.approx(3.0)

    def test_unary_neg_flips_all_components(self):
        a = Vector3D(1.0, -2.0, 3.0)
        b = -a
        assert b.x == pytest.approx(-1.0)
        assert b.y == pytest.approx(2.0)
        assert b.z == pytest.approx(-3.0)

    def test_mul_vector_times_scalar(self):
        a = Vector3D(1.0, 2.0, 3.0)
        b = a * 3.0
        assert b.x == pytest.approx(3.0)
        assert b.y == pytest.approx(6.0)
        assert b.z == pytest.approx(9.0)

    def test_mul_scalar_times_vector(self):
        a = Vector3D(1.0, 2.0, 3.0)
        b = 3.0 * a
        assert b.x == pytest.approx(3.0)
        assert b.y == pytest.approx(6.0)
        assert b.z == pytest.approx(9.0)

    def test_div_by_scalar(self):
        a = Vector3D(3.0, 6.0, 9.0)
        b = a / 3.0
        assert b.x == pytest.approx(1.0)
        assert b.y == pytest.approx(2.0)
        assert b.z == pytest.approx(3.0)

    def test_div_by_near_zero_raises(self):
        """Division by |scalar| < 1e-15 raises ValueError."""
        a = Vector3D(1.0, 0.0, 0.0)
        with pytest.raises(ValueError):
            a / 1e-16

    def test_iadd_modifies_in_place(self):
        a = Vector3D(1.0, 2.0, 3.0)
        a += Vector3D(1.0, 1.0, 1.0)
        assert a.x == pytest.approx(2.0)
        assert a.y == pytest.approx(3.0)
        assert a.z == pytest.approx(4.0)

    def test_isub_modifies_in_place(self):
        a = Vector3D(3.0, 3.0, 3.0)
        a -= Vector3D(1.0, 2.0, 3.0)
        assert a.x == pytest.approx(2.0)
        assert a.y == pytest.approx(1.0)
        assert a.z == pytest.approx(0.0)

    def test_imul_modifies_in_place(self):
        a = Vector3D(1.0, 2.0, 3.0)
        a *= 2.0
        assert a.x == pytest.approx(2.0)
        assert a.y == pytest.approx(4.0)
        assert a.z == pytest.approx(6.0)

    def test_itruediv_modifies_in_place(self):
        a = Vector3D(2.0, 4.0, 6.0)
        a /= 2.0
        assert a.x == pytest.approx(1.0)
        assert a.y == pytest.approx(2.0)
        assert a.z == pytest.approx(3.0)

    def test_itruediv_by_near_zero_raises(self):
        a = Vector3D(1.0, 0.0, 0.0)
        with pytest.raises(ValueError):
            a /= 0.0


# ==========================================================================
# Comparison
# ==========================================================================


class TestComparison:
    def test_eq_identical_vectors(self):
        assert Vector3D(1.0, 2.0, 3.0) == Vector3D(1.0, 2.0, 3.0)

    def test_eq_within_epsilon(self):
        """Component-wise |a - b| < 1e-10."""
        tiny = 5e-11
        assert Vector3D(1.0, 1.0, 1.0) == Vector3D(1.0 + tiny, 1.0 + tiny, 1.0 + tiny)

    def test_ne_clearly_different(self):
        assert Vector3D(1.0, 0.0, 0.0) != Vector3D(0.0, 1.0, 0.0)


# ==========================================================================
# Dot product
# ==========================================================================


class TestDotProduct:
    def test_perpendicular_unit_vectors_give_zero(self):
        """a . b = |a||b|cos(theta).  For theta = 90deg, cos(90) = 0."""
        assert Vector3D.unit_x().dot(Vector3D.unit_y()) == pytest.approx(0.0)
        assert Vector3D.unit_y().dot(Vector3D.unit_z()) == pytest.approx(0.0)
        assert Vector3D.unit_z().dot(Vector3D.unit_x()) == pytest.approx(0.0)

    def test_unit_vector_with_itself_gives_one(self):
        assert Vector3D.unit_x().dot(Vector3D.unit_x()) == pytest.approx(1.0)

    def test_general_case(self):
        """1*4 + 2*5 + 3*6 = 32."""
        assert Vector3D(1.0, 2.0, 3.0).dot(Vector3D(4.0, 5.0, 6.0)) == pytest.approx(32.0)

    def test_commutative(self):
        a = Vector3D(1.0, 2.0, 3.0)
        b = Vector3D(7.0, -3.0, 0.5)
        assert a.dot(b) == pytest.approx(b.dot(a))


# ==========================================================================
# Cross product
# ==========================================================================


class TestCrossProduct:
    def test_right_hand_rule(self):
        """X x Y = Z, Y x Z = X, Z x X = Y."""
        assert Vector3D.unit_x().cross(Vector3D.unit_y()) == Vector3D.unit_z()
        assert Vector3D.unit_y().cross(Vector3D.unit_z()) == Vector3D.unit_x()
        assert Vector3D.unit_z().cross(Vector3D.unit_x()) == Vector3D.unit_y()

    def test_anti_commutative(self):
        a = Vector3D(1.0, 2.0, 3.0)
        b = Vector3D(4.0, 5.0, 6.0)
        assert a.cross(b) == -(b.cross(a))

    def test_parallel_vectors_produce_zero(self):
        """Parallel vectors span a degenerate plane."""
        a = Vector3D(2.0, 0.0, 0.0)
        b = Vector3D(5.0, 0.0, 0.0)
        assert a.cross(b).is_zero()

    def test_general_case(self):
        """(1,2,3) x (4,5,6) = (-3, 6, -3)."""
        c = Vector3D(1.0, 2.0, 3.0).cross(Vector3D(4.0, 5.0, 6.0))
        assert c.x == pytest.approx(-3.0)
        assert c.y == pytest.approx(6.0)
        assert c.z == pytest.approx(-3.0)

    def test_result_perpendicular_to_both_operands(self):
        a = Vector3D(1.0, 2.0, 0.0)
        b = Vector3D(3.0, 0.0, 4.0)
        c = a.cross(b)
        assert approx_eq(c.dot(a), 0.0)
        assert approx_eq(c.dot(b), 0.0)


# ==========================================================================
# Magnitude
# ==========================================================================


class TestMagnitude:
    def test_unit_vector_has_magnitude_one(self):
        assert Vector3D.unit_x().magnitude() == pytest.approx(1.0)

    def test_pythagorean_triple(self):
        assert Vector3D(3.0, 4.0, 0.0).magnitude() == pytest.approx(5.0)

    def test_zero_vector_has_magnitude_zero(self):
        assert Vector3D.zero().magnitude() == pytest.approx(0.0)


# ==========================================================================
# Normalisation
# ==========================================================================


class TestNormalisation:
    def test_normalized_produces_unit_vector_original_unchanged(self):
        v = Vector3D(3.0, 4.0, 0.0)
        n = v.normalized()
        assert n.magnitude() == pytest.approx(1.0)
        assert n.x == pytest.approx(0.6)
        assert n.y == pytest.approx(0.8)
        assert n.z == pytest.approx(0.0)
        assert v.x == 3.0

    def test_normalize_modifies_in_place(self):
        v = Vector3D(0.0, 0.0, 5.0)
        v.normalize()
        assert v == Vector3D.unit_z()

    def test_normalized_raises_for_zero_vector(self):
        with pytest.raises(ValueError):
            Vector3D.zero().normalized()

    def test_normalize_raises_for_zero_vector(self):
        v = Vector3D()
        with pytest.raises(ValueError):
            v.normalize()

    def test_is_normalized_true_for_unit_vectors(self):
        assert Vector3D.unit_x().is_normalized()
        assert Vector3D.unit_y().is_normalized()
        assert Vector3D.unit_z().is_normalized()

    def test_is_normalized_false_for_non_unit(self):
        assert not Vector3D(2.0, 0.0, 0.0).is_normalized()
        assert not Vector3D.zero().is_normalized()


# ==========================================================================
# is_zero
# ==========================================================================


class TestIsZero:
    def test_true_for_zero_vector(self):
        assert Vector3D.zero().is_zero()

    def test_true_for_near_zero(self):
        assert Vector3D(1e-11, 1e-11, 1e-11).is_zero()

    def test_false_for_non_zero(self):
        assert not Vector3D.unit_x().is_zero()
        assert not Vector3D(1e-5, 0.0, 0.0).is_zero()


# ==========================================================================
# Angle between vectors
# ==========================================================================


class TestAngle:
    def test_perpendicular_gives_pi_over_2(self):
        """arccos(0) = pi/2."""
        angle = Vector3D.unit_x().angle_to(Vector3D.unit_y())
        assert angle == pytest.approx(math.pi / 2.0)

    def test_parallel_gives_zero(self):
        assert Vector3D.unit_x().angle_to(Vector3D.unit_x()) == pytest.approx(0.0)

    def test_anti_parallel_gives_pi(self):
        angle = Vector3D.unit_x().angle_to(-Vector3D.unit_x())
        assert angle == pytest.approx(math.pi)

    def test_symmetric(self):
        a = Vector3D(1.0, 2.0, 0.0)
        b = Vector3D(3.0, -1.0, 0.0)
        assert a.angle_to(b) == pytest.approx(b.angle_to(a))


# ==========================================================================
# Projection
# ==========================================================================


class TestProjection:
    def test_project_onto_self(self):
        v = Vector3D(3.0, 0.0, 0.0)
        assert v.project_onto(Vector3D.unit_x()) == v

    def test_project_onto_perpendicular_gives_zero(self):
        """(0,1,0) has no component along (1,0,0)."""
        result = Vector3D.unit_y().project_onto(Vector3D.unit_x())
        assert result.is_zero()

    def test_general_case(self):
        """(1,1,0) projected onto unit_x = (1,0,0)."""
        proj = Vector3D(1.0, 1.0, 0.0).project_onto(Vector3D.unit_x())
        assert proj.x == pytest.approx(1.0)
        assert proj.y == pytest.approx(0.0)
        assert proj.z == pytest.approx(0.0)

    def test_non_unit_target(self):
        """(2,0,0) projected onto (3,0,0) = (2,0,0)."""
        v = Vector3D(2.0, 0.0, 0.0)
        onto = Vector3D(3.0, 0.0, 0.0)
        proj = v.project_onto(onto)
        assert proj.x == pytest.approx(2.0)
        assert proj.y == pytest.approx(0.0)
        assert proj.z == pytest.approx(0.0)


# ==========================================================================
# String output
# ==========================================================================


class TestStringOutput:
    def test_repr_starts_with_vector3d(self):
        s = repr(Vector3D(1.0, 2.0, 3.0))
        assert "Vector3D(" in s

    def test_repr_contains_all_components(self):
        s = repr(Vector3D(1.0, 2.0, 3.0))
        assert "1" in s
        assert "2" in s
        assert "3" in s
