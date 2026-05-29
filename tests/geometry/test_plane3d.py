"""Unit tests for pycadwork.geometry.Plane3D.

A Plane3D is an infinite plane in 3D space, described either as:
  - a point P0 on the plane and a unit normal n, or
  - the implicit equation  ax + by + cz + d = 0
    where (a,b,c) = n  and  d = -n.P0.

Positive signed distance means the query point is on the same side as n;
negative means it is on the opposite side.
"""

import math

import pytest

from pycadwork.geometry import Plane3D, Point3D, Vector3D

EPS = 1e-9


def check_point(a: Point3D, b: Point3D, eps: float = EPS) -> None:
    assert abs(a.x - b.x) < eps
    assert abs(a.y - b.y) < eps
    assert abs(a.z - b.z) < eps


# ==========================================================================
# Factory construction
# ==========================================================================


class TestFactoryConstruction:
    def test_from_default_xy_plane(self):
        """Default plane is XY at z=0, normal=(0,0,1)."""
        p = Plane3D.from_default()
        assert p.normal == Vector3D.unit_z()
        assert p.contains(Point3D.origin())
        assert p.d() == pytest.approx(0.0)

    def test_from_point_and_normal_normalizes(self):
        """A non-unit normal (0,0,5) must be normalized to (0,0,1)."""
        p = Plane3D.from_point_and_normal(Point3D.origin(), Vector3D(0.0, 0.0, 5.0))
        assert p.normal == Vector3D.unit_z()

    def test_from_point_and_normal_contains_point(self):
        pt = Point3D(1.0, 2.0, 3.0)
        p = Plane3D.from_point_and_normal(pt, Vector3D.unit_z())
        assert p.contains(pt)

    def test_from_three_points_right_hand_rule(self):
        """(P2-P1) x (P3-P1) = (1,0,0)x(0,1,0) = (0,0,1) -> normal +Z."""
        p1 = Point3D(0.0, 0.0, 0.0)
        p2 = Point3D(1.0, 0.0, 0.0)
        p3 = Point3D(0.0, 1.0, 0.0)
        plane = Plane3D.from_three_points(p1, p2, p3)
        assert plane.normal == Vector3D.unit_z()

    def test_from_three_points_all_lie_on_plane(self):
        p1 = Point3D(1.0, 0.0, 0.0)
        p2 = Point3D(0.0, 1.0, 0.0)
        p3 = Point3D(0.0, 0.0, 1.0)
        plane = Plane3D.from_three_points(p1, p2, p3)
        assert plane.contains(p1)
        assert plane.contains(p2)
        assert plane.contains(p3)

    def test_from_three_points_collinear_raises(self):
        """Collinear points -> degenerate triangle -> no unique plane."""
        p1 = Point3D(0.0, 0.0, 0.0)
        p2 = Point3D(1.0, 0.0, 0.0)
        p3 = Point3D(2.0, 0.0, 0.0)
        with pytest.raises(ValueError):
            Plane3D.from_three_points(p1, p2, p3)

    def test_from_coefficients_round_trips(self):
        """Build from (1,1,1,-1), extract coefficients, rebuild -- must be equal."""
        plane1 = Plane3D.from_coefficients(1.0, 1.0, 1.0, -1.0)
        coeff = plane1.coefficients()
        plane2 = Plane3D.from_coefficients(*coeff)
        assert plane1 == plane2

    def test_from_coefficients_zero_normal_raises(self):
        with pytest.raises(ValueError):
            Plane3D.from_coefficients(0.0, 0.0, 0.0, 1.0)


# ==========================================================================
# Accessors
# ==========================================================================


class TestAccessors:
    def test_d_xy_plane_at_z5(self):
        """z=5: 0*x + 0*y + 1*z - 5 = 0  ->  d = -5."""
        p = Plane3D.from_point_and_normal(Point3D(0.0, 0.0, 5.0), Vector3D.unit_z())
        assert p.d() == pytest.approx(-5.0)

    def test_coefficients_on_plane_gives_zero(self):
        """ax + by + cz + d = 0 for any on-plane point."""
        p = Plane3D.from_point_and_normal(Point3D(0.0, 0.0, 5.0), Vector3D.unit_z())
        coeff = p.coefficients()
        on_plane = Point3D(3.0, 7.0, 5.0)
        val = coeff[0] * on_plane.x + coeff[1] * on_plane.y + coeff[2] * on_plane.z + coeff[3]
        assert val == pytest.approx(0.0)

    def test_normal_is_always_unit_vector(self):
        p = Plane3D.from_coefficients(3.0, 4.0, 0.0, -5.0)
        assert p.normal.magnitude() == pytest.approx(1.0)


