"""Double-layer lath strategy: two families of continuous laths, bolted at crossings.

This is the authentic *strained gridshell* (Weald & Downland / Mannheim): rather
than joint every high-valence node, two families of laths — one running along the
grid rows, one along the columns — are laid in **separate layers** stacked along
the shell normal and simply bolted where they cross. Each lath is continuous:
its straight segments abut end-to-end through the interior grid points with **no
node joint at all**, so the hard multi-rib hub never arises.

It consumes the sample grid directly (``list[list[Point3D]]``) — rows and columns
are the two families — which is exactly what
:class:`~pycadwork.gridshell.surface_builder.TriangulatedSurfaceBuilder` starts
from, so no fragile edge-chaining is needed. Element creation goes through the
``Beam`` / ``Drilling`` wrappers; this module never touches ``cadwork.*`` directly.
"""

from __future__ import annotations

from collections.abc import Sequence

from pycadwork.element.beam import Beam
from pycadwork.element.drilling import Drilling
from pycadwork.geometry import AxisPoints, Point3D, RectSection, Segment, Vector3D
from pycadwork.gridshell.specs import GridShellResult


def build_laths(
    grid: Sequence[Sequence[Point3D]],
    section: RectSection,
    *,
    layers: int = 2,
    layer_gap: float,
    bolt_diameter: float | None = None,
) -> GridShellResult:
    """Build a double-layer lath gridshell from a sample grid.

    ``layer_gap`` is the normal separation between the row layer (below) and the
    column layer (above). When ``bolt_diameter`` is given, a bolt is drilled
    through both layers at every grid crossing. Only the two-family (row +
    column) double layer is supported, so ``layers`` must be 2.
    """
    if layers != 2:
        raise ValueError(
            "build_laths supports only layers=2 (a row family + a column family)"
        )
    if layer_gap <= 0.0:
        raise ValueError("build_laths.layer_gap must be positive")
    rows = [list(row) for row in grid]
    row_count = len(rows)
    if row_count < 2:
        raise ValueError("build_laths: grid needs at least 2 rows")
    col_count = len(rows[0])
    if col_count < 2:
        raise ValueError("build_laths: grid needs at least 2 columns")
    if any(len(row) != col_count for row in rows):
        raise ValueError("build_laths: all grid rows must be the same length")

    normals = _point_normals(rows)
    # Row family sits on the shell (layer 0); the column family is stacked one
    # gap above it along the normal.
    row_pts = _offset_grid(rows, normals, 0.0)
    col_pts = _offset_grid(rows, normals, layer_gap)

    laths: list[Beam] = []
    for i in range(row_count):
        for j in range(col_count - 1):
            laths.append(
                _lath_segment(row_pts[i][j], row_pts[i][j + 1], normals[i][j], section)
            )
    for j in range(col_count):
        for i in range(row_count - 1):
            laths.append(
                _lath_segment(col_pts[i][j], col_pts[i + 1][j], normals[i][j], section)
            )

    drillings: list[Drilling] = []
    if bolt_diameter is not None:
        if bolt_diameter <= 0.0:
            raise ValueError("build_laths.bolt_diameter must be positive")
        reach = section.height
        for i in range(row_count):
            for j in range(col_count):
                normal = normals[i][j]
                start = rows[i][j] + normal * (-reach)
                end = rows[i][j] + normal * (layer_gap + reach)
                drillings.append(Drilling.create(bolt_diameter, Segment(start, end)))

    return GridShellResult(
        laths=tuple(laths),
        drillings=tuple(drillings),
    )


def _lath_segment(
    p1: Point3D, p2: Point3D, normal: Vector3D, section: RectSection
) -> Beam:
    """One straight lath segment standing on-edge along the shell normal."""
    return Beam.create_rectangular(section, AxisPoints(p1, p2, p1 + normal))


def _offset_grid(
    grid: list[list[Point3D]], normals: list[list[Vector3D]], distance: float
) -> list[list[Point3D]]:
    """Move every grid point ``distance`` along its normal (a whole-layer offset)."""
    return [
        [point + normals[i][j] * distance for j, point in enumerate(row)]
        for i, row in enumerate(grid)
    ]


def _point_normals(grid: list[list[Point3D]]) -> list[list[Vector3D]]:
    """Per-point shell normal from the two grid tangents (one-sided at edges)."""
    row_count = len(grid)
    col_count = len(grid[0])
    normals: list[list[Vector3D]] = []
    for i in range(row_count):
        row_normals: list[Vector3D] = []
        for j in range(col_count):
            tangent_col = _tangent(grid[i], j)  # along columns (varies j)
            tangent_row = _tangent(
                [grid[r][j] for r in range(row_count)], i
            )  # varies i
            normal = tangent_col.cross(tangent_row)
            row_normals.append(
                Vector3D.unit_z() if normal.is_zero() else normal.normalized()
            )
        normals.append(row_normals)
    return normals


def _tangent(points: list[Point3D], index: int) -> Vector3D:
    """Central-difference tangent along a 1-D point strip (one-sided at the ends)."""
    last = len(points) - 1
    if index <= 0:
        return points[1] - points[0]
    if index >= last:
        return points[last] - points[last - 1]
    return points[index + 1] - points[index - 1]
