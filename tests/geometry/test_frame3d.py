"""Unit tests for pycadwork.geometry.Frame3D.

A Frame3D is a right-handed 3D coordinate system consisting of:
  - an origin Point3D  (translation)
  - three orthonormal axis vectors X, Y, Z  (rotation)

Coordinate transformations project the displacement onto each axis via dot
product.

Coordinate transformation conventions
--------------------------------------
  world_to_local(P)  -- expresses a world-space point in frame-local coords.
  local_to_world(P)  -- reconstructs the world position from local coords.

The round-trip local_to_world(world_to_local(P)) must equal P.
"""

import math

import pytest

from pycadwork.geometry import Frame3D, Point3D, Vector3D

EPS = 1e-9


def check_point(a: Point3D, b: Point3D, eps: float = EPS) -> None:
    assert abs(a.x - b.x) < eps
    assert abs(a.y - b.y) < eps
    assert abs(a.z - b.z) < eps


def check_vector(a: Vector3D, b: Vector3D, eps: float = EPS) -> None:
    assert abs(a.x - b.x) < eps
    assert abs(a.y - b.y) < eps
    assert abs(a.z - b.z) < eps


# ==========================================================================
# Construction
# ==========================================================================


class TestConstruction:
    def test_default_constructor_creates_world_frame(self):
        """Origin at (0,0,0), axes aligned with world X, Y, Z."""
        f = Frame3D()
        assert f.origin == Point3D.origin()
        assert f.axis_x == Vector3D.unit_x()
        assert f.axis_y == Vector3D.unit_y()
        assert f.axis_z == Vector3D.unit_z()

    def test_world_frame_returns_identity(self):
        f = Frame3D.world_frame()
        assert f.origin == Point3D.origin()
        assert f.axis_x == Vector3D.unit_x()
        assert f.axis_y == Vector3D.unit_y()
        assert f.axis_z == Vector3D.unit_z()

    def test_three_axis_constructor_normalizes(self):
        """Non-unit axis vectors should be normalized."""
        f = Frame3D(
            Point3D(1.0, 0.0, 0.0),
            Vector3D(2.0, 0.0, 0.0),
            Vector3D(0.0, 3.0, 0.0),
            Vector3D(0.0, 0.0, 5.0),
        )
        check_vector(f.axis_x, Vector3D.unit_x())
        check_vector(f.axis_y, Vector3D.unit_y())
        check_vector(f.axis_z, Vector3D.unit_z())

    def test_two_axis_constructor_derives_z(self):
        """Z = normalize(X x Y).  For X=(1,0,0) Y=(0,1,0), Z=(0,0,1)."""
        f = Frame3D(Point3D.origin(), Vector3D.unit_x(), Vector3D.unit_y())
        check_vector(f.axis_z, Vector3D.unit_z())

    def test_two_axis_constructor_45_degree(self):
        """45-degree rotation in XY plane should still yield orthonormal frame."""
        c = math.cos(math.pi / 4.0)
        s = math.sin(math.pi / 4.0)
        f = Frame3D(
            Point3D.origin(),
            Vector3D(c, s, 0.0),
            Vector3D(-s, c, 0.0),
        )
        assert f.is_orthonormal()
        check_vector(f.axis_z, Vector3D.unit_z())


# ==========================================================================
# isOrthonormal
# ==========================================================================


class TestIsOrthonormal:
    def test_default_frame_passes(self):
        assert Frame3D().is_orthonormal()

    def test_frame_from_unit_axes_passes(self):
        f = Frame3D(
            Point3D(5.0, 3.0, -2.0),
            Vector3D.unit_x(),
            Vector3D.unit_y(),
            Vector3D.unit_z(),
        )
        assert f.is_orthonormal()


# ==========================================================================
# worldToLocal / localToWorld -- identity (world) frame
# ==========================================================================


class TestIdentityTransformations:
    def test_world_to_local_identity_point(self):
        world = Frame3D()
        p = Point3D(3.0, 4.0, 5.0)
        check_point(world.world_to_local(p), p)

    def test_local_to_world_identity_point(self):
        world = Frame3D()
        p = Point3D(3.0, 4.0, 5.0)
        check_point(world.local_to_world(p), p)

    def test_world_to_local_identity_vector(self):
        world = Frame3D()
        v = Vector3D(1.0, -2.0, 3.0)
        check_vector(world.world_to_local(v), v)

    def test_local_to_world_identity_vector(self):
        world = Frame3D()
        v = Vector3D(1.0, -2.0, 3.0)
        check_vector(world.local_to_world(v), v)


# ==========================================================================
# worldToLocal / localToWorld -- translated frame (no rotation)
# ==========================================================================


class TestTranslatedFrame:
    def test_world_to_local_subtracts_offset(self):
        """World point (4,6,8) in frame at (1,2,3) -> local (3,4,5)."""
        f = Frame3D(
            Point3D(1.0, 2.0, 3.0),
            Vector3D.unit_x(),
            Vector3D.unit_y(),
            Vector3D.unit_z(),
        )
        check_point(f.world_to_local(Point3D(4.0, 6.0, 8.0)), Point3D(3.0, 4.0, 5.0))

    def test_local_to_world_adds_offset(self):
        f = Frame3D(
            Point3D(1.0, 2.0, 3.0),
            Vector3D.unit_x(),
            Vector3D.unit_y(),
            Vector3D.unit_z(),
        )
        check_point(f.local_to_world(Point3D(3.0, 4.0, 5.0)), Point3D(4.0, 6.0, 8.0))


