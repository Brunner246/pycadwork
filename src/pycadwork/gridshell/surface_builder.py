"""TriangulatedSurfaceBuilder: generate a triangulated surface to feed the gridshell.

cadwork's ``create_surface`` builds one planar polygon per call, so a curved
nurbs-style shell is emitted as a list of single-triangle ``Surface`` elements
(``GridShellBuilder`` accepts a ``Sequence[Surface]`` and stitches them back
together by shared vertices).

Each grid quad is split on a **consistent diagonal** so every triangle winds the
same way — that keeps facet normals consistent, which the members-mode up-vector
averaging relies on.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from pycadwork.element.surface import Surface
from pycadwork.geometry import Point3D


class TriangulatedSurfaceBuilder:
    """Build a triangulated surface from a control/sample grid of points."""

    def __init__(self) -> None:
        self._grid: list[list[Point3D]] | None = None
        self._closed_u = False
        self._closed_v = False

    def from_grid(
        self, grid: Sequence[Sequence[Point3D]]
    ) -> "TriangulatedSurfaceBuilder":
        """Use an R×C grid of already-evaluated sample points."""
        self._grid = [list(row) for row in grid]
        return self

    def from_function(
        self,
        f: Callable[[float, float], Point3D],
        u_div: int,
        v_div: int,
    ) -> "TriangulatedSurfaceBuilder":
        """Sample a parametric surface ``f(u, v)``, u,v in [0, 1], into a grid."""
        if u_div < 1 or v_div < 1:
            raise ValueError(
                "TriangulatedSurfaceBuilder.from_function: u_div and v_div must be >= 1"
            )
        self._grid = [
            [f(i / u_div, j / v_div) for j in range(v_div + 1)]
            for i in range(u_div + 1)
        ]
        return self

    def closed_u(self, closed: bool = True) -> "TriangulatedSurfaceBuilder":
        """Wrap the last row back to the first (periodic in u)."""
        self._closed_u = closed
        return self

    def closed_v(self, closed: bool = True) -> "TriangulatedSurfaceBuilder":
        """Wrap the last column back to the first (periodic in v)."""
        self._closed_v = closed
        return self

    def build(self) -> list[Surface]:
        """Triangulate the grid and create one ``Surface`` per triangle."""
        if self._grid is None:
            raise ValueError(
                "TriangulatedSurfaceBuilder.build: no grid; "
                "call from_grid(...) or from_function(...) first"
            )
        grid = self._grid
        rows = len(grid)
        if rows < 2:
            raise ValueError("TriangulatedSurfaceBuilder: grid needs at least 2 rows")
        cols = len(grid[0])
        if cols < 2:
            raise ValueError(
                "TriangulatedSurfaceBuilder: grid needs at least 2 columns"
            )
        if any(len(row) != cols for row in grid):
            raise ValueError(
                "TriangulatedSurfaceBuilder: all grid rows must be the same length"
            )

        row_max = rows if self._closed_u else rows - 1
        col_max = cols if self._closed_v else cols - 1

        surfaces: list[Surface] = []
        for i in range(row_max):
            i1 = (i + 1) % rows
            for j in range(col_max):
                j1 = (j + 1) % cols
                v00 = grid[i][j]
                v01 = grid[i][j1]
                v11 = grid[i1][j1]
                v10 = grid[i1][j]
                surfaces.append(Surface.create([v00, v01, v11]))
                surfaces.append(Surface.create([v00, v11, v10]))
        return surfaces