# ==========================================================================
# Signed distance
# ==========================================================================


class TestSignedDistance:
    def test_positive_on_normal_side(self):
        """XY plane at z=0; point at z=3 -> +3."""
        p = Plane3D.from_default()
        assert p.signed_distance_to(Point3D(0.0, 0.0, 3.0)) == pytest.approx(3.0)

    def test_negative_on_opposite_side(self):
        p = Plane3D.from_default()
        assert p.signed_distance_to(Point3D(0.0, 0.0, -4.0)) == pytest.approx(-4.0)

    def test_zero_on_plane(self):
        p = Plane3D.from_default()
        assert p.signed_distance_to(Point3D(5.0, -3.0, 0.0)) == pytest.approx(0.0)

    def test_tilted_plane(self):
        """YZ plane at x=1. Point (4,0,0) -> +3, point (-2,0,0) -> -3."""
        p = Plane3D.from_point_and_normal(Point3D(1.0, 0.0, 0.0), Vector3D.unit_x())
        assert p.signed_distance_to(Point3D(4.0, 0.0, 0.0)) == pytest.approx(3.0)
        assert p.signed_distance_to(Point3D(-2.0, 0.0, 0.0)) == pytest.approx(-3.0)


# ==========================================================================
# Absolute distance
# ==========================================================================


class TestAbsoluteDistance:
    def test_always_non_negative(self):
        p = Plane3D.from_default()
        assert p.distance_to_point(Point3D(0.0, 0.0, 3.0)) == pytest.approx(3.0)
        assert p.distance_to_point(Point3D(0.0, 0.0, -3.0)) == pytest.approx(3.0)

    def test_zero_for_point_on_plane(self):
        p = Plane3D.from_default()
        assert p.distance_to_point(Point3D(2.0, 7.0, 0.0)) == pytest.approx(0.0)


# ==========================================================================
# Point classification
# ==========================================================================


class TestPointClassification:
    def test_contains_true_on_plane(self):
        p = Plane3D.from_default()
        assert p.contains(Point3D(1.0, 2.0, 0.0))

    def test_contains_false_off_plane(self):
        p = Plane3D.from_default()
        assert not p.contains(Point3D(0.0, 0.0, 0.001))

    def test_contains_respects_custom_tolerance(self):
        p = Plane3D.from_default()
        assert p.contains(Point3D(0.0, 0.0, 0.001), 0.01)

    def test_is_above(self):
        p = Plane3D.from_default()
        assert p.is_above(Point3D(0.0, 0.0, 1.0))
        assert not p.is_above(Point3D(0.0, 0.0, -1.0))
        assert not p.is_above(Point3D(0.0, 0.0, 0.0))

    def test_is_below(self):
        p = Plane3D.from_default()
        assert p.is_below(Point3D(0.0, 0.0, -1.0))
        assert not p.is_below(Point3D(0.0, 0.0, 1.0))
        assert not p.is_below(Point3D(0.0, 0.0, 0.0))


# ==========================================================================
# Projection
# ==========================================================================


class TestProjection:
    def test_project_point_onto_xy(self):
        """(3,4,5) projected onto XY -> (3,4,0)."""
        p = Plane3D.from_default()
        proj = p.project_point(Point3D(3.0, 4.0, 5.0))
        check_point(proj, Point3D(3.0, 4.0, 0.0))
        assert p.contains(proj)

    def test_project_point_already_on_plane(self):
        p = Plane3D.from_default()
        on = Point3D(2.0, 3.0, 0.0)
        check_point(p.project_point(on), on)

    def test_project_point_distance_zero_after(self):
        p = Plane3D.from_point_and_normal(Point3D(0.0, 0.0, 2.0), Vector3D.unit_z())
        proj = p.project_point(Point3D(7.0, -5.0, 9.0))
        assert p.distance_to_point(proj) == pytest.approx(0.0)

    def test_project_vector_removes_normal_component(self):
        """(0,0,1) projected onto XY -> (0,0,0)."""
        p = Plane3D.from_default()
        assert p.project_vector(Vector3D.unit_z()).is_zero()

    def test_project_vector_in_plane_unchanged(self):
        p = Plane3D.from_default()
        assert p.project_vector(Vector3D.unit_x()) == Vector3D.unit_x()
        assert p.project_vector(Vector3D.unit_y()) == Vector3D.unit_y()

    def test_project_vector_general_diagonal(self):
        """(1,0,1) onto XY -> (1,0,0)."""
        p = Plane3D.from_default()
        proj = p.project_vector(Vector3D(1.0, 0.0, 1.0))
        assert proj.x == pytest.approx(1.0)
        assert proj.y == pytest.approx(0.0)
        assert proj.z == pytest.approx(0.0)