# ==========================================================================
# worldToLocal / localToWorld -- 90-degree rotated frame
# ==========================================================================


class TestRotatedFrame:
    def test_world_to_local_90_degree(self):
        """local X = world Y, local Y = world -X, local Z = world Z.
        World (1,0,0) -> local (0,-1,0)."""
        f = Frame3D(
            Point3D.origin(),
            Vector3D(0.0, 1.0, 0.0),
            Vector3D(-1.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )
        local = f.world_to_local(Point3D(1.0, 0.0, 0.0))
        check_point(local, Point3D(0.0, -1.0, 0.0))

    def test_local_to_world_90_degree(self):
        f = Frame3D(
            Point3D.origin(),
            Vector3D(0.0, 1.0, 0.0),
            Vector3D(-1.0, 0.0, 0.0),
            Vector3D(0.0, 0.0, 1.0),
        )
        check_point(f.local_to_world(Point3D(0.0, 1.0, 0.0)), Point3D(-1.0, 0.0, 0.0))


# ==========================================================================
# Round-trip consistency
# ==========================================================================


class TestRoundTrip:
    def test_local_to_world_of_world_to_local(self):
        """localToWorld(worldToLocal(P)) == P for rotated + translated frame."""
        angle = math.pi / 4.0
        f = Frame3D(
            Point3D(5.0, 3.0, -2.0),
            Vector3D(math.cos(angle), math.sin(angle), 0.0),
            Vector3D(-math.sin(angle), math.cos(angle), 0.0),
            Vector3D.unit_z(),
        )
        original = Point3D(7.0, -1.0, 4.0)
        check_point(f.local_to_world(f.world_to_local(original)), original)

    def test_world_to_local_of_local_to_world(self):
        f = Frame3D(
            Point3D(1.0, -2.0, 3.0),
            Vector3D(0.0, 0.0, 1.0),
            Vector3D(0.0, 1.0, 0.0),
            Vector3D(-1.0, 0.0, 0.0),
        )
        local_orig = Point3D(2.0, 3.0, 4.0)
        check_point(f.world_to_local(f.local_to_world(local_orig)), local_orig)


# ==========================================================================
# Vector transformations (no translation)
# ==========================================================================


class TestVectorTransformations:
    def test_not_affected_by_frame_translation(self):
        """Vectors represent directions, not positions."""
        at_origin = Frame3D(
            Point3D.origin(),
            Vector3D.unit_x(),
            Vector3D.unit_y(),
            Vector3D.unit_z(),
        )
        at_offset = Frame3D(
            Point3D(100.0, 200.0, 300.0),
            Vector3D.unit_x(),
            Vector3D.unit_y(),
            Vector3D.unit_z(),
        )
        v = Vector3D(1.0, 2.0, 3.0)
        check_vector(at_origin.world_to_local(v), at_offset.world_to_local(v))

    def test_world_axis_maps_to_local_basis(self):
        """Frame's local X-axis in world coords -> (1,0,0) in local coords."""
        angle = math.pi / 3.0
        f = Frame3D(
            Point3D.origin(),
            Vector3D(math.cos(angle), math.sin(angle), 0.0),
            Vector3D(-math.sin(angle), math.cos(angle), 0.0),
            Vector3D.unit_z(),
        )
        check_vector(f.world_to_local(f.axis_x), Vector3D.unit_x())
        check_vector(f.world_to_local(f.axis_y), Vector3D.unit_y())
        check_vector(f.world_to_local(f.axis_z), Vector3D.unit_z())


# ==========================================================================
# Mutators
# ==========================================================================


class TestMutators:
    def test_set_origin(self):
        f = Frame3D()
        f.set_origin(Point3D(5.0, 6.0, 7.0))
        assert f.origin == Point3D(5.0, 6.0, 7.0)

    def test_set_origin_does_not_change_axes(self):
        f = Frame3D()
        f.set_origin(Point3D(1.0, 2.0, 3.0))
        check_vector(f.axis_x, Vector3D.unit_x())
        check_vector(f.axis_y, Vector3D.unit_y())
        check_vector(f.axis_z, Vector3D.unit_z())

    def test_set_axes_normalizes(self):
        f = Frame3D()
        f.set_axes(
            Vector3D(3.0, 0.0, 0.0),
            Vector3D(0.0, 4.0, 0.0),
            Vector3D(0.0, 0.0, 5.0),
        )
        check_vector(f.axis_x, Vector3D.unit_x())
        check_vector(f.axis_y, Vector3D.unit_y())
        check_vector(f.axis_z, Vector3D.unit_z())


# ==========================================================================
# Stream output
# ==========================================================================


class TestStringOutput:
    def test_repr_contains_frame3d(self):
        s = repr(Frame3D())
        assert "Frame3D" in s

    def test_repr_mentions_origin_and_axes(self):
        s = repr(Frame3D())
        assert "Origin" in s
        assert "X-Axis" in s
        assert "Y-Axis" in s
        assert "Z-Axis" in s
