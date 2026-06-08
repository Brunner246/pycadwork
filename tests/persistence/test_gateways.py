"""Per-table gateways: upsert→select round-trips and conflict-updates."""

from __future__ import annotations

from pycadwork.persistence import open_sqlite
from pycadwork.persistence.gateways import (
    BuildingGateway,
    ElementGateway,
    GeometryGateway,
    ProjectGateway,
    StoreyAssignmentGateway,
    StoreyGateway,
)
from pycadwork.persistence.records import (
    BuildingRecord,
    ElementRecord,
    GeometryRecord,
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
