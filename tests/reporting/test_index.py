"""SnapshotIndex serves O(1) per-element lookups and the cover-label map."""

from __future__ import annotations

import pytest

from pycadwork.persistence.records import (
    AttributeRecord,
    CoverRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
    StoreyAssignmentRecord,
)
from pycadwork.reporting import SnapshotIndex


def _snapshot(**kwargs: object) -> ModelSnapshot:
    return ModelSnapshot(project=ProjectRecord("g"), **kwargs)  # type: ignore[arg-type]


def test_lookups_return_the_matching_satellite() -> None:
    index = SnapshotIndex(
        _snapshot(
            elements=(ElementRecord("g", 1, "beam"),),
            attributes=(AttributeRecord("g", 1, name="Stud"),),
            geometries=(GeometryRecord("g", 1, length=3000.0),),
            storey_assignments=(StoreyAssignmentRecord("g", 1, "B", "GF"),),
        )
    )

    assert index.attribute(1).name == "Stud"
    assert index.geometry(1).length == 3000.0
    assert index.assignment(1).storey_name == "GF"


def test_lookups_return_none_for_missing_satellites() -> None:
    index = SnapshotIndex(_snapshot(elements=(ElementRecord("g", 1, "beam"),)))

    assert index.attribute(1) is None
    assert index.geometry(1) is None
    assert index.assignment(1) is None


def test_cover_labels_link_by_group_or_subgroup() -> None:
    index = SnapshotIndex(
        _snapshot(
            elements=(ElementRecord("g", 10, "wall"),),
            attributes=(
                AttributeRecord("g", 10, name="WallA", group_name="W1", subgroup="SG1"),
            ),
            covers=(CoverRecord("g", 10, "framed_wall"),),
        )
    )

    assert index.cover_label_by_link_key("group") == {"W1": "WallA"}
    assert index.cover_label_by_link_key("subgroup") == {"SG1": "WallA"}


def test_unnamed_cover_parent_falls_back_to_kind_and_key() -> None:
    index = SnapshotIndex(
        _snapshot(
            elements=(ElementRecord("g", 10, "wall"),),
            attributes=(AttributeRecord("g", 10, group_name="W1"),),
            covers=(CoverRecord("g", 10, "framed_wall"),),
        )
    )

    assert index.cover_label_by_link_key("group") == {"W1": "framed_wall:W1"}


def test_cover_without_link_key_is_omitted() -> None:
    index = SnapshotIndex(
        _snapshot(
            elements=(ElementRecord("g", 10, "wall"),),
            attributes=(AttributeRecord("g", 10, name="WallA"),),  # no group value
            covers=(CoverRecord("g", 10, "framed_wall"),),
        )
    )

    assert index.cover_label_by_link_key("group") == {}


def test_unknown_link_raises() -> None:
    index = SnapshotIndex(_snapshot())
    with pytest.raises(ValueError, match="link"):
        index.cover_label_by_link_key("comment")
