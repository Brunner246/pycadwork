"""Unit tests for pycadwork.geometry.AxisAlignedBoundingBox."""

import pytest

from pycadwork.geometry import AxisAlignedBoundingBox, Point3D, Vector3D


def _oob_vertices_unit_cube(origin: Point3D = Point3D(0.0, 0.0, 0.0)) -> list[Point3D]:
    """Return the 8 vertices of a unit cube anchored at ``origin``."""
    x, y, z = origin.x, origin.y, origin.z
    return [
        Point3D(x, y, z),
        Point3D(x + 1, y, z),
        Point3D(x + 1, y + 1, z),
        Point3D(x, y + 1, z),
        Point3D(x, y, z + 1),
        Point3D(x + 1, y, z + 1),
        Point3D(x + 1, y + 1, z + 1),
        Point3D(x, y + 1, z + 1),
    ]


class TestConstruction:
    def test_from_eight_oob_vertices(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert box.min_point == Point3D(0.0, 0.0, 0.0)
        assert box.max_point == Point3D(1.0, 1.0, 1.0)

    def test_rotated_points_still_yield_axis_aligned_extremes(self):
        points = [
            Point3D(-1.0, 0.0, 2.0),
            Point3D(3.0, -4.0, 5.0),
            Point3D(0.0, 7.0, -1.0),
        ]
        box = AxisAlignedBoundingBox(points)
        assert box.min_point == Point3D(-1.0, -4.0, -1.0)
        assert box.max_point == Point3D(3.0, 7.0, 5.0)

    def test_single_point_yields_zero_volume_box(self):
        p = Point3D(2.0, 3.0, 4.0)
        box = AxisAlignedBoundingBox([p])
        assert box.min_point == p
        assert box.max_point == p
        assert box.is_empty()

    def test_empty_iterable_raises(self):
        with pytest.raises(ValueError):
            AxisAlignedBoundingBox([])

    def test_accepts_generator(self):
        box = AxisAlignedBoundingBox(
            p for p in [Point3D(0, 0, 0), Point3D(2, 2, 2)]
        )
        assert box.max_point == Point3D(2.0, 2.0, 2.0)


class TestFromMinMax:
    def test_roundtrip(self):
        box = AxisAlignedBoundingBox.from_min_max(
            Point3D(1.0, 2.0, 3.0), Point3D(4.0, 5.0, 6.0)
        )
        assert box.min_point == Point3D(1.0, 2.0, 3.0)
        assert box.max_point == Point3D(4.0, 5.0, 6.0)

    def test_invalid_order_raises(self):
        with pytest.raises(ValueError):
            AxisAlignedBoundingBox.from_min_max(
                Point3D(5.0, 0.0, 0.0), Point3D(0.0, 1.0, 1.0)
            )


class TestAccessors:
    def test_center(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert box.center == Point3D(0.5, 0.5, 0.5)

    def test_size(self):
        box = AxisAlignedBoundingBox(
            [Point3D(0.0, 0.0, 0.0), Point3D(3.0, 4.0, 5.0)]
        )
        assert box.size == Vector3D(3.0, 4.0, 5.0)

    def test_is_empty_for_flat_box(self):
        flat = AxisAlignedBoundingBox(
            [Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 0.0)]
        )
        assert flat.is_empty()

    def test_non_empty_for_volumetric_box(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert not box.is_empty()


class TestPredicates:
    def test_contains_interior_point(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert box.contains_point(Point3D(0.5, 0.5, 0.5))

    def test_contains_boundary_point(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert box.contains_point(Point3D(1.0, 1.0, 1.0))

    def test_does_not_contain_exterior_point(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert not box.contains_point(Point3D(2.0, 0.5, 0.5))

    def test_intersects_overlapping(self):
        a = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        b = AxisAlignedBoundingBox(_oob_vertices_unit_cube(Point3D(0.5, 0.5, 0.5)))
        assert a.intersects(b)
        assert b.intersects(a)

    def test_intersects_touching_boundary(self):
        a = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        b = AxisAlignedBoundingBox(_oob_vertices_unit_cube(Point3D(1.0, 0.0, 0.0)))
        assert a.intersects(b)

    def test_does_not_intersect_disjoint(self):
        a = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        b = AxisAlignedBoundingBox(_oob_vertices_unit_cube(Point3D(5.0, 5.0, 5.0)))
        assert not a.intersects(b)


class TestUnion:
    def test_union_of_disjoint_boxes(self):
        a = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        b = AxisAlignedBoundingBox(_oob_vertices_unit_cube(Point3D(5.0, 5.0, 5.0)))
        u = a.union(b)
        assert u.min_point == Point3D(0.0, 0.0, 0.0)
        assert u.max_point == Point3D(6.0, 6.0, 6.0)

    def test_union_of_nested_boxes_is_outer(self):
        outer = AxisAlignedBoundingBox.from_min_max(
            Point3D(-1.0, -1.0, -1.0), Point3D(2.0, 2.0, 2.0)
        )
        inner = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert outer.union(inner) == outer


class TestExpanded:
    def test_grows_every_face_outward(self):
        box = AxisAlignedBoundingBox.from_min_max(
            Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 1.0)
        )
        grown = box.expanded(0.5)
        assert grown.min_point == Point3D(-0.5, -0.5, -0.5)
        assert grown.max_point == Point3D(1.5, 1.5, 1.5)

    def test_zero_margin_is_unchanged(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert box.expanded(0.0) == box

    def test_negative_margin_raises(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        with pytest.raises(ValueError):
            box.expanded(-0.1)

    def test_margin_turns_a_near_miss_into_an_intersection(self):
        a = AxisAlignedBoundingBox.from_min_max(
            Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 1.0)
        )
        b = AxisAlignedBoundingBox.from_min_max(
            Point3D(1.5, 0.0, 0.0), Point3D(2.5, 1.0, 1.0)
        )
        assert not a.intersects(b)
        assert a.expanded(0.5).intersects(b)


class TestCoordinates:
    def test_as_coordinates_ordering(self):
        box = AxisAlignedBoundingBox.from_min_max(
            Point3D(1.0, 2.0, 3.0), Point3D(4.0, 5.0, 6.0)
        )
        assert box.as_coordinates() == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)


class TestComparison:
    def test_equal_boxes(self):
        a = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        b = AxisAlignedBoundingBox.from_min_max(
            Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 1.0)
        )
        assert a == b

    def test_different_boxes_not_equal(self):
        a = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        b = AxisAlignedBoundingBox(_oob_vertices_unit_cube(Point3D(1.0, 0.0, 0.0)))
        assert a != b


class TestRepr:
    def test_repr_starts_with_class_name(self):
        box = AxisAlignedBoundingBox(_oob_vertices_unit_cube())
        assert repr(box).startswith("AxisAlignedBoundingBox(")
