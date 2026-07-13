"""SpherePavilionBuilder end-to-end against the FakeCadworkAdapter."""

from __future__ import annotations

import pytest

from pycadwork import Point3D, RectSection
from pycadwork.element.beam import Beam
from pycadwork.element.plate import Plate
from pycadwork.sphere import SpherePavilionBuilder
from tests._fakes.cadwork_adapter import FakeCadworkAdapter

# ---- frame + cladding together ----


def test_builds_frame_and_cladding_in_one_result():
    # Frequency 1 icosahedron: 30 struts, 20 faces.
    result = (
        SpherePavilionBuilder(1000.0)
        .frequency(1)
        .timber(RectSection(60, 120))
        .cladding(thickness=20.0, gap=10.0)
        .build()
    )
    assert len(result.members) == 30
    assert all(isinstance(m, Beam) for m in result.members)
    assert len(result.panels) == 20
    assert all(isinstance(p, Plate) for p in result.panels)


def test_frame_only_when_no_cladding_requested():
    result = (
        SpherePavilionBuilder(1000.0).frequency(1).timber(RectSection(60, 120)).build()
    )
    assert len(result.members) == 30
    assert result.panels == ()


# ---- the shift-cut (radial bisector) node joint ----


def test_high_valence_nodes_get_radial_bisector_cuts(fake_cadwork: FakeCadworkAdapter):
    # Every icosahedron node is valence 5, so RadialMiterJoint cuts each strut on
    # its neighbours' bisector planes -> many plane cuts, and no miters.
    SpherePavilionBuilder(1000.0).frequency(1).timber(RectSection(60, 120)).build()
    assert fake_cadwork.state.plane_cut_calls  # rosette bisector cuts issued
    assert fake_cadwork.state.miter_calls == []


# ---- strut schedule ----


def test_icosahedron_reports_a_single_strut_group():
    result = (
        SpherePavilionBuilder(1000.0).frequency(1).timber(RectSection(60, 120)).build()
    )
    assert len(result.strut_groups) == 1
    (group,) = result.strut_groups
    assert group.count == 30
    assert len(group.member_indices) == 30


def test_higher_frequency_reports_several_strut_groups():
    result = (
        SpherePavilionBuilder(1000.0).frequency(3).timber(RectSection(60, 120)).build()
    )
    assert len(result.strut_groups) > 1
    # every strut belongs to exactly one group
    assert sum(g.count for g in result.strut_groups) == len(result.members)


# ---- ground truncation: clean base ring on the cut ----


def test_ground_cut_leaves_a_coplanar_base_and_a_sill_ring():
    full = (
        SpherePavilionBuilder(1000.0).frequency(3).timber(RectSection(60, 120)).build()
    )
    domed = (
        SpherePavilionBuilder(1000.0)
        .frequency(3)
        .ground_cut(0.0)  # snaps to the ring nearest the equator
        .timber(RectSection(60, 120))
        .build()
    )
    # fewer struts than the whole sphere, and the base-ring edges are excluded
    assert 0 < len(domed.members) < len(full.members)
    # the cut snapped to a node ring: base nodes are coplanar, lifted onto z=0
    assert min(node.position.z for node in domed.nodes) == pytest.approx(0.0)
    # a dedicated sill ring closes the base, is tagged, and is perfectly flat
    assert len(domed.ring) >= 5
    assert all(beam.attrs.name == "Base Ring" for beam in domed.ring)
    assert all(
        beam.geometry.start_point.z == pytest.approx(0.0)
        and beam.geometry.end_point.z == pytest.approx(0.0)
        for beam in domed.ring
    )


def test_ground_cut_uses_no_boolean_subtraction(fake_cadwork: FakeCadworkAdapter):
    # The base is formed by cutting at a node ring, not by subtracting a block.
    SpherePavilionBuilder(1000.0).frequency(2).ground_cut(0.0).timber(
        RectSection(60, 120)
    ).build()
    assert fake_cadwork.state.subtract_calls == []


def test_full_sphere_has_no_ring_or_foundation():
    result = (
        SpherePavilionBuilder(1000.0).frequency(2).timber(RectSection(60, 120)).build()
    )
    assert result.ring == ()
    assert result.foundation is None


def test_sill_uses_its_own_section(fake_cadwork: FakeCadworkAdapter):
    result = (
        SpherePavilionBuilder(1000.0)
        .frequency(2)
        .ground_cut(0.0)
        .timber(RectSection(60, 120))
        .sill(RectSection(100, 200))
        .build()
    )
    assert result.ring
    for beam in result.ring:
        element = fake_cadwork.state.elements[beam.id]
        assert (element.width, element.height) == pytest.approx((100.0, 200.0))


# ---- foundation ----


def test_foundation_builds_a_tagged_slab(fake_cadwork: FakeCadworkAdapter):
    result = (
        SpherePavilionBuilder(1000.0)
        .frequency(2)
        .ground_cut(0.0)
        .timber(RectSection(60, 120))
        .foundation(300.0, material="C25/30")
        .build()
    )
    assert isinstance(result.foundation, Plate)
    element = fake_cadwork.state.elements[result.foundation.id]
    assert element.name == "Foundation"
    assert element.material == "C25/30"
    assert element.height == pytest.approx(300.0)  # slab thickness


def test_foundation_without_ground_cut_is_skipped_with_warning():
    result = (
        SpherePavilionBuilder(1000.0)
        .frequency(1)
        .timber(RectSection(60, 120))
        .foundation(300.0)
        .build()
    )
    assert result.foundation is None
    assert any("foundation" in w for w in result.warnings)


def test_explicit_center_places_the_sphere():
    origin = Point3D(5000.0, 5000.0, 5000.0)
    result = (
        SpherePavilionBuilder(1000.0)
        .frequency(1)
        .center(origin)
        .timber(RectSection(60, 120))
        .build()
    )
    for node in result.nodes:
        assert float(node.position.distance_to(origin)) == pytest.approx(1000.0)


# ---- guards ----


def test_build_without_timber_or_cladding_raises():
    with pytest.raises(ValueError, match="nothing to build"):
        SpherePavilionBuilder(1000.0).build()


def test_rejects_non_positive_radius():
    with pytest.raises(ValueError, match="radius must be positive"):
        SpherePavilionBuilder(0.0)


def test_rejects_frequency_below_one():
    with pytest.raises(ValueError, match="frequency must be >= 1"):
        SpherePavilionBuilder(1000.0).frequency(0)


def test_rejects_negative_ground_cut():
    with pytest.raises(ValueError, match="ground_cut must not be negative"):
        SpherePavilionBuilder(1000.0).ground_cut(-1.0)
