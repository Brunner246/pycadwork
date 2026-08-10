"""Unit tests for the OrientedBoundingBox helpers added for connectivity.

Core OBB construction and the SAT intersection test live in the geometry
layer already; these focus on :meth:`expanded` and :meth:`from_axis_aligned`,
the two helpers the connectivity layer relies on.
"""

import pytest

from pycadwork.geometry import (
    AxisAlignedBoundingBox,
    Frame3D,
    OrientedBoundingBox,
    Point3D,
    Vector3D,
)


def _world_frame(center: Point3D) -> Frame3D:
    return Frame3D(
        center,
        Vector3D(1.0, 0.0, 0.0),
        Vector3D(0.0, 1.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )


class TestFromAxisAligned:
    def test_center_and_half_extents_match_the_aabb(self):
        aabb = AxisAlignedBoundingBox.from_min_max(
            Point3D(0.0, 0.0, 0.0), Point3D(2.0, 4.0, 6.0)
        )
        obb = OrientedBoundingBox.from_axis_aligned(aabb)
        assert obb.center == Point3D(1.0, 2.0, 3.0)
        assert obb.half_extents == Vector3D(1.0, 2.0, 3.0)
        assert obb.size == Vector3D(2.0, 4.0, 6.0)

    def test_axes_are_the_world_axes(self):
        aabb = AxisAlignedBoundingBox.from_min_max(
            Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 1.0)
        )
        obb = OrientedBoundingBox.from_axis_aligned(aabb)
        assert obb.axis_x == Vector3D(1.0, 0.0, 0.0)
        assert obb.axis_y == Vector3D(0.0, 1.0, 0.0)
        assert obb.axis_z == Vector3D(0.0, 0.0, 1.0)

    def test_round_trips_back_to_the_same_aabb(self):
        aabb = AxisAlignedBoundingBox.from_min_max(
            Point3D(-1.0, 2.0, -3.0), Point3D(4.0, 5.0, 6.0)
        )
        obb = OrientedBoundingBox.from_axis_aligned(aabb)
        assert obb.to_axis_aligned_bounding_box() == aabb


class TestExpanded:
    def test_grows_each_half_extent(self):
        obb = OrientedBoundingBox.from_frame_and_half_extents(
            _world_frame(Point3D(0.0, 0.0, 0.0)), Vector3D(1.0, 1.0, 1.0)
        )
        grown = obb.expanded(0.5)
        assert grown.half_extents == Vector3D(1.5, 1.5, 1.5)
        assert grown.center == Point3D(0.0, 0.0, 0.0)

    def test_zero_margin_is_unchanged(self):
        obb = OrientedBoundingBox.from_frame_and_half_extents(
            _world_frame(Point3D(1.0, 2.0, 3.0)), Vector3D(2.0, 2.0, 2.0)
        )
        assert obb.expanded(0.0) == obb

    def test_negative_margin_raises(self):
        obb = OrientedBoundingBox.from_frame_and_half_extents(
            _world_frame(Point3D(0.0, 0.0, 0.0)), Vector3D(1.0, 1.0, 1.0)
        )
        with pytest.raises(ValueError):
            obb.expanded(-0.1)


class TestExpandedDrivesContact:
    def test_margin_turns_a_gap_into_an_intersection(self):
        a = OrientedBoundingBox.from_axis_aligned(
            AxisAlignedBoundingBox.from_min_max(
                Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 1.0)
            )
        )
        b = OrientedBoundingBox.from_axis_aligned(
            AxisAlignedBoundingBox.from_min_max(
                Point3D(1.5, 0.0, 0.0), Point3D(2.5, 1.0, 1.0)
            )
        )
        assert not a.intersects(b)
        assert a.expanded(0.5).intersects(b)
