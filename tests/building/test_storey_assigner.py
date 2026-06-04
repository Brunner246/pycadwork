"""StoreyAssigner against the fake adapter: assignment, marking, aggregates."""

from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    BuildingName,
    Point3D,
    RectSection,
    StoreyAssigner,
    Wall,
    from_id,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode


def _beam_z(z_lo: float, z_hi: float, *, y: float = 0.0) -> Beam:
    """A beam whose AABB spans ``[z_lo, z_hi]`` vertically."""
    return Beam.create_rectangular(
        RectSection(80.0, z_hi - z_lo),
        AxisPoints(
            Point3D(0.0, y, z_lo),
            Point3D(0.0, y + 1000.0, z_lo),
            Point3D(0.0, y, z_lo + 1.0),
        ),
    )


def _register_three_storeys(building: str = "B") -> None:
    cadwork.bim.set_storey_height(building, "S0", 0.0)
    cadwork.bim.set_storey_height(building, "S1", 3000.0)
    cadwork.bim.set_storey_height(building, "S2", 6000.0)


def test_loose_elements_assigned_to_their_storey():
    _register_three_storeys()
    ground = _beam_z(100.0, 2900.0)
    first = _beam_z(3100.0, 3500.0)

    StoreyAssigner(BuildingName("B")).assign([ground, first])

    assert cadwork.bim.get_building(ground.id) == "B"
    assert cadwork.bim.get_storey(ground.id) == "S0"
    assert cadwork.bim.get_storey(first.id) == "S1"


def test_straddling_element_assigned_to_majority_and_marked():
    _register_three_storeys()
    spanning = _beam_z(2900.0, 3300.0)  # 100 in S0, 300 in S1

    report = StoreyAssigner(BuildingName("B")).assign([spanning])

    assert cadwork.bim.get_storey(spanning.id) == "S1"
    # default marker lands in user_attribute slot 1
    assert cadwork.attributes.get_user_attribute(spanning.id, 1) == "spans-storeys"
    assert report[0].spans is True


def test_non_straddling_element_is_not_marked():
    _register_three_storeys()
    clean = _beam_z(100.0, 2900.0)

    StoreyAssigner(BuildingName("B")).assign([clean])

    assert cadwork.attributes.get_user_attribute(clean.id, 1) == ""


def test_mark_attribute_index_and_value_are_configurable():
    _register_three_storeys()
    spanning = _beam_z(2900.0, 3300.0)

    StoreyAssigner(
        BuildingName("B"), mark_attribute_index=7, mark_value="REVIEW"
    ).assign([spanning])

    assert cadwork.attributes.get_user_attribute(spanning.id, 7) == "REVIEW"


def test_building_without_storeys_raises():
    spanning = _beam_z(100.0, 200.0)
    with pytest.raises(ValueError, match="no storeys"):
        StoreyAssigner(BuildingName("Empty")).assign([spanning])


def test_aggregate_forces_parent_storey_onto_children():
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    _register_three_storeys()

    parent = _beam_z(3100.0, 3500.0)  # S1
    child_low = _beam_z(100.0, 500.0)  # would be S0 if loose
    child_mid = _beam_z(200.0, 800.0)  # would be S0 if loose
    cadwork.attributes.set_cover_kind([parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([parent.id, child_low.id, child_mid.id], "Wall1")

    wall = from_id(parent.id)
    assert isinstance(wall, Wall)

    # Pass a child loosely too: the ``seen`` set must keep it on the parent storey.
    StoreyAssigner(BuildingName("B")).assign([wall, child_low])

    assert cadwork.bim.get_storey(parent.id) == "S1"
    assert cadwork.bim.get_storey(child_low.id) == "S1"
    assert cadwork.bim.get_storey(child_mid.id) == "S1"
    assert cadwork.bim.get_building(child_mid.id) == "B"
