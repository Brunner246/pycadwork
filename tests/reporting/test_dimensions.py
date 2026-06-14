"""Each by_* factory yields a labelled, ""-falling-back grouping axis."""

from __future__ import annotations

import pytest

from pycadwork.persistence.records import (
    AttributeRecord,
    CoverRecord,
    ElementRecord,
    ModelSnapshot,
    ProjectRecord,
    StoreyAssignmentRecord,
)
from pycadwork.reporting import (
    SnapshotIndex,
    by_cover,
    by_group,
    by_material,
    by_storey,
    by_subgroup,
)


def _index(**kwargs: object) -> SnapshotIndex:
    return SnapshotIndex(ModelSnapshot(project=ProjectRecord("g"), **kwargs))  # type: ignore[arg-type]


_ATTRIBUTED = dict(
    elements=(ElementRecord("g", 1, "beam"),),
    attributes=(
        AttributeRecord("g", 1, material_name="Pine", group_name="W1", subgroup="SG1"),
    ),
)


def test_by_material() -> None:
    dimension = by_material()
    assert dimension.label == "material"
    assert dimension.key_of(_index(**_ATTRIBUTED), 1) == "Pine"


def test_by_group_and_by_subgroup() -> None:
    index = _index(**_ATTRIBUTED)
    assert by_group().label == "group"
    assert by_group().key_of(index, 1) == "W1"
    assert by_subgroup().label == "subgroup"
    assert by_subgroup().key_of(index, 1) == "SG1"


def test_missing_attribute_record_keys_to_empty() -> None:
    index = _index(elements=(ElementRecord("g", 1, "beam"),))
    assert by_material().key_of(index, 1) == ""
    assert by_group().key_of(index, 1) == ""
    assert by_subgroup().key_of(index, 1) == ""


def test_by_storey_joins_building_and_storey() -> None:
    index = _index(
        elements=(ElementRecord("g", 1, "beam"),),
        storey_assignments=(StoreyAssignmentRecord("g", 1, "Building A", "GF"),),
    )
    assert by_storey().label == "storey"
    assert by_storey().key_of(index, 1) == "Building A/GF"
    assert by_storey(separator=" · ").key_of(index, 1) == "Building A · GF"


def test_by_storey_unassigned_keys_to_empty() -> None:
    index = _index(elements=(ElementRecord("g", 1, "beam"),))
    assert by_storey().key_of(index, 1) == ""


def test_by_cover_labels_members_through_the_shared_key() -> None:
    index = _index(
        elements=(ElementRecord("g", 10, "wall"), ElementRecord("g", 1, "beam")),
        attributes=(
            AttributeRecord("g", 10, name="WallA", group_name="W1"),
            AttributeRecord("g", 1, group_name="W1"),
        ),
        covers=(CoverRecord("g", 10, "framed_wall"),),
    )
    dimension = by_cover()
    assert dimension.label == "cover"
    assert dimension.key_of(index, 1) == "WallA"
    # The parent itself shares the key and gets its own label too.
    assert dimension.key_of(index, 10) == "WallA"


def test_by_cover_via_subgroup_link() -> None:
    index = _index(
        elements=(ElementRecord("g", 10, "wall"), ElementRecord("g", 1, "beam")),
        attributes=(
            AttributeRecord("g", 10, name="WallA", subgroup="SG1"),
            AttributeRecord("g", 1, subgroup="SG1"),
        ),
        covers=(CoverRecord("g", 10, "framed_wall"),),
    )
    assert by_cover(link="subgroup").key_of(index, 1) == "WallA"


def test_by_cover_loose_element_keys_to_empty() -> None:
    index = _index(
        elements=(ElementRecord("g", 1, "beam"),),
        attributes=(AttributeRecord("g", 1, group_name="loose"),),
    )
    assert by_cover().key_of(index, 1) == ""


def test_by_cover_rejects_unknown_link() -> None:
    with pytest.raises(ValueError, match="link"):
        by_cover(link="comment")
