"""MiterJoint via the .joint() entry point (pairwise cadwork miters)."""

from __future__ import annotations

from pycadwork import Point3D, RectSection, Surface
from pycadwork.gridshell import GridShellBuilder, TriangulatedSurfaceBuilder
from pycadwork.gridshell.joints import MiterJoint
from pycadwork.gridshell.specs import MiterPolicy
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


def test_valence_2_only_miters_two_corners(fake_cadwork: FakeCadworkAdapter):
    _build(MiterJoint(MiterPolicy.VALENCE_2_ONLY))
    assert len(fake_cadwork.state.miter_calls) == 2


def test_none_policy_skips_all_miters(fake_cadwork: FakeCadworkAdapter):
    _build(MiterJoint(MiterPolicy.NONE))
    assert fake_cadwork.state.miter_calls == []


def test_through_pair_also_miters_the_hubs(fake_cadwork: FakeCadworkAdapter):
    # No setback here, so unlike the hub joint, THROUGH_PAIR miters every node's
    # straightest pair: 2 valence-3 hubs + 2 valence-2 corners = 4 miters.
    _build(MiterJoint(MiterPolicy.THROUGH_PAIR))
    assert len(fake_cadwork.state.miter_calls) == 4


def test_joint_overrides_legacy_flags(fake_cadwork: FakeCadworkAdapter):
    # An explicit .joint(...) wins over .miter_policy(...)/.hub_joints(...).
    (
        GridShellBuilder(_two_triangle_surfaces())
        .members(RectSection(60, 200))
        .miter_policy(MiterPolicy.NONE)
        .joint(MiterJoint(MiterPolicy.VALENCE_2_ONLY))
        .build()
    )
    assert len(fake_cadwork.state.miter_calls) == 2
