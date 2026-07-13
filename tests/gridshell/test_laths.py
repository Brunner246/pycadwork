"""Double-layer lath gridshell: two continuous families, layered, bolted."""

from __future__ import annotations

import pytest

from pycadwork import Point3D, RectSection
from pycadwork.gridshell import GridShellBuilder
from tests._fakes.cadwork_adapter import FakeCadworkAdapter

SECTION = RectSection(50, 50)
LAYER_GAP = 50.0


def _flat_grid() -> list[list[Point3D]]:
    # 2 rows x 3 cols, flat on z=0. Rows run along +x, columns along +y.
    return [
        [Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(2000, 0, 0)],
        [Point3D(0, 1000, 0), Point3D(1000, 1000, 0), Point3D(2000, 1000, 0)],
    ]


def _build(bolt_diameter=None):
    return (
        GridShellBuilder.from_grid(_flat_grid())
        .laths(SECTION, layer_gap=LAYER_GAP, bolt_diameter=bolt_diameter)
        .build()
    )


def test_one_segment_per_grid_edge_in_each_family():
    result = _build()
    # rows: 2 x (3-1) = 4 ; columns: 3 x (2-1) = 3 ; total 7.
    assert len(result.laths) == 7
    assert result.members == ()  # laths are not "members"


def test_two_distinct_layers_along_the_normal(fake_cadwork: FakeCadworkAdapter):
    result = _build()
    zs = {round(b.geometry.start_point.z, 6) for b in result.laths}
    # Row family on the shell (z=0); column family one gap above.
    assert zs == {0.0, LAYER_GAP}


def test_continuous_laths_abut_with_no_joint(fake_cadwork: FakeCadworkAdapter):
    # Members pass straight through interior nodes: no miter, no plane cut.
    _build()
    assert fake_cadwork.state.miter_calls == []
    assert fake_cadwork.state.plane_cut_calls == []


def test_row_lath_segments_share_endpoints():
    result = _build()
    # The two segments of the first row lath meet at the interior grid point.
    row_segs = [
        b
        for b in result.laths
        if b.geometry.start_point.z == 0 and b.geometry.start_point.y == 0
    ]
    row_segs.sort(key=lambda b: b.geometry.start_point.x)
    assert len(row_segs) == 2
    assert row_segs[0].geometry.end_point == row_segs[1].geometry.start_point


def test_bolt_drilled_at_every_crossing():
    result = _build(bolt_diameter=12.0)
    # One bolt per grid point: 2 x 3 = 6.
    assert len(result.drillings) == 6


def test_no_bolts_without_a_diameter():
    assert _build().drillings == ()


def test_laths_requires_a_grid():
    surface_builder = GridShellBuilder([])
    with pytest.raises(ValueError, match="no grid"):
        surface_builder.laths(SECTION, layer_gap=LAYER_GAP)


def test_rejects_unsupported_layer_count():
    with pytest.raises(ValueError, match="only layers=2"):
        GridShellBuilder.from_grid(_flat_grid()).laths(
            SECTION, layers=3, layer_gap=LAYER_GAP
        ).build()


def test_curved_grid_lath_follows_the_surface():
    # A ridged grid: the middle column is raised, so row laths tilt and the
    # per-point normals are no longer +z everywhere. Build must still succeed.
    grid = [
        [Point3D(0, 0, 0), Point3D(1000, 0, 500), Point3D(2000, 0, 0)],
        [Point3D(0, 1000, 0), Point3D(1000, 1000, 500), Point3D(2000, 1000, 0)],
    ]
    result = (
        GridShellBuilder.from_grid(grid).laths(SECTION, layer_gap=LAYER_GAP).build()
    )
    assert len(result.laths) == 7
    # The first row lath rises from z=0 toward the raised ridge.
    ridge_segment = max(result.laths, key=lambda b: b.geometry.end_point.z)
    assert ridge_segment.geometry.end_point.z > 0
