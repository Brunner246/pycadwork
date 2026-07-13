"""Cladding strategy: one gapped triangular panel per lattice face.

Like :func:`~pycadwork.gridshell.panels.build_panels`, each triangular face
becomes an extruded :class:`~pycadwork.element.plate.Plate`; unlike it, the panel
is *inset* so neighbouring panels leave a uniform ``gap`` between them (open
joints), the same distance on every side.

The inset is a homothety about the triangle's incenter: scaling a triangle about
its incenter by ``(r − inset) / r`` (``r`` = inradius) moves every edge inward by
exactly ``inset``, so two panels sharing an edge — each inset by ``gap / 2`` —
end up ``gap`` apart on that edge. The thickness extrudes along the *outward*
sphere normal (centre → face), so panels clad the outside of the frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycadwork.element.plate import Plate
from pycadwork.geometry import Point3D, Vector3D

if TYPE_CHECKING:
    from pycadwork.gridshell.topology import GridTopology

Triangle = list[Point3D]


def build_cladding(
    topology: "GridTopology",
    *,
    thickness: float,
    gap: float,
    center: Point3D,
) -> tuple[list[Plate], list[str]]:
    """Build inset cladding panels for every triangular face of ``topology``.

    ``gap`` is the total open joint between adjacent panels (each panel is inset
    by ``gap / 2``); ``thickness`` extrudes each panel outward along the sphere
    normal. Returns the created plates and any non-fatal warnings.
    """
    if thickness <= 0.0:
        raise ValueError("build_cladding: thickness must be positive")
    if gap < 0.0:
        raise ValueError("build_cladding: gap must not be negative")

    warnings: list[str] = []
    panels: list[Plate] = []
    inset = gap / 2.0
    for index, face in enumerate(topology.faces()):
        vertices = list(face.outer_loop.vertices)
        if len(vertices) != 3:
            warnings.append(f"cladding: face {index} is not a triangle; skipped")
            continue

        outward = _centroid(vertices) - center
        outward = (
            face.normal.normalized() if outward.is_zero() else outward.normalized()
        )

        shaped = _inset_triangle(vertices, inset) if inset > 0.0 else vertices
        if shaped is None:
            warnings.append(f"cladding: face {index} too small for the gap; skipped")
            continue

        ordered = _ccw_about(shaped, outward)
        in_plane = (ordered[1] - ordered[0]).normalized()
        panel = Plate.create_polygon(
            ordered,
            float(thickness),
            x_local_direction=_as_point(in_plane),
            z_local_direction=_as_point(outward),
        )
        # cadwork returns id 0 when a panel could not be formed (no exception).
        if not panel.id:
            warnings.append(f"cladding: face {index} not created")
        panels.append(panel)

    return panels, warnings


def _centroid(vertices: Triangle) -> Point3D:
    return Point3D(
        (vertices[0].x + vertices[1].x + vertices[2].x) / 3.0,
        (vertices[0].y + vertices[1].y + vertices[2].y) / 3.0,
        (vertices[0].z + vertices[1].z + vertices[2].z) / 3.0,
    )


def _inset_triangle(vertices: Triangle, inset: float) -> Triangle | None:
    """Shrink a triangle inward by ``inset`` on every edge (incenter homothety).

    Returns ``None`` when the triangle is too small to inset by ``inset`` (the
    inradius would go non-positive) — the caller skips that panel.
    """
    a, b, c = vertices
    side_a = float(b.distance_to(c))  # opposite vertex a
    side_b = float(c.distance_to(a))
    side_c = float(a.distance_to(b))
    perimeter = side_a + side_b + side_c
    if perimeter <= 0.0:
        return None
    incenter = Point3D(
        (side_a * a.x + side_b * b.x + side_c * c.x) / perimeter,
        (side_a * a.y + side_b * b.y + side_c * c.y) / perimeter,
        (side_a * a.z + side_b * b.z + side_c * c.z) / perimeter,
    )
    area = 0.5 * float((b - a).cross(c - a).magnitude())
    inradius = area / (perimeter / 2.0)
    if inradius <= inset:
        return None
    scale = (inradius - inset) / inradius
    return [incenter + (v - incenter) * scale for v in vertices]


def _ccw_about(vertices: Triangle, normal: Vector3D) -> Triangle:
    """Wind ``vertices`` counter-clockwise about ``normal`` (outward, right-handed)."""
    edge_1 = vertices[1] - vertices[0]
    edge_2 = vertices[2] - vertices[0]
    if edge_1.cross(edge_2).dot(normal) < 0.0:
        return list(reversed(vertices))
    return vertices


def _as_point(vector: Vector3D) -> Point3D:
    return Point3D(vector.x, vector.y, vector.z)
