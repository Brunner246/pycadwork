"""BuildingQuery: building → storeys → elements navigation over the store."""

from __future__ import annotations

from pycadwork.persistence import BuildingQuery, open_sqlite
from pycadwork.persistence.gateways import (
    BuildingGateway,
    ElementGateway,
    ProjectGateway,
    StoreyAssignmentGateway,
    StoreyGateway,
)
from pycadwork.persistence.records import (
    BuildingRecord,
    ElementRecord,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
)


def _seed(connection, guid: str = "g") -> None:
    """One project, building "B", storeys S0@0.0 and S1@3.0, three elements.

    Elements 1 and 2 are assigned to S0; element 3 to S1.
    """
    ProjectGateway(connection).upsert(ProjectRecord(guid, name="P"))
    BuildingGateway(connection).upsert(BuildingRecord(guid, "B"))
    # Insert S1 before S0 so any building-scoped read must sort, not rely on order.
    StoreyGateway(connection).upsert(StoreyRecord(guid, "B", "S1", 3.0))
    StoreyGateway(connection).upsert(StoreyRecord(guid, "B", "S0", 0.0))
    for eid in (1, 2, 3):
        ElementGateway(connection).upsert(ElementRecord(guid, eid, "beam"))
    gateway = StoreyAssignmentGateway(connection)
    gateway.upsert(StoreyAssignmentRecord(guid, 1, "B", "S0"))
    gateway.upsert(StoreyAssignmentRecord(guid, 2, "B", "S0"))
    gateway.upsert(StoreyAssignmentRecord(guid, 3, "B", "S1"))


def test_buildings_lists_the_project_buildings() -> None:
    connection = open_sqlite(":memory:")
    _seed(connection)

    assert BuildingQuery(connection, "g").buildings() == [BuildingRecord("g", "B")]


def test_storeys_are_returned_ascending_by_elevation() -> None:
    connection = open_sqlite(":memory:")
    _seed(connection)

    storeys = BuildingQuery(connection, "g").storeys("B")

    assert [s.name for s in storeys] == ["S0", "S1"]
    assert [s.elevation for s in storeys] == [0.0, 3.0]


def test_elements_returns_only_that_storeys_assignments_sorted_by_id() -> None:
    connection = open_sqlite(":memory:")
    _seed(connection)
    query = BuildingQuery(connection, "g")

    s0 = query.elements("B", "S0")
    s1 = query.elements("B", "S1")

    assert [e.id for e in s0] == [1, 2]
    assert all(isinstance(e, ElementRecord) for e in s0)
    assert [e.id for e in s1] == [3]


def test_unknown_building_and_storey_yield_empty() -> None:
    connection = open_sqlite(":memory:")
    _seed(connection)
    query = BuildingQuery(connection, "g")

    assert query.storeys("missing") == []
    assert query.elements("B", "missing") == []
    assert query.elements("missing", "S0") == []
