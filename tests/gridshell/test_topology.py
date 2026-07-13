"""GridTopology edge/node extraction — pure geometry, no cadwork needed."""

from __future__ import annotations

import pytest

from pycadwork.geometry import Brep, Face, Loop, Plane3D, Point3D, Vector3D
from pycadwork.gridshell import GridTopology


def _tri(a: Point3D, b: Point3D, c: Point3D) -> Face:
    return Face(Loop([a, b, c]), Plane3D.from_three_points(a, b, c))


# Two triangles sharing the a-b-c / b-d-c diagonal, coplanar in z=0.
A, B, C, D = Point3D(0, 0, 0), Point3D(1, 0, 0), Point3D(0, 1, 0), Point3D(1, 1, 0)


def _square_brep() -> Brep:
    return Brep([_tri(A, B, C), _tri(B, D, C)])


def test_shared_edge_is_deduplicated_to_one_interior_edge():
    topo = GridTopology.from_breps([_square_brep()])
    edges = topo.edges()
    assert len(edges) == 5  # 3 + 3 triangle edges minus 1 shared

    interior = [e for e in edges if e.valence == 2]
    assert len(interior) == 1
    assert interior[0].is_boundary is False


def test_boundary_edges_have_valence_one():
    topo = GridTopology.from_breps([_square_brep()])
    boundary = [e for e in topo.edges() if e.valence == 1]
    assert len(boundary) == 4
    assert all(e.is_boundary for e in boundary)


def test_interior_edge_up_is_averaged_face_normal():
    topo = GridTopology.from_breps([_square_brep()])
    interior = next(e for e in topo.edges() if e.valence == 2)
    assert interior.up == Vector3D(0, 0, 1)


def test_nodes_and_valences():
    topo = GridTopology.from_breps([_square_brep()])
    nodes = topo.nodes()
    assert len(nodes) == 4
    valences = sorted(n.valence for n in nodes)
    # two shared-diagonal endpoints have valence 3, the two corners valence 2
    assert valences == [2, 2, 3, 3]


def test_non_triangular_face_raises_when_strict():
    quad = Face(Loop([A, B, D, C]), Plane3D.from_three_points(A, B, D))
    with pytest.raises(ValueError, match="triangulated"):
        GridTopology.from_breps([Brep([quad])])


def test_non_triangular_face_skipped_when_lenient():
    quad = Face(Loop([A, B, D, C]), Plane3D.from_three_points(A, B, D))
    topo = GridTopology.from_breps([Brep([quad])], strict=False)
    assert topo.edges() == []
    assert topo.warnings()


def test_degenerate_triangle_rejected_under_tolerance():
    # Third vertex collapses onto the second at tol=1e-3.
    loop = Loop([Point3D(0, 0, 0), Point3D(1, 0, 0), Point3D(1.0000001, 0, 0)])
    face = Face(
        loop, Plane3D.from_point_and_normal(Point3D(0, 0, 0), Vector3D(0, 0, 1))
    )
    with pytest.raises(ValueError, match="degenerate"):
        GridTopology.from_breps([Brep([face])], tolerance=1e-3)


def test_non_positive_tolerance_rejected():
    with pytest.raises(ValueError, match="tolerance"):
        GridTopology.from_breps([_square_brep()], tolerance=0.0)