# ==========================================================================
# Plane relationships
# ==========================================================================


class TestPlaneRelationships:
    def test_is_parallel_to_same_normal_different_height(self):
        p1 = Plane3D.xy(0.0)
        p2 = Plane3D.xy(5.0)
        assert p1.is_parallel_to(p2)

    def test_is_parallel_to_flipped_normal(self):
        """Anti-parallel normals are still parallel."""
        assert Plane3D.xy(0.0).is_parallel_to(Plane3D.xy(0.0).flipped())

    def test_is_parallel_to_perpendicular_planes_false(self):
        assert not Plane3D.xy().is_parallel_to(Plane3D.xz())

    def test_is_perpendicular_to_xy_xz(self):
        """XY (normal Z) and XZ (normal Y): Z.Y = 0."""
        assert Plane3D.xy().is_perpendicular_to(Plane3D.xz())
        assert Plane3D.xy().is_perpendicular_to(Plane3D.yz())
        assert Plane3D.xz().is_perpendicular_to(Plane3D.yz())

    def test_is_perpendicular_parallel_planes_false(self):
        assert not Plane3D.xy(0.0).is_perpendicular_to(Plane3D.xy(5.0))

    def test_is_coplanar_with_self(self):
        p = Plane3D.from_default()
        assert p.is_coplanar_with(p)

    def test_is_coplanar_parallel_but_distinct_false(self):
        assert not Plane3D.xy(0.0).is_coplanar_with(Plane3D.xy(1.0))

    def test_is_coplanar_with_flipped(self):
        p = Plane3D.from_default()
        assert p.is_coplanar_with(p.flipped())

    def test_angle_to_perpendicular(self):
        """Dihedral angle between XY and XZ is 90deg."""
        assert Plane3D.xy().angle_to(Plane3D.xz()) == pytest.approx(math.pi / 2.0)

    def test_angle_to_parallel(self):
        assert Plane3D.xy(0.0).angle_to(Plane3D.xy(5.0)) == pytest.approx(0.0)

    def test_angle_to_anti_parallel(self):
        """Anti-parallel normals -> geometric angle 0."""
        assert Plane3D.xy(0.0).angle_to(Plane3D.xy(0.0).flipped()) == pytest.approx(0.0)

    def test_distance_to_plane_parallel(self):
        p1 = Plane3D.xy(0.0)
        p2 = Plane3D.xy(3.0)
        dist = p1.distance_to_plane(p2)
        assert dist is not None
        assert dist == pytest.approx(3.0)

    def test_distance_to_plane_coplanar(self):
        p = Plane3D.from_default()
        dist = p.distance_to_plane(p)
        assert dist is not None
        assert dist == pytest.approx(0.0)

    def test_distance_to_plane_non_parallel_none(self):
        dist = Plane3D.xy().distance_to_plane(Plane3D.xz())
        assert dist is None


# ==========================================================================
# Line intersection
# ==========================================================================


