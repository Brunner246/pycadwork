"""Unit tests for pycadwork.geometry.Face.

A Face wraps an outer Loop (boundary), zero or more inner Loops (holes), and
a support Plane3D. ``Face.normal`` delegates to the support plane.
"""

from pycadwork.geometry import Face, Loop, Plane3D, Point3D, Vector3D


def _square_loop() -> Loop:
    return Loop(
        [
            Point3D(0.0, 0.0, 0.0),
            Point3D(1.0, 0.0, 0.0),
            Point3D(1.0, 1.0, 0.0),
            Point3D(0.0, 1.0, 0.0),
        ]
    )


def _square_hole() -> Loop:
    return Loop(
        [
            Point3D(0.25, 0.25, 0.0),
            Point3D(0.75, 0.25, 0.0),
            Point3D(0.75, 0.75, 0.0),
            Point3D(0.25, 0.75, 0.0),
        ]
    )


class TestConstruction:
    def test_outer_plus_plane_no_holes(self):
        face = Face(_square_loop(), Plane3D.xy())
        assert face.inner_loop_count() == 0
        assert not face.has_holes()
        assert face.outer_loop.vertex_count() == 4

    def test_with_holes(self):
        face = Face(_square_loop(), Plane3D.xy(), [_square_hole()])
        assert face.inner_loop_count() == 1
        assert face.has_holes()


class TestAccessors:
    def test_normal_delegates_to_plane(self):
        face = Face(_square_loop(), Plane3D.xy())
        assert face.normal == Vector3D.unit_z()

    def test_support_plane_returns_stored_plane(self):
        plane = Plane3D.xy(2.0)
        face = Face(_square_loop(), plane)
        assert face.support_plane == plane

    def test_inner_loops_returns_all_holes(self):
        face = Face(_square_loop(), Plane3D.xy(), [_square_hole(), _square_hole()])
        assert len(face.inner_loops) == 2


class TestComparison:
    def test_equal_faces(self):
        a = Face(_square_loop(), Plane3D.xy())
        b = Face(_square_loop(), Plane3D.xy())
        assert a == b

    def test_differing_outer_unequal(self):
        a = Face(_square_loop(), Plane3D.xy())
        b = Face(Loop([Point3D()]), Plane3D.xy())
        assert a != b

    def test_differing_hole_count_unequal(self):
        a = Face(_square_loop(), Plane3D.xy())
        b = Face(_square_loop(), Plane3D.xy(), [_square_hole()])
        assert a != b

    def test_same_hole_in_both(self):
        a = Face(_square_loop(), Plane3D.xy(), [_square_hole()])
        b = Face(_square_loop(), Plane3D.xy(), [_square_hole()])
        assert a == b


class TestRepr:
    def test_repr_starts_with_face(self):
        assert repr(Face(_square_loop(), Plane3D.xy())).startswith("Face(")

    def test_repr_reports_hole_count(self):
        face = Face(_square_loop(), Plane3D.xy(), [_square_hole(), _square_hole()])
        assert "holes=2" in repr(face)
