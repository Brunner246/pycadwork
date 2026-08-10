"""Unit tests for pycadwork.geometry.Brep.

A Brep is a flat collection of Face instances. No topological relations
(shared edges/vertices) are tracked.
"""

import pytest

from pycadwork.geometry import Brep, Face, Loop, Plane3D, Point3D


def _unit_square_face_xy(z: float = 0.0) -> Face:
    outer = Loop(
        [
            Point3D(0.0, 0.0, z),
            Point3D(1.0, 0.0, z),
            Point3D(1.0, 1.0, z),
            Point3D(0.0, 1.0, z),
        ]
    )
    return Face(outer, Plane3D.xy(z))


def _unit_square_face_xz(y: float = 0.0) -> Face:
    outer = Loop(
        [
            Point3D(0.0, y, 0.0),
            Point3D(1.0, y, 0.0),
            Point3D(1.0, y, 1.0),
            Point3D(0.0, y, 1.0),
        ]
    )
    return Face(outer, Plane3D.xz(y))


class TestConstruction:
    def test_default_is_empty(self):
        brep = Brep()
        assert brep.is_empty()
        assert brep.face_count() == 0

    def test_constructor_from_iterable_stores_faces(self):
        brep = Brep([_unit_square_face_xy(), _unit_square_face_xz()])
        assert brep.face_count() == 2


class TestMutators:
    def test_add_face_increases_count(self):
        brep = Brep()
        brep.add_face(_unit_square_face_xy())
        assert brep.face_count() == 1
        brep.add_face(_unit_square_face_xz())
        assert brep.face_count() == 2


class TestFaceAt:
    def test_out_of_range_raises(self):
        with pytest.raises(IndexError):
            Brep().face_at(0)

    def test_returns_face_at_index(self):
        brep = Brep()
        brep.add_face(_unit_square_face_xy(0.0))
        brep.add_face(_unit_square_face_xy(5.0))
        assert brep.face_at(0).support_plane == Plane3D.xy(0.0)
        assert brep.face_at(1).support_plane == Plane3D.xy(5.0)


class TestComparison:
    def test_two_empty_breps_equal(self):
        assert Brep() == Brep()

    def test_same_faces_in_same_order_equal(self):
        a = Brep([_unit_square_face_xy()])
        b = Brep([_unit_square_face_xy()])
        assert a == b

    def test_different_face_counts_unequal(self):
        a = Brep([_unit_square_face_xy()])
        b = Brep()
        assert a != b

    def test_different_faces_unequal(self):
        a = Brep([_unit_square_face_xy()])
        b = Brep([_unit_square_face_xz()])
        assert a != b


class TestRepr:
    def test_repr_starts_with_brep(self):
        brep = Brep([_unit_square_face_xy()])
        assert repr(brep).startswith("Brep(")

    def test_repr_reports_face_count(self):
        brep = Brep([_unit_square_face_xy(), _unit_square_face_xz()])
        assert "2 faces" in repr(brep)