class TestLineIntersection:
    def test_vertical_ray_hits_xy_at_origin(self):
        """Ray from (0,0,5) in direction (0,0,-1) hits XY at (0,0,0)."""
        plane = Plane3D.from_default()
        hit = plane.intersect_line(Point3D(0.0, 0.0, 5.0), Vector3D(0.0, 0.0, -1.0))
        assert hit is not None
        check_point(hit, Point3D(0.0, 0.0, 0.0))

    def test_tilted_line(self):
        """Line P=(0,0,1) dir=(1,0,-1). t=1 -> hit at (1,0,0)."""
        plane = Plane3D.from_default()
        hit = plane.intersect_line(Point3D(0.0, 0.0, 1.0), Vector3D(1.0, 0.0, -1.0))
        assert hit is not None
        check_point(hit, Point3D(1.0, 0.0, 0.0))

    def test_hit_point_lies_on_plane(self):
        plane = Plane3D.from_point_and_normal(Point3D(0.0, 0.0, 3.0), Vector3D.unit_z())
        hit = plane.intersect_line(Point3D(0.0, 0.0, 0.0), Vector3D(1.0, 1.0, 1.0))
        assert hit is not None
        assert plane.contains(hit)

    def test_parallel_line_returns_none(self):
        """Line in XY plane with no Z component -> no intersection."""
        plane = Plane3D.from_default()
        hit = plane.intersect_line(Point3D(0.0, 0.0, 1.0), Vector3D(1.0, 0.0, 0.0))
        assert hit is None

    def test_intersect_line_parameter_vertical_ray(self):
        """t = n.(P0-linePoint) / n.dir = -2 / -1 = 2."""
        plane = Plane3D.from_default()
        t = plane.intersect_line_parameter(Point3D(0.0, 0.0, 2.0), Vector3D(0.0, 0.0, -1.0))
        assert t is not None
        assert t == pytest.approx(2.0)

    def test_intersect_line_parameter_parallel_none(self):
        plane = Plane3D.from_default()
        t = plane.intersect_line_parameter(Point3D(0.0, 0.0, 1.0), Vector3D(1.0, 0.0, 0.0))
        assert t is None


# ==========================================================================
# Plane transformations
# ==========================================================================


class TestPlaneTransformations:
    def test_offset_along_normal(self):
        """XY at z=0 offset by 3 -> passes through (0,0,3)."""
        p = Plane3D.from_default()
        q = p.offset(3.0)
        assert q.contains(Point3D(0.0, 0.0, 3.0))
        assert q.normal == Vector3D.unit_z()

    def test_offset_negative(self):
        p = Plane3D.from_default()
        q = p.offset(-2.0)
        assert q.contains(Point3D(0.0, 0.0, -2.0))

    def test_offset_round_trip(self):
        p = Plane3D.from_default()
        assert p == p.offset(5.0).offset(-5.0)

    def test_flipped_reverses_normal(self):
        p = Plane3D.from_default()
        f = p.flipped()
        assert f.normal == -Vector3D.unit_z()

    def test_flipped_same_geometric_plane(self):
        """operator== uses is_coplanar_with(), ignoring normal direction."""
        p = Plane3D.from_default()
        assert p == p.flipped()

    def test_double_flip_recovers_original(self):
        p = Plane3D.from_default()
        assert p.flipped().flipped().normal == p.normal


# ==========================================================================
# Static axis-aligned planes
# ==========================================================================


class TestStaticPlanes:
    def test_xy_contains_correct_z(self):
        p = Plane3D.xy(2.0)
        assert p.contains(Point3D(3.0, 4.0, 2.0))
        assert not p.contains(Point3D(0.0, 0.0, 0.0))
        assert p.normal == Vector3D.unit_z()

    def test_xz_contains_correct_y(self):
        p = Plane3D.xz(1.0)
        assert p.contains(Point3D(3.0, 1.0, 4.0))
        assert p.normal == Vector3D.unit_y()

    def test_yz_contains_correct_x(self):
        p = Plane3D.yz(2.0)
        assert p.contains(Point3D(2.0, 5.0, 6.0))
        assert p.normal == Vector3D.unit_x()

    def test_mutually_perpendicular(self):
        assert Plane3D.xy().is_perpendicular_to(Plane3D.xz())
        assert Plane3D.xy().is_perpendicular_to(Plane3D.yz())
        assert Plane3D.xz().is_perpendicular_to(Plane3D.yz())


# ==========================================================================
# Comparison
# ==========================================================================


class TestComparison:
    def test_eq_same_plane_different_factories(self):
        p1 = Plane3D.from_default()
        p2 = Plane3D.from_coefficients(0.0, 0.0, 1.0, 0.0)
        assert p1 == p2

    def test_ne_parallel_different_heights(self):
        assert Plane3D.xy(0.0) != Plane3D.xy(1.0)

    def test_eq_self(self):
        p = Plane3D.from_default()
        assert p == p

    def test_eq_flipped_equals_original(self):
        p = Plane3D.from_default()
        assert p == p.flipped()


# ==========================================================================
# String output
# ==========================================================================


class TestStringOutput:
    def test_repr_starts_with_plane3d(self):
        s = repr(Plane3D.from_default())
        assert "Plane3D(" in s

    def test_repr_contains_equals_zero(self):
        s = repr(Plane3D.from_default())
        assert "= 0" in s
