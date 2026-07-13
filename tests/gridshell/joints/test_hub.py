"""HubConnectorJoint: section-aware setback + connector + dowels at hub nodes.

Flat 2x2 mesh: nodes (0,0) and (1000,1000) are valence-3 hubs; the two other
corners are valence-2. Five unique edges (four boundary ribs each touch one hub,
the diagonal touches both).
"""

from __future__ import annotations

import math

import pytest

from pycadwork import Point3D, RectSection, Surface
from pycadwork.element.connector_axis import ConnectorAxis
from pycadwork.element.drilling import Drilling
from pycadwork.gridshell import GridShellBuilder, TriangulatedSurfaceBuilder
from pycadwork.gridshell.joints import HubConnectorJoint
from pycadwork.gridshell.specs import MiterPolicy
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _two_triangle_surfaces() -> list[Surface]:
    grid = [
        [Point3D(0, 0, 0), Point3D(1000, 0, 0)],
        [Point3D(0, 1000, 0), Point3D(1000, 1000, 0)],
    ]
    return TriangulatedSurfaceBuilder().from_grid(grid).build()


def _build(joint) -> object:
    return (
        GridShellBuilder(_two_triangle_surfaces())
        .members(RectSection(60, 200))
        .joint(joint)
        .build()
    )


def test_places_one_connector_per_hub():
    result = _build(HubConnectorJoint(gap=100, connector_name="hub-plate"))
    assert len(result.connectors) == 2  # two valence-3 hubs
    assert all(isinstance(c, ConnectorAxis) for c in result.connectors)


def test_no_connector_without_a_name():
    # Setback-only (the legacy hub_joints behaviour): no connector, no dowels.
    result = _build(HubConnectorJoint(gap=100))
    assert result.connectors == ()
    assert result.drillings == ()


def test_dowels_one_per_rib_incident_to_a_hub():
    result = _build(
        HubConnectorJoint(gap=100, connector_name="hub", dowel_diameter=12.0)
    )
    # Both hubs are valence 3 -> 3 + 3 dowels (the diagonal is dowelled at each end).
    assert len(result.drillings) == 6
    assert all(isinstance(d, Drilling) for d in result.drillings)


def test_auto_gap_is_section_derived_when_gap_is_none():
    # height 200 -> auto setback 0.75 * 200 = 150.
    result = _build(HubConnectorJoint())
    lengths = sorted(float(beam.geometry.length) for beam in result.members)
    diagonal = math.hypot(1000, 1000)
    assert lengths[:4] == pytest.approx([850, 850, 850, 850])  # each touches one hub
    assert lengths[4] == pytest.approx(diagonal - 300)  # diagonal touches two


def test_hub_still_miters_valence_two_corners(fake_cadwork: FakeCadworkAdapter):
    _build(HubConnectorJoint(gap=100, connector_name="hub"))
    # The two valence-2 corners are mitered; the valence-3 hubs are not.
    assert len(fake_cadwork.state.miter_calls) == 2


def test_hub_never_issues_a_plane_cut(fake_cadwork: FakeCadworkAdapter):
    # Setback is an axis edit; connector/dowels are element creation. No cuts.
    _build(HubConnectorJoint(gap=100, connector_name="hub", dowel_diameter=12.0))
    assert fake_cadwork.state.plane_cut_calls == []


def test_connector_axis_spans_the_node_along_the_normal(
    fake_cadwork: FakeCadworkAdapter,
):
    # Flat mesh -> normal is +z; connector is centred on the hub, height = section.
    result = _build(HubConnectorJoint(gap=100, connector_name="hub"))
    for connector in result.connectors:
        el = fake_cadwork.state.elements[connector.id]
        assert el.p1[2] == pytest.approx(-100.0)  # -half of section height 200
        assert el.p2[2] == pytest.approx(100.0)
        assert el.p1[0] == pytest.approx(el.p2[0])  # vertical: same x/y
        assert el.p1[1] == pytest.approx(el.p2[1])


def test_rejects_bad_arguments():
    with pytest.raises(ValueError, match="gap must be positive"):
        HubConnectorJoint(gap=0.0)
    with pytest.raises(ValueError, match="min_valence must be >= 3"):
        HubConnectorJoint(gap=100, min_valence=2)
    with pytest.raises(ValueError, match="dowel_diameter must be positive"):
        HubConnectorJoint(dowel_diameter=0.0)


def test_through_pair_miters_only_non_hub_nodes(fake_cadwork: FakeCadworkAdapter):
    _build(
        HubConnectorJoint(
            gap=100, connector_name="hub", miter_policy=MiterPolicy.THROUGH_PAIR
        )
    )
    # Hubs are skipped; only the two valence-2 corners miter.
    assert len(fake_cadwork.state.miter_calls) == 2
