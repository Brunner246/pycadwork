"""Unit tests for pycadwork.geometry.spatial_index."""

import pytest

from pycadwork.geometry import (
    AxisAlignedBoundingBox,
    Point3D,
    RTreeIndex3D,
    SpatialIndex3D,
    SpatialQuery3D,
)


def _cube(origin: Point3D, side: float = 1.0) -> AxisAlignedBoundingBox:
    return AxisAlignedBoundingBox.from_min_max(
        origin,
        Point3D(origin.x + side, origin.y + side, origin.z + side),
    )


class TestProtocolConformance:
    def test_rtree_index_conforms_to_spatial_index_protocol(self):
        idx = RTreeIndex3D()
        assert isinstance(idx, SpatialIndex3D)
        assert isinstance(idx, SpatialQuery3D)


class TestConstruction:
    def test_empty_index_is_length_zero(self):
        assert len(RTreeIndex3D()) == 0

    def test_bulk_insert_via_constructor(self):
        items = [
            (1, _cube(Point3D(0.0, 0.0, 0.0))),
            (2, _cube(Point3D(5.0, 0.0, 0.0))),
            (3, _cube(Point3D(0.0, 5.0, 0.0))),
        ]
        idx = RTreeIndex3D(items)
        assert len(idx) == 3


class TestInsertAndIntersection:
    def test_intersection_returns_only_overlapping_elements(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        idx.insert(2, _cube(Point3D(5.0, 0.0, 0.0)))
        idx.insert(3, _cube(Point3D(0.0, 5.0, 0.0)))

        query = AxisAlignedBoundingBox.from_min_max(
            Point3D(-0.5, -0.5, -0.5), Point3D(0.5, 0.5, 0.5)
        )
        assert list(idx.intersection(query)) == [1]

    def test_intersection_returns_multiple_when_overlapping(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        idx.insert(2, _cube(Point3D(0.5, 0.0, 0.0)))
        idx.insert(3, _cube(Point3D(10.0, 10.0, 10.0)))

        query = AxisAlignedBoundingBox.from_min_max(
            Point3D(0.2, 0.2, 0.2), Point3D(0.8, 0.8, 0.8)
        )
        assert sorted(idx.intersection(query)) == [1, 2]

    def test_intersection_empty_for_far_region(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        far = AxisAlignedBoundingBox.from_min_max(
            Point3D(100.0, 100.0, 100.0), Point3D(200.0, 200.0, 200.0)
        )
        assert list(idx.intersection(far)) == []


class TestRemove:
    def test_removed_entry_no_longer_appears(self):
        idx = RTreeIndex3D()
        box = _cube(Point3D(0.0, 0.0, 0.0))
        idx.insert(42, box)
        assert len(idx) == 1

        idx.remove(42, box)
        assert len(idx) == 0

        query = AxisAlignedBoundingBox.from_min_max(
            Point3D(-1.0, -1.0, -1.0), Point3D(2.0, 2.0, 2.0)
        )
        assert list(idx.intersection(query)) == []


class TestNearest:
    def test_nearest_returns_closest_element(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        idx.insert(2, _cube(Point3D(10.0, 0.0, 0.0)))
        idx.insert(3, _cube(Point3D(0.0, 10.0, 0.0)))

        nearest = list(idx.nearest(Point3D(0.2, 0.2, 0.2), k=1))
        assert nearest == [1]

    def test_nearest_k_returns_k_elements(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        idx.insert(2, _cube(Point3D(10.0, 0.0, 0.0)))
        idx.insert(3, _cube(Point3D(100.0, 0.0, 0.0)))

        # Closest to origin: 1 (at 0), then 2 (at 10), then 3 (at 100).
        nearest = list(idx.nearest(Point3D(-1.0, 0.0, 0.0), k=2))
        assert nearest == [1, 2]

    def test_nearest_invalid_k_raises(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        with pytest.raises(ValueError):
            list(idx.nearest(Point3D(0.0, 0.0, 0.0), k=0))


class TestClear:
    def test_clear_empties_index(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        idx.insert(2, _cube(Point3D(5.0, 0.0, 0.0)))
        assert len(idx) == 2

        idx.clear()
        assert len(idx) == 0

        query = AxisAlignedBoundingBox.from_min_max(
            Point3D(-1.0, -1.0, -1.0), Point3D(100.0, 100.0, 100.0)
        )
        assert list(idx.intersection(query)) == []

    def test_reuse_after_clear(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        idx.clear()
        idx.insert(7, _cube(Point3D(0.0, 0.0, 0.0)))

        query = AxisAlignedBoundingBox.from_min_max(
            Point3D(-1.0, -1.0, -1.0), Point3D(2.0, 2.0, 2.0)
        )
        assert list(idx.intersection(query)) == [7]


class TestRepr:
    def test_repr_starts_with_class_name(self):
        idx = RTreeIndex3D()
        idx.insert(1, _cube(Point3D(0.0, 0.0, 0.0)))
        assert repr(idx).startswith("RTreeIndex3D(")
        assert "1 entries" in repr(idx)
