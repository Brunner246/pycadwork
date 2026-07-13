"""pycadwork.sphere — build a triangulated timber sphere pavilion.

Turn a sphere radius into a geodesic timber dome/sphere: a strut frame whose
members are as close to one length as the geometry allows, whose high-valence
nodes are resolved with radial bisector "shift cuts", truncated flat so it stands
on the ground, and clad with gapped triangular panels::

    from pycadwork.sphere import SpherePavilionBuilder
    from pycadwork.geometry import RectSection

    result = (
        SpherePavilionBuilder(radius=4000.0)
        .frequency(3)
        .ground_cut(1500.0)
        .timber(RectSection(60, 120))
        .cladding(thickness=27.0, gap=15.0)
        .build()
    )
    frame, cladding = result.members, result.panels

The build reuses the gridshell realization stack; :class:`RadialMiterJoint` is
re-exported here as the default (and swappable) node joint.
"""

from __future__ import annotations

from pycadwork.gridshell.joints import JointStrategy, RadialMiterJoint
from pycadwork.sphere.builder import SpherePavilionBuilder
from pycadwork.sphere.cladding import build_cladding
from pycadwork.sphere.icosphere import (
    faces_to_surfaces,
    icosphere_faces,
    ring_levels,
    snap_boundary_to_plane,
    truncate_at_ring,
)
from pycadwork.sphere.specs import SpherePavilionResult, StrutGroup

__all__ = [
    "JointStrategy",
    "RadialMiterJoint",
    "SpherePavilionBuilder",
    "SpherePavilionResult",
    "StrutGroup",
    "build_cladding",
    "faces_to_surfaces",
    "icosphere_faces",
    "ring_levels",
    "snap_boundary_to_plane",
    "truncate_at_ring",
]
