"""Geodesic icosphere mesh: subdivide an icosahedron and project to a sphere.

A geodesic sphere gives near-uniform strut lengths — far better than a lat/long
UV sphere, whose struts vary wildly and whose poles pinch. The construction is
the classic one: start from the 12-vertex / 20-face icosahedron, split every
face into ``frequency²`` small triangles (Class I / "alternate" geodesic), and
project every generated vertex radially onto the sphere of the given radius.

The output is a flat list of triangles (each three :class:`Point3D`). One
``Surface`` per triangle (:func:`faces_to_surfaces`) is exactly the
``list[Surface]`` that :class:`~pycadwork.gridshell.topology.GridTopology`
consumes — shared vertices are deduplicated there, so no vertex bookkeeping is
needed here. This module is pure geometry and never touches ``cadwork.*``.
"""

from __future__ import annotations

import math

from pycadwork.element.surface import Surface
from pycadwork.geometry import Point3D, Vector3D


def _pole_up_vertices() -> tuple[tuple[float, float, float], ...]:
    """The 12 icosahedron vertices oriented pole-up (a vertex at each pole).

    Top pole, an upper ring of 5, a lower ring of 5 (offset 36°), bottom pole —
    all on the unit sphere. This orientation has 5-fold symmetry about the
    vertical axis, so subdivided vertices fall on horizontal rings, which is what
    lets a ground cut land on a clean coplanar node ring.
    """
    ring_r = 2.0 / math.sqrt(5.0)  # xy-radius of the two rings
    ring_z = 1.0 / math.sqrt(5.0)  # |z| of the two rings
    step = 2.0 * math.pi / 5.0
    upper = [
        (ring_r * math.cos(step * k), ring_r * math.sin(step * k), ring_z)
        for k in range(5)
    ]
    lower = [
        (
            ring_r * math.cos(step * k + step / 2.0),
            ring_r * math.sin(step * k + step / 2.0),
            -ring_z,
        )
        for k in range(5)
    ]
    return ((0.0, 0.0, 1.0), *upper, *lower, (0.0, 0.0, -1.0))


def _pole_up_faces() -> tuple[tuple[int, int, int], ...]:
    """The 20 faces of the pole-up icosahedron (winding fixed at build time)."""
    top, bottom = 0, 11
    faces: list[tuple[int, int, int]] = []
    for k in range(5):
        u_k, u_next = 1 + k, 1 + (k + 1) % 5
        l_k, l_next = 6 + k, 6 + (k + 1) % 5
        faces.append((top, u_k, u_next))  # top cap
        faces.append((u_k, u_next, l_k))  # band, pointing down
        faces.append((u_next, l_next, l_k))  # band, pointing up
        faces.append((bottom, l_next, l_k))  # bottom cap
    return tuple(faces)


#: The 12 pole-up icosahedron vertices (normalized at projection time).
_ICO_VERTICES = _pole_up_vertices()

#: The 20 triangular faces; winding is normalized outward in ``icosphere_faces``.
_ICO_FACES = _pole_up_faces()

Triangle = tuple[Point3D, Point3D, Point3D]


def icosphere_faces(
    radius: float, frequency: int, center: Point3D | None = None
) -> list[Triangle]:
    """Triangulate a sphere of ``radius`` about ``center`` at the given frequency.

    ``frequency`` is the icosahedron subdivision level: each of the 20 base faces
    becomes ``frequency²`` triangles, so the result has ``20 * frequency²``
    triangles and ``10 * frequency² + 2`` unique vertices. Frequency 1 is the raw
    icosahedron (all 30 edges identical length).
    """
    if radius <= 0.0:
        raise ValueError("icosphere_faces: radius must be positive")
    if frequency < 1:
        raise ValueError("icosphere_faces: frequency must be >= 1")
    origin = center if center is not None else Point3D.origin()
    base = [Vector3D(*v) for v in _ICO_VERTICES]
    faces: list[Triangle] = []
    for i0, i1, i2 in _ICO_FACES:
        a, b, c = _outward_winding(base[i0], base[i1], base[i2])
        faces.extend(_subdivide(a, b, c, frequency, radius, origin))
    return faces


