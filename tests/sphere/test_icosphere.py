"""Geodesic icosphere mesh generation (pure geometry + topology round-trip)."""

from __future__ import annotations

import pytest

import math

from pycadwork import Point3D
from pycadwork.gridshell import GridTopology
from pycadwork.sphere import (
    faces_to_surfaces,
    icosphere_faces,
    ring_levels,
    snap_boundary_to_plane,
    truncate_at_ring,
)


def _topology(faces):
    surfaces = faces_to_surfaces(faces)
    return GridTopology.from_breps([s.geometry.brep for s in surfaces])


# ---- face / vertex counts ----


@pytest.mark.parametrize(
    "frequency, faces, vertices, edges",
    [
        (1, 20, 12, 30),  # raw icosahedron
        (2, 80, 42, 120),
        (3, 180, 92, 270),
    ],
)
def test_counts_follow_the_geodesic_formula(frequency, faces, vertices, edges):
    mesh = icosphere_faces(1000.0, frequency)
    assert len(mesh) == faces  # 20 * frequency^2 triangles
    topology = _topology(mesh)
    assert len(topology.nodes()) == vertices  # 10 * frequency^2 + 2
    assert len(topology.edges()) == edges  # 30 * frequency^2


def test_every_vertex_lies_on_the_sphere():
    center = Point3D(1000.0, -500.0, 250.0)
    radius = 3200.0
    for triangle in icosphere_faces(radius, 3, center):
        for vertex in triangle:
            assert float(vertex.distance_to(center)) == pytest.approx(radius)


def test_closed_sphere_has_no_boundary_edges():
    topology = _topology(icosphere_faces(1000.0, 2))
    assert all(edge.valence == 2 for edge in topology.edges())


def test_icosahedron_edges_are_all_one_length():
    # Frequency 1 is the special case where every strut is genuinely identical.
    topology = _topology(icosphere_faces(1000.0, 1))
    lengths = [float(e.p1.distance_to(e.p2)) for e in topology.edges()]
    assert lengths[0] == pytest.approx(min(lengths))
    assert max(lengths) == pytest.approx(min(lengths))


# ---- ring levels + truncation ----


def test_ring_levels_are_the_pole_up_latitudes():
    # Pole-up icosahedron (frequency 1): two poles + two symmetric vertex rings.
    radius = 1000.0
    levels = ring_levels(icosphere_faces(radius, 1))
    assert len(levels) == 4
    ring = radius / math.sqrt(5.0)
    assert levels == pytest.approx([-radius, -ring, ring, radius])


def test_truncate_at_ring_leaves_a_coplanar_base():
    radius = 1000.0
    faces = icosphere_faces(radius, 3)
    ring_z = -radius / math.sqrt(5.0)  # the lower vertex ring
    kept = truncate_at_ring(faces, ring_z)
    assert 0 < len(kept) < len(faces)
    zs = [p.z for tri in kept for p in tri]
    assert min(zs) == pytest.approx(ring_z)  # base nodes coplanar on the ring
    assert all(z >= ring_z - 1e-6 for z in zs)  # nothing survives below it


def test_snap_boundary_flattens_the_whole_perimeter():
    radius = 1000.0
    faces = icosphere_faces(radius, 3)
    ring_z = ring_levels(faces)[1]  # a mid ring -> crenellated boundary
    kept = truncate_at_ring(faces, ring_z)
    # before snapping, the perimeter dips and rises around the cut
    assert min(p.z for tri in kept for p in tri) == pytest.approx(ring_z)
    snapped = snap_boundary_to_plane(kept, ring_z)
    # same triangle count; interior geometry preserved, perimeter pulled to plane
    assert len(snapped) == len(kept)
    # every vertex that was below-or-touching the ring now sits exactly on it,
    # and nothing is left below the plane
    assert all(p.z >= ring_z - 1e-6 for tri in snapped for p in tri)
    boundary_pts = [p for tri in snapped for p in tri if p.z == pytest.approx(ring_z)]
    assert boundary_pts  # a flat perimeter exists


# ---- guards ----


def test_rejects_non_positive_radius():
    with pytest.raises(ValueError, match="radius must be positive"):
        icosphere_faces(0.0, 2)


def test_rejects_frequency_below_one():
    with pytest.raises(ValueError, match="frequency must be >= 1"):
        icosphere_faces(1000.0, 0)
