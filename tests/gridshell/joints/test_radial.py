"""RadialMiterJoint: multi-rib bisector-plane cuts, no connector, no void."""

from __future__ import annotations

import pytest

from pycadwork import Point3D, RectSection, Surface
from pycadwork.gridshell import GridShellBuilder, TriangulatedSurfaceBuilder
from pycadwork.gridshell.joints import RadialMiterJoint
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _two_triangle_surfaces() -> list[Surface]:
    grid = [
        [Point3D(0, 0, 0), Point3D(1000, 0, 0)],
        [Point3D(0, 1000, 0), Point3D(1000, 1000, 0)],
    ]
    return TriangulatedSurfaceBuilder().from_grid(grid).build()


def _build(joint=None):
    joint = joint if joint is not None else RadialMiterJoint()
    return (
        GridShellBuilder(_two_triangle_surfaces())
        .members(RectSection(60, 200))
        .joint(joint)
        .build()
    )


def test_cuts_each_hub_rib_on_two_bisector_planes(fake_cadwork: FakeCadworkAdapter):
    # Two valence-3 hubs: each rib gets one plane per angular neighbour = 2,
    # so 3 ribs x 2 = 6 cuts per hub -> 12 plane cuts total.
    _build()
    assert len(fake_cadwork.state.plane_cut_calls) == 12


def test_valence_two_corners_fall_back_to_miter(fake_cadwork: FakeCadworkAdapter):
    _build()
    # The two valence-2 corners are mitered (not radially cut).
    assert len(fake_cadwork.state.miter_calls) == 2


def test_creates_no_connectors_or_drillings():
    result = _build()
    assert result.connectors == ()
    assert result.drillings == ()


def test_bisector_planes_contain_the_shell_normal(fake_cadwork: FakeCadworkAdapter):
    # A bisector plane contains the node normal (+z on the flat mesh), so its
    # own normal lies in the tangent plane: z-component ~ 0.
    _build()
    for _eid, normal, _dist in fake_cadwork.state.plane_cut_calls:
        assert normal[2] == pytest.approx(0.0, abs=1e-9)


def test_ribs_are_not_set_back(fake_cadwork: FakeCadworkAdapter):
    # Radial miter leaves the ribs meeting at the node (the planes must land);
    # boundary ribs keep their full 1000 length before the cut.
    result = _build()
    lengths = sorted(float(b.geometry.length) for b in result.members)
    assert lengths[0] == pytest.approx(1000.0)


def test_rejects_bad_min_valence():
    with pytest.raises(ValueError, match="min_valence must be >= 3"):
        RadialMiterJoint(min_valence=2)
