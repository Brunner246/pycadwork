"""TriangulatedSurfaceBuilder: grid/function triangulation into Surfaces."""

from __future__ import annotations

import pytest

from pycadwork import Point3D, Surface
from pycadwork.gridshell import TriangulatedSurfaceBuilder


def _flat_grid(rows: int, cols: int) -> list[list[Point3D]]:
    return [[Point3D(j, i, 0) for j in range(cols)] for i in range(rows)]


def test_from_grid_emits_two_triangles_per_quad():
    surfaces = TriangulatedSurfaceBuilder().from_grid(_flat_grid(2, 2)).build()
    assert len(surfaces) == 2
    assert all(isinstance(s, Surface) for s in surfaces)


def test_from_function_triangle_count_is_two_per_cell():
    surfaces = (
        TriangulatedSurfaceBuilder()
        .from_function(lambda u, v: Point3D(u, v, 0), u_div=2, v_div=3)
        .build()
    )
    assert len(surfaces) == 2 * 2 * 3


def test_closed_u_wraps_the_last_row():
    grid = _flat_grid(3, 2)
    open_count = len(TriangulatedSurfaceBuilder().from_grid(grid).build())
    closed_count = len(TriangulatedSurfaceBuilder().from_grid(grid).closed_u().build())
    assert open_count == 2 * 2  # (3-1) rows x (2-1) cols x 2
    assert closed_count == 3 * 2  # 3 rows x (2-1) cols x 2


def test_build_without_grid_raises():
    with pytest.raises(ValueError, match="no grid"):
        TriangulatedSurfaceBuilder().build()


def test_from_function_rejects_zero_divisions():
    with pytest.raises(ValueError, match=">= 1"):
        TriangulatedSurfaceBuilder().from_function(
            lambda u, v: Point3D(u, v, 0), u_div=0, v_div=2
        )


def test_ragged_grid_rejected():
    grid = [[Point3D(0, 0, 0), Point3D(1, 0, 0)], [Point3D(0, 1, 0)]]
    with pytest.raises(ValueError, match="same length"):
        TriangulatedSurfaceBuilder().from_grid(grid).build()
