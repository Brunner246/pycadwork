"""Panels strategy: one polygon panel per triangular face.

Each face becomes a ``Plate`` built directly from its polygon
(``create_polygon_panel``) and extruded by ``thickness`` along the face normal.
The panel's thickness runs along its *z-local* axis, so the face normal is
passed as ``z_local_direction`` and a meaningful in-plane edge as
``x_local_direction``. The polygon must wind counter-clockwise about the normal
for a valid (right-handed, non-inverted) solid, so the vertices are reordered
here to guarantee it. The flat triangles already tile the surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycadwork.element.plate import Plate
from pycadwork.geometry import Point3D
from pycadwork.gridshell.specs import GridShellResult

if TYPE_CHECKING:
    from pycadwork.geometry import Vector3D
    from pycadwork.gridshell.topology import GridTopology


def build_panels(topology: "GridTopology", thickness: float) -> GridShellResult:
    """Build a panel shell from ``topology`` and return the created plates."""
    warnings = list(topology.warnings())

    panels: list[Plate] = []
    for index, face in enumerate(topology.faces()):
        normal = face.normal.normalized()
        vertices = _ccw_about(list(face.outer_loop.vertices), normal)
        in_plane = (vertices[1] - vertices[0]).normalized()
        # z-local is the panel normal (the thickness axis); x-local is a
        # meaningful in-plane direction (the first polygon edge).
        panel = Plate.create_polygon(
            vertices,
            float(thickness),
            x_local_direction=_as_point(in_plane),
            z_local_direction=_as_point(normal),
        )
        # cadwork returns id 0 when a panel could not be formed (no exception);
        # surface it so a silent miss can't recur.
        if not panel.id:
            warnings.append(f"panel: face {index} not created")
        panels.append(panel)

    return GridShellResult(
        panels=tuple(panels),
        nodes=tuple(topology.nodes()),
        warnings=tuple(warnings),
    )


def _ccw_about(vertices: list[Point3D], normal: "Vector3D") -> list[Point3D]:
    """Return ``vertices`` wound counter-clockwise about ``normal``.

    The polygon's own right-hand-rule normal must agree with the target normal;
    if it points the other way the winding is clockwise, so the order is
    reversed. Guarantees cadwork extrudes to the outward side and builds a
    right-handed frame.
    """
    edge_1 = vertices[1] - vertices[0]
    edge_2 = vertices[2] - vertices[0]
    if edge_1.cross(edge_2).dot(normal) < 0.0:
        return list(reversed(vertices))
    return vertices


def _as_point(vector: "Vector3D") -> Point3D:
    return Point3D(vector.x, vector.y, vector.z)
