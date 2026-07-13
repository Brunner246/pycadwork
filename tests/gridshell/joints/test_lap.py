"""LapJoint: native housed cross-lap (+ optional bolts) at multi-rib nodes."""

from __future__ import annotations

import pytest

from pycadwork import Point3D, RectSection, Surface
from pycadwork.gridshell import GridShellBuilder, TriangulatedSurfaceBuilder
from pycadwork.gridshell.joints import LapJoint
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _two_triangle_surfaces() -> list[Surface]:
    grid = [
        [Point3D(0, 0, 0), Point3D(1000, 0, 0)],
        [Point3D(0, 1000, 0), Point3D(1000, 1000, 0)],
    ]
    return TriangulatedSurfaceBuilder().from_grid(grid).build()


def _build(joint):
    return (
        GridShellBuilder(_two_triangle_surfaces())
        .members(RectSection(60, 200))
        .joint(joint)
        .build()
    )


def test_cross_laps_the_through_pair_at_each_hub(fake_cadwork: FakeCadworkAdapter):
    _build(LapJoint())
    # Two valence-3 hubs -> one cross-lap (of the straightest pair) each.
    assert len(fake_cadwork.state.cross_lap_calls) == 2


def test_default_depth_is_half_the_section_height(fake_cadwork: FakeCadworkAdapter):
    _build(LapJoint())  # section height 200 -> depth 100
    for call in fake_cadwork.state.cross_lap_calls:
        depth = call[1]
        assert depth == pytest.approx(100.0)


def test_bolts_are_passed_through(fake_cadwork: FakeCadworkAdapter):
    _build(LapJoint(bolt_count=2, bolt_diameter=12.0, bolt_tolerance=1.0))
    for call in fake_cadwork.state.cross_lap_calls:
        _eids, _depth, _cb, _cs, count, dia, tol = call
        assert (count, dia, tol) == (2, pytest.approx(12.0), pytest.approx(1.0))


def test_lap_issues_no_miter_or_plane_cut(fake_cadwork: FakeCadworkAdapter):
    _build(LapJoint())
    assert fake_cadwork.state.miter_calls == []
    assert fake_cadwork.state.plane_cut_calls == []


def test_rejects_bad_arguments():
    with pytest.raises(ValueError, match="min_valence must be >= 2"):
        LapJoint(min_valence=1)
    with pytest.raises(ValueError, match="depth must be positive"):
        LapJoint(depth=0.0)
    with pytest.raises(ValueError, match="bolt_count must be non-negative"):
        LapJoint(bolt_count=-1)
