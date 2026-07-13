"""GridShellBuilder end-to-end against the FakeCadworkAdapter."""

from __future__ import annotations

import math

import pytest

from pycadwork import Point3D, RectSection, Surface
from pycadwork.element.plate import Plate
from pycadwork.gridshell import (
    GridShellBuilder,
    HubJoint,
    MiterPolicy,
    TriangulatedSurfaceBuilder,
)
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _two_triangle_surfaces() -> list[Surface]:
    # Flat 2x2 grid -> two triangles sharing the diagonal -> 5 unique edges.
    grid = [
        [Point3D(0, 0, 0), Point3D(1000, 0, 0)],
        [Point3D(0, 1000, 0), Point3D(1000, 1000, 0)],
    ]
    return TriangulatedSurfaceBuilder().from_grid(grid).build()


# ---- members ----


def test_members_creates_one_beam_per_unique_edge():
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).members(RectSection(60, 200)).build()
    assert len(result.members) == 5
    assert not result.warnings


def test_members_miters_only_valence_two_nodes(fake_cadwork: FakeCadworkAdapter):
    surfaces = _two_triangle_surfaces()
    GridShellBuilder(surfaces).members(RectSection(60, 200)).build()
    # The two valence-2 corner nodes each get one miter; valence-3 nodes none.
    assert len(fake_cadwork.state.miter_calls) == 2


def test_members_never_issue_a_plane_cut(fake_cadwork: FakeCadworkAdapter):
    # A plane through a rib's own axis is degenerate for ACIS; the members
    # strategy must never boolean-cut ribs against the shell.
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).members(RectSection(60, 200)).build()
    assert fake_cadwork.state.plane_cut_calls == []
    # centred ribs stay on the (flat, z=0) mesh edges
    assert all(beam.geometry.start_point.z == 0 for beam in result.members)


def test_seat_on_surface_offsets_ribs_below_shell(fake_cadwork: FakeCadworkAdapter):
    surfaces = _two_triangle_surfaces()  # flat mesh, up = +z, rib height 200
    result = (
        GridShellBuilder(surfaces)
        .members(RectSection(60, 200))
        .seat_on_surface()
        .build()
    )
    assert fake_cadwork.state.plane_cut_calls == []  # offset, not a cut
    assert all(beam.geometry.start_point.z == -100 for beam in result.members)


def test_members_miter_none_skips_miters(fake_cadwork: FakeCadworkAdapter):
    surfaces = _two_triangle_surfaces()
    (
        GridShellBuilder(surfaces)
        .members(RectSection(60, 200))
        .miter_policy(MiterPolicy.NONE)
        .build()
    )
    assert fake_cadwork.state.miter_calls == []


def test_hub_joints_shorten_ribs_at_multi_rib_nodes():
    # Flat 2x2 mesh: (0,0) and (1000,1000) are valence-3 hubs; the two other
    # corners are valence-2. gap=100 pulls each rib back from every hub end.
    surfaces = _two_triangle_surfaces()
    result = (
        GridShellBuilder(surfaces).members(RectSection(60, 200)).hub_joints(100).build()
    )
    lengths = sorted(float(beam.geometry.length) for beam in result.members)
    diagonal = math.hypot(1000, 1000)
    # 4 boundary ribs touch one hub -> 1000 - 100; the diagonal touches two.
    assert lengths[:4] == pytest.approx([900, 900, 900, 900])
    assert lengths[4] == pytest.approx(diagonal - 200)


def test_hub_joints_never_issue_a_plane_cut(fake_cadwork: FakeCadworkAdapter):
    # The setback shortens the axis at creation; it is not a boolean cut.
    surfaces = _two_triangle_surfaces()
    GridShellBuilder(surfaces).members(RectSection(60, 200)).hub_joints(100).build()
    assert fake_cadwork.state.plane_cut_calls == []


def test_hub_node_is_never_also_mitered(fake_cadwork: FakeCadworkAdapter):
    # THROUGH_PAIR would otherwise miter the two valence-3 nodes too (4 calls);
    # with hub joints those nodes are skipped, leaving only the valence-2 pair.
    surfaces = _two_triangle_surfaces()
    (
        GridShellBuilder(surfaces)
        .members(RectSection(60, 200))
        .hub_joints(100)
        .miter_policy(MiterPolicy.THROUGH_PAIR)
        .build()
    )
    assert len(fake_cadwork.state.miter_calls) == 2


def test_hub_joints_compose_with_seat_on_surface(fake_cadwork: FakeCadworkAdapter):
    surfaces = _two_triangle_surfaces()  # flat mesh, up = +z, rib height 200
    result = (
        GridShellBuilder(surfaces)
        .members(RectSection(60, 200))
        .hub_joints(100)
        .seat_on_surface()
        .build()
    )
    assert fake_cadwork.state.plane_cut_calls == []  # both are offsets, not cuts
    assert all(beam.geometry.start_point.z == -100 for beam in result.members)
    # still shortened along-axis: the diagonal lost 2*gap.
    longest = max(float(beam.geometry.length) for beam in result.members)
    assert longest == pytest.approx(math.hypot(1000, 1000) - 200)