def faces_to_surfaces(faces: list[Triangle]) -> list[Surface]:
    """Create one cadwork ``Surface`` per triangle (the gridshell topology input)."""
    return [Surface.create([a, b, c]) for a, b, c in faces]


def ring_levels(faces: list[Triangle], *, tolerance: float = 1e-6) -> list[float]:
    """The sorted distinct vertex ``z`` levels — the candidate ground-cut rings.

    Vertices are quantized by ``tolerance`` so a whole horizontal node ring
    collapses to one level. A ground cut snaps to whichever level is nearest.
    """
    seen: dict[int, float] = {}
    for tri in faces:
        for point in tri:
            seen[round(point.z / tolerance)] = point.z
    return sorted(seen.values())


def truncate_at_ring(
    faces: list[Triangle], ring_z: float, *, tolerance: float = 1e-6
) -> list[Triangle]:
    """Keep faces sitting entirely on or above ``ring_z`` (drop the cap below it).

    A face survives only if *every* vertex has ``z >= ring_z - tolerance``. When
    ``ring_z`` is a natural node level the surviving mesh's lowest vertices are
    exactly coplanar at ``ring_z`` — a clean base ring for the sill and slab.
    """
    return [tri for tri in faces if all(p.z >= ring_z - tolerance for p in tri)]


def snap_boundary_to_plane(
    faces: list[Triangle], plane_z: float, *, tolerance: float = 1e-6
) -> list[Triangle]:
    """Flatten the open boundary of a truncated mesh onto ``z = plane_z``.

    After :func:`truncate_at_ring` the perimeter is crenellated — only the lowest
    nodes touch the ring, the rest of the boundary loop zigzags above it. This
    drops every boundary vertex straight down onto the plane (keeping its XY), so
    the perimeter becomes one coplanar polygon (a clean sill ring / slab
    footprint); the lowest ring of faces stretches to meet it. Interior vertices
    are untouched. Boundary vertices are found from a pure-geometry edge scan (an
    undirected edge touched by one triangle is a boundary edge) — no cadwork
    surfaces are created.
    """

    def key(point: Point3D) -> tuple[int, int, int]:
        return (
            round(point.x / tolerance),
            round(point.y / tolerance),
            round(point.z / tolerance),
        )

    edge_faces: dict[tuple, int] = {}
    for tri in faces:
        keys = [key(p) for p in tri]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge = (keys[a], keys[b]) if keys[a] <= keys[b] else (keys[b], keys[a])
            edge_faces[edge] = edge_faces.get(edge, 0) + 1
    boundary_keys = {
        k for edge, count in edge_faces.items() if count == 1 for k in edge
    }

    def snap(point: Point3D) -> Point3D:
        if key(point) in boundary_keys:
            return Point3D(point.x, point.y, plane_z)
        return point

    return [tuple(snap(p) for p in tri) for tri in faces]


def _outward_winding(
    a: Vector3D, b: Vector3D, c: Vector3D
) -> tuple[Vector3D, Vector3D, Vector3D]:
    """Reorder a face so its normal points away from the origin (outward)."""
    normal = (b - a).cross(c - a)
    outward = a + b + c  # centroid direction from the origin
    if normal.dot(outward) < 0.0:
        return a, c, b
    return a, b, c


def _project(direction: Vector3D, radius: float, center: Point3D) -> Point3D:
    """Radially project a direction from the origin onto the sphere surface."""
    return center + direction.normalized() * radius


def _subdivide(
    a: Vector3D,
    b: Vector3D,
    c: Vector3D,
    freq: int,
    radius: float,
    center: Point3D,
) -> list[Triangle]:
    """Split one base face into ``freq²`` projected triangles (barycentric grid).

    ``i`` runs toward ``b``, ``j`` toward ``c``; the up/down triangle pairs keep
    the parent face's winding so every facet normal points outward.
    """
    grid: dict[tuple[int, int], Point3D] = {}
    for i in range(freq + 1):
        for j in range(freq + 1 - i):
            k = freq - i - j
            direction = a * (k / freq) + b * (i / freq) + c * (j / freq)
            grid[(i, j)] = _project(direction, radius, center)

    triangles: list[Triangle] = []
    for i in range(freq):
        for j in range(freq - i):
            triangles.append((grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]))
            if i + j < freq - 1:
                triangles.append(
                    (grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)])
                )
    return triangles
