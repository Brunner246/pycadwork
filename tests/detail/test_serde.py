"""Serialization round-trips for geometry specs, properties, and definitions.

Every spec type must survive ``to_dict`` -> ``from_dict`` and a JSON string
round-trip, the ``$type`` discriminator must keep the structurally-similar
sections apart, default properties must encode sparsely, and an unknown key must
fail loudly.
"""

from __future__ import annotations

import pytest

from pycadwork.cadwork_adapter.types import CoverKind, DetailType
from pycadwork.detail import serde
from pycadwork.detail.definition import DetailDefinition, MemberSpec
from pycadwork.detail.properties import (
    CuttingElement,
    Distribution,
    ModuleProperties,
    ModulePropertyError,
)
from pycadwork.geometry import (
    AxisFrame,
    AxisPoints,
    PanelSection,
    Point3D,
    RectSection,
    Vector3D,
)


@pytest.mark.parametrize(
    "obj",
    [
        Point3D(1.0, 2.0, 3.0),
        Vector3D(0.0, 0.0, 1.0),
        RectSection(60.0, 120.0),
        PanelSection(600.0, 15.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)),
        AxisFrame(Point3D(0, 0, 0), Vector3D(1, 0, 0), Vector3D(0, 0, 1), 2500.0),
    ],
)
def test_geometry_spec_round_trip(obj):
    assert serde.decode(serde.encode(obj)) == obj


def test_type_discriminator_disambiguates_sections():
    rect = serde.encode(RectSection(60.0, 120.0))
    panel = serde.encode(PanelSection(60.0, 120.0))
    assert rect["$type"] == "RectSection"
    assert panel["$type"] == "PanelSection"
    assert isinstance(serde.decode(rect), RectSection)
    assert isinstance(serde.decode(panel), PanelSection)


def test_decode_without_type_tag_errors():
    with pytest.raises(serde.SerdeError, match="discriminator"):
        serde.decode({"width": 1, "height": 2})


def test_decode_unknown_type_errors():
    with pytest.raises(serde.SerdeError, match="unknown"):
        serde.decode({"$type": "Banana"})


def test_default_properties_encode_sparsely():
    assert ModuleProperties().to_dict() == {}


def test_non_default_properties_round_trip():
    props = ModuleProperties(
        auxiliary=True,
        distribute_in_axis=Distribution(active=True, count=4),
        cutting_element=CuttingElement(active=True, priority=2),
    )
    data = props.to_dict()
    assert set(data) == {"auxiliary", "distribute_in_axis", "cutting_element"}
    assert ModuleProperties.from_dict(data) == props


def test_properties_unknown_key_errors():
    with pytest.raises(ModulePropertyError, match="unknown"):
        ModuleProperties.from_dict({"not_a_field": True})


def test_member_spec_round_trip_with_frame_placement():
    spec = MemberSpec(
        kind="beam",
        section=RectSection(60, 120),
        frame=AxisFrame(Point3D(0, 0, 0), Vector3D(1, 0, 0), Vector3D(0, 0, 1), 2500),
        role="stud",
        name="S1",
        material="GL24h",
    )
    assert MemberSpec.from_dict(spec.to_dict()) == spec


def test_definition_json_round_trip():
    definition = DetailDefinition(
        name="corner",
        detail_type=DetailType.CORNER_DETAIL,
        cover_kind=CoverKind.FRAMED_WALL,
        members=(
            MemberSpec(
                kind="beam",
                section=RectSection(60, 120),
                points=AxisPoints(
                    Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)
                ),
                role="stud",
            ),
            MemberSpec(
                kind="panel",
                section=PanelSection(600, 15),
                points=AxisPoints(
                    Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)
                ),
                properties=ModuleProperties(auxiliary=True),
            ),
        ),
        metadata={"author": "test"},
    )
    assert DetailDefinition.from_json(definition.to_json()) == definition
