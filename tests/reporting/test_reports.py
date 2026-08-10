"""cutting_list and material_totals: aggregation, identity, filters, ordering."""

from __future__ import annotations

from pycadwork.persistence.records import (
    AttributeRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
)
from pycadwork.reporting import (
    by_group,
    by_material,
    cutting_list,
    material_totals,
)


def _part(
    eid: int,
    *,
    element_type: str = "beam",
    name: str = "Stud",
    material: str = "Pine",
    group: str = "",
    length: float = 3000.0,
    width: float = 80.0,
    height: float = 200.0,
    volume: float = 0.048,
    weight: float = 24.0,
) -> tuple[ElementRecord, AttributeRecord, GeometryRecord]:
    return (
        ElementRecord("g", eid, element_type),
        AttributeRecord("g", eid, name=name, material_name=material, group_name=group),
        GeometryRecord(
            "g",
            eid,
            length=length,
            width=width,
            height=height,
            volume=volume,
            weight=weight,
        ),
    )


def _snapshot(
    *parts: tuple[ElementRecord, AttributeRecord, GeometryRecord]
) -> ModelSnapshot:
    return ModelSnapshot(
        project=ProjectRecord("g"),
        elements=tuple(p[0] for p in parts),
        attributes=tuple(p[1] for p in parts),
        geometries=tuple(p[2] for p in parts),
    )


def test_identical_parts_aggregate_into_one_row() -> None:
    rows = cutting_list(_snapshot(_part(2), _part(1), _part(3)))

    assert len(rows) == 1
    row = rows[0]
    assert row.count == 3
    assert row.total_volume == 3 * 0.048
    assert row.total_weight == 3 * 24.0
    assert row.element_ids == (1, 2, 3)
    assert row.group == ()


def test_differing_name_material_or_dimension_splits_rows() -> None:
    rows = cutting_list(
        _snapshot(
            _part(1),
            _part(2, name="Post"),
            _part(3, material="Oak"),
            _part(4, length=2500.0),
        )
    )
    assert len(rows) == 4
    assert all(r.count == 1 for r in rows)


def test_precision_rounds_dimension_identity() -> None:
    snapshot = _snapshot(_part(1, length=199.96), _part(2, length=200.0))

    assert len(cutting_list(snapshot, precision=1)) == 1
    assert len(cutting_list(snapshot, precision=2)) == 2


def test_default_part_types_exclude_non_stock() -> None:
    rows = cutting_list(
        _snapshot(
            _part(1),
            _part(10, element_type="wall"),
            _part(11, element_type="container"),
            _part(12, element_type="drilling"),
        )
    )
    assert len(rows) == 1
    assert rows[0].element_type == "beam"


def test_part_types_filter_is_overridable() -> None:
    snapshot = _snapshot(_part(1), _part(12, element_type="drilling"))
    rows = cutting_list(snapshot, part_types=frozenset({"drilling"}))
    assert [r.element_type for r in rows] == ["drilling"]


def test_missing_satellites_key_to_defaults() -> None:
    snapshot = ModelSnapshot(
        project=ProjectRecord("g"), elements=(ElementRecord("g", 1, "beam"),)
    )
    rows = cutting_list(snapshot)
    assert rows[0].name == ""
    assert rows[0].material_name == ""
    assert rows[0].length == 0.0
    assert rows[0].total_volume == 0.0


def test_composed_dimensions_split_and_label_rows() -> None:
    rows = cutting_list(
        _snapshot(
            _part(1, group="W1"),
            _part(2, group="W1"),
            _part(3, group="W2", material="Oak"),
        ),
        dimensions=(by_group(), by_material()),
    )

    assert [(r.group, r.count) for r in rows] == [
        (("W1", "Pine"), 2),
        (("W2", "Oak"), 1),
    ]


def test_output_ordering_is_deterministic() -> None:
    parts = [_part(1, material="Pine"), _part(2, material="Oak"), _part(3, name="Post")]
    forward = cutting_list(_snapshot(*parts))
    backward = cutting_list(_snapshot(*reversed(parts)))
    assert forward == backward
    assert [r.material_name for r in forward] == ["Oak", "Pine", "Pine"]


def test_material_totals_match_cutting_list_sums() -> None:
    snapshot = _snapshot(
        _part(1),
        _part(2, name="Post", volume=0.1, weight=50.0),
        _part(3, material="Oak", volume=0.2, weight=100.0),
    )

    totals = {r.material_name: r for r in material_totals(snapshot)}
    parts = cutting_list(snapshot)

    for material, total in totals.items():
        matching = [r for r in parts if r.material_name == material]
        assert total.count == sum(r.count for r in matching)
        assert total.total_volume == sum(r.total_volume for r in matching)
        assert total.total_weight == sum(r.total_weight for r in matching)
    assert set(totals) == {"Pine", "Oak"}


def test_material_totals_respect_dimensions() -> None:
    rows = material_totals(
        _snapshot(_part(1, group="W1"), _part(2, group="W2")),
        dimensions=(by_group(),),
    )
    assert [(r.group, r.count) for r in rows] == [(("W1",), 1), (("W2",), 1)]
