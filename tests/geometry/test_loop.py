"""Unit tests for pycadwork.geometry.Loop.

A Loop is an ordered, closed polyline of Point3D vertices. The closing edge
between the last and first vertex is implicit.
"""

import pytest

from pycadwork.geometry import Loop, Point3D


class TestConstruction:
    def test_default_constructor_is_empty(self):
        loop = Loop()
        assert loop.is_empty()
        assert loop.vertex_count() == 0

    def test_constructor_from_iterable_stores_vertices(self):
        verts = [Point3D(0.0, 0.0, 0.0), Point3D(1.0, 0.0, 0.0), Point3D(0.0, 1.0, 0.0)]
        loop = Loop(verts)
        assert loop.vertex_count() == 3
        assert not loop.is_empty()

    def test_constructor_preserves_vertex_order(self):
        loop = Loop([Point3D(1.0, 2.0, 3.0), Point3D(4.0, 5.0, 6.0)])
        assert loop.vertex_at(0) == Point3D(1.0, 2.0, 3.0)
        assert loop.vertex_at(1) == Point3D(4.0, 5.0, 6.0)

    def test_vertices_property_returns_list(self):
        loop = Loop([Point3D(), Point3D(1.0, 1.0, 1.0)])
        assert len(loop.vertices) == 2


class TestVertexAt:
    def test_out_of_range_raises_index_error(self):
        loop = Loop([Point3D()])
        with pytest.raises(IndexError):
            loop.vertex_at(1)

    def test_negative_index_raises_index_error(self):
        loop = Loop([Point3D()])
        with pytest.raises(IndexError):
            loop.vertex_at(-1)

    def test_empty_loop_always_raises(self):
        with pytest.raises(IndexError):
            Loop().vertex_at(0)


class TestComparison:
    def test_identical_loops_compare_equal(self):
        a = Loop([Point3D(0.0, 0.0, 0.0), Point3D(1.0, 0.0, 0.0)])
        b = Loop([Point3D(0.0, 0.0, 0.0), Point3D(1.0, 0.0, 0.0)])
        assert a == b

    def test_empty_loops_compare_equal(self):
        assert Loop() == Loop()

    def test_different_vertex_counts_unequal(self):
        a = Loop([Point3D()])
        b = Loop([Point3D(), Point3D(1.0, 0.0, 0.0)])
        assert a != b

    def test_different_vertex_values_unequal(self):
        a = Loop([Point3D(0.0, 0.0, 0.0)])
        b = Loop([Point3D(1.0, 0.0, 0.0)])
        assert a != b


class TestRepr:
    def test_repr_starts_with_loop(self):
        assert repr(Loop([Point3D()])).startswith("Loop(")

    def test_repr_reports_vertex_count(self):
        assert "3 vertices" in repr(Loop([Point3D(), Point3D(), Point3D()]))