def test_hub_joints_warn_and_keep_rib_full_when_edge_too_short():
    surfaces = _two_triangle_surfaces()  # edges are 1000 / ~1414 long
    result = (
        GridShellBuilder(surfaces)
        .members(RectSection(60, 200))
        .hub_joints(5000)  # far larger than any edge
        .build()
    )
    assert result.warnings
    assert all(w.startswith("hub joint: edge") for w in result.warnings)
    # left full length: the diagonal keeps its untrimmed length.
    longest = max(float(beam.geometry.length) for beam in result.members)
    assert longest == pytest.approx(math.hypot(1000, 1000))


def test_hub_joint_rejects_bad_arguments():
    with pytest.raises(ValueError, match="gap must be positive"):
        HubJoint(gap=0.0)
    with pytest.raises(ValueError, match="min_valence must be >= 3"):
        HubJoint(gap=100.0, min_valence=2)


def test_single_surface_input_is_accepted():
    surface = _two_triangle_surfaces()[0]  # one triangle -> 3 edges, no interior
    result = GridShellBuilder(surface).members(RectSection(60, 200)).build()
    assert len(result.members) == 3


# ---- panels ----


def test_panels_creates_one_plate_per_face(fake_cadwork: FakeCadworkAdapter):
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).panels(40.0).build()
    assert len(result.panels) == 2
    assert all(isinstance(p, Plate) for p in result.panels)


def test_panels_never_miter(fake_cadwork: FakeCadworkAdapter):
    # The flat triangular panels tile the surface directly; no boolean cuts.
    surfaces = _two_triangle_surfaces()
    GridShellBuilder(surfaces).panels(40.0).build()
    assert fake_cadwork.state.miter_calls == []


def test_panels_are_built_from_polygons_not_extruded_surfaces(
    fake_cadwork: FakeCadworkAdapter,
):
    # Panels are created directly from the face polygon (create_polygon_panel),
    # so no intermediate surface is ever made or deleted; the panels survive.
    surfaces = _two_triangle_surfaces()
    before = sum(el.snapshot.is_surface for el in fake_cadwork.state.elements.values())
    result = GridShellBuilder(surfaces).panels(40.0).build()
    for panel in result.panels:
        assert panel.id in fake_cadwork.state.elements
    # build_panels neither creates nor deletes any intermediate surface.
    after = sum(el.snapshot.is_surface for el in fake_cadwork.state.elements.values())
    assert after == before


def test_panels_have_a_right_handed_local_frame(fake_cadwork: FakeCadworkAdapter):
    # cadwork is right-handed: xl x yl must equal zl for every panel.
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).panels(40.0).build()
    for panel in result.panels:
        el = fake_cadwork.state.elements[panel.id]
        cross = _cross(el.xl, el.yl)
        assert cross == pytest.approx(el.zl)


def test_panels_extrude_along_the_face_normal(fake_cadwork: FakeCadworkAdapter):
    # Flat mesh (z=0): every panel's local Z (the thickness/normal axis) is +Z.
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).panels(40.0).build()
    for panel in result.panels:
        el = fake_cadwork.state.elements[panel.id]
        assert el.zl == pytest.approx((0.0, 0.0, 1.0))
        assert el.height == pytest.approx(40.0)  # thickness along the normal


def test_panels_polygon_winds_ccw_about_the_normal(fake_cadwork: FakeCadworkAdapter):
    # The stored polygon winds CCW about the panel's normal / thickness axis
    # (local Z): (v1-v0) x (v2-v0) points along +zl.
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).panels(40.0).build()
    for panel in result.panels:
        el = fake_cadwork.state.elements[panel.id]
        v0, v1, v2 = el.surface_points[:3]
        edge_1 = _sub(v1, v0)
        edge_2 = _sub(v2, v0)
        assert _dot(_cross(edge_1, edge_2), el.zl) > 0.0


def test_panels_pass_a_closed_polygon_to_cadwork(fake_cadwork: FakeCadworkAdapter):
    # cadwork's polygon-panel builder needs a *closed* loop; an open one yields
    # an invalid element with no error (the live "zero panels, no error" bug).
    # The adapter seam closes it, so every stored polygon starts and ends on the
    # same vertex.
    surfaces = _two_triangle_surfaces()
    result = GridShellBuilder(surfaces).panels(40.0).build()
    for panel in result.panels:
        el = fake_cadwork.state.elements[panel.id]
        assert el.surface_points[0] == el.surface_points[-1]
        assert len(el.surface_points) == 4  # 3 triangle vertices + closing repeat


# ---- guards ----


def test_build_without_mode_raises():
    with pytest.raises(ValueError, match="no mode set"):
        GridShellBuilder(_two_triangle_surfaces()).build()
