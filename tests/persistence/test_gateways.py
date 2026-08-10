"""Per-table gateways: upsert→select round-trips and conflict-updates."""

from __future__ import annotations

from pycadwork.persistence import open_sqlite
from pycadwork.persistence.gateways import (
    BuildingGateway,
    ElementGateway,
    ElementMaterialGateway,
    GeometryGateway,
    MaterialGateway,
    ProjectGateway,
    StoreyAssignmentGateway,
    StoreyGateway,
)
from pycadwork.persistence.records import (
    BuildingRecord,
    ElementMaterialRecord,
    ElementRecord,
    GeometryRecord,
    MaterialRecord,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
)


def _seed_project(connection, guid: str = "g") -> None:
    ProjectGateway(connection).upsert(ProjectRecord(guid, name="P"))


def _seed_element(connection, eid: int, guid: str = "g") -> None:
    ElementGateway(connection).upsert(ElementRecord(guid, eid, "beam"))


def test_element_upsert_select_roundtrip() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    record = ElementRecord("g", 1, "beam", "cadwork-guid-1", None)

    ElementGateway(connection).upsert(record)

    assert ElementGateway(connection).select_for_project("g") == [record]


def test_upsert_updates_non_key_columns_on_conflict() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    gateway = ElementGateway(connection)

    gateway.upsert(ElementRecord("g", 1, "beam"))
    gateway.upsert(ElementRecord("g", 1, "plate", "guid-x", 5))

    rows = gateway.select_for_project("g")
    assert len(rows) == 1
    assert rows[0].element_type == "plate"
    assert rows[0].cadwork_guid == "guid-x"
    assert rows[0].parent_container_id == 5


def test_geometry_roundtrip_preserves_scalars() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    _seed_element(connection, 1)
    record = GeometryRecord(
        "g", 1, p1x=1.0, p2y=2.0, width=80.0, height=200.0, length=3000.0, volume=42.0
    )

    GeometryGateway(connection).upsert(record)

    assert GeometryGateway(connection).select_for_project("g") == [record]


def test_select_is_scoped_to_one_project() -> None:
    connection = open_sqlite(":memory:")
    ProjectGateway(connection).upsert(ProjectRecord("g1"))
    ProjectGateway(connection).upsert(ProjectRecord("g2"))
    ElementGateway(connection).upsert(ElementRecord("g1", 1, "beam"))
    ElementGateway(connection).upsert(ElementRecord("g2", 2, "plate"))

    rows = ElementGateway(connection).select_for_project("g1")
    assert [r.id for r in rows] == [1]


def test_all_key_table_upsert_does_not_raise_on_conflict() -> None:
    # ``building``'s columns are all part of its key, so the upsert resolves to
    # DO NOTHING — a repeated upsert must be a clean no-op, not an error.
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    gateway = BuildingGateway(connection)

    gateway.upsert(BuildingRecord("g", "B"))
    gateway.upsert(BuildingRecord("g", "B"))

    assert gateway.select_for_project("g") == [BuildingRecord("g", "B")]


def test_storey_assignment_spans_roundtrips_as_bool() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    BuildingGateway(connection).upsert(BuildingRecord("g", "B"))
    StoreyGateway(connection).upsert(StoreyRecord("g", "B", "S0", 0.0))
    _seed_element(connection, 1)
    record = StoreyAssignmentRecord("g", 1, "B", "S0", spans=True)

    StoreyAssignmentGateway(connection).upsert(record)

    rows = StoreyAssignmentGateway(connection).select_for_project("g")
    assert rows == [record]
    assert rows[0].spans is True


def test_select_for_building_is_scoped_to_one_building() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    gateway = StoreyGateway(connection)
    BuildingGateway(connection).upsert(BuildingRecord("g", "A"))
    BuildingGateway(connection).upsert(BuildingRecord("g", "B"))
    gateway.upsert(StoreyRecord("g", "A", "S0", 0.0))
    gateway.upsert(StoreyRecord("g", "B", "S0", 0.0))
    gateway.upsert(StoreyRecord("g", "B", "S1", 3.0))

    rows = gateway.select_for_building("g", "B")

    assert {r.name for r in rows} == {"S0", "S1"}
    assert {r.building_name for r in rows} == {"B"}


def test_select_for_storey_is_scoped_to_one_storey() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    BuildingGateway(connection).upsert(BuildingRecord("g", "B"))
    StoreyGateway(connection).upsert(StoreyRecord("g", "B", "S0", 0.0))
    StoreyGateway(connection).upsert(StoreyRecord("g", "B", "S1", 3.0))
    _seed_element(connection, 1)
    _seed_element(connection, 2)
    gateway = StoreyAssignmentGateway(connection)
    gateway.upsert(StoreyAssignmentRecord("g", 1, "B", "S0"))
    gateway.upsert(StoreyAssignmentRecord("g", 2, "B", "S1"))

    rows = gateway.select_for_storey("g", "B", "S0")

    assert [r.element_id for r in rows] == [1]


def test_material_roundtrip_preserves_structural_props() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    record = MaterialRecord(
        "g",
        "Pine",
        group_name="Softwood",
        grade="C24",
        modulus_elasticity_1=11000.0,
        shear_modulus_1=690.0,
        weight=420.0,
    )

    MaterialGateway(connection).upsert(record)

    assert MaterialGateway(connection).select_for_project("g") == [record]


def test_element_material_link_roundtrips() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    _seed_element(connection, 1)
    MaterialGateway(connection).upsert(MaterialRecord("g", "Pine"))
    record = ElementMaterialRecord("g", 1, "cadwork-guid-1", "Pine")

    ElementMaterialGateway(connection).upsert(record)

    assert ElementMaterialGateway(connection).select_for_project("g") == [record]


def test_element_material_requires_an_existing_material() -> None:
    # The link's (project_guid, material_name) FK must reference a master row.
    import sqlite3

    import pytest

    connection = open_sqlite(":memory:")
    _seed_project(connection)
    _seed_element(connection, 1)

    with pytest.raises(sqlite3.IntegrityError):
        ElementMaterialGateway(connection).upsert(
            ElementMaterialRecord("g", 1, "guid", "Nonexistent")
        )


def test_select_for_ids_filters_to_the_given_ids() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    for eid in (1, 2, 3):
        _seed_element(connection, eid)

    rows = ElementGateway(connection).select_for_ids("g", [1, 3])

    assert sorted(r.id for r in rows) == [1, 3]


def test_select_for_ids_short_circuits_on_empty() -> None:
    connection = open_sqlite(":memory:")
    _seed_project(connection)
    _seed_element(connection, 1)

    assert ElementGateway(connection).select_for_ids("g", []) == []


def test_select_for_ids_is_scoped_to_one_project() -> None:
    connection = open_sqlite(":memory:")
    ProjectGateway(connection).upsert(ProjectRecord("g1"))
    ProjectGateway(connection).upsert(ProjectRecord("g2"))
    ElementGateway(connection).upsert(ElementRecord("g1", 1, "beam"))
    ElementGateway(connection).upsert(ElementRecord("g2", 1, "plate"))

    rows = ElementGateway(connection).select_for_ids("g1", [1])

    assert [r.element_type for r in rows] == ["beam"]
