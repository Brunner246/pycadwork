"""UnitOfWork: commit persists atomically; any error rolls the whole thing back."""

from __future__ import annotations

import sqlite3

import pytest

from pycadwork.persistence import UnitOfWork, open_sqlite
from pycadwork.persistence.gateways import ElementGateway, ProjectGateway
from pycadwork.persistence.records import (
    AttributeRecord,
    ElementRecord,
    ProjectRecord,
)


def test_commit_persists_all_registered_records() -> None:
    connection = open_sqlite(":memory:")
    unit = UnitOfWork(connection)
    unit.register_new(ProjectRecord("g", name="P"))
    unit.register_new(ElementRecord("g", 1, "beam"))

    unit.commit()

    assert ProjectGateway(connection).select_for_project("g")[0].name == "P"
    assert [e.id for e in ElementGateway(connection).select_for_project("g")] == [1]


def test_commit_orders_parents_before_children() -> None:
    # The element FK points at project; registering the child first must still
    # commit, because the UoW reorders to gateway (parent→child) order.
    connection = open_sqlite(":memory:")
    unit = UnitOfWork(connection)
    unit.register_new(ElementRecord("g", 1, "beam"))
    unit.register_new(ProjectRecord("g"))

    unit.commit()

    assert [e.id for e in ElementGateway(connection).select_for_project("g")] == [1]


def test_a_failing_gateway_rolls_back_the_whole_transaction() -> None:
    connection = open_sqlite(":memory:")
    unit = UnitOfWork(connection)
    unit.register_new(ProjectRecord("g"))
    # An attribute for a non-existent element violates the FK at commit time.
    unit.register_new(AttributeRecord("g", 999, name="orphan"))

    with pytest.raises(sqlite3.IntegrityError):
        unit.commit()

    # The project insert that preceded the failure must not have survived.
    assert ProjectGateway(connection).select_for_project("g") == []


def test_register_removed_deletes_on_commit() -> None:
    connection = open_sqlite(":memory:")
    setup = UnitOfWork(connection)
    setup.register_new(ProjectRecord("g"))
    setup.register_new(ElementRecord("g", 1, "beam"))
    setup.commit()

    remove = UnitOfWork(connection)
    remove.register_removed(ElementRecord("g", 1, ""))
    remove.commit()

    assert ElementGateway(connection).select_for_project("g") == []


def test_unknown_record_type_raises() -> None:
    connection = open_sqlite(":memory:")
    unit = UnitOfWork(connection)
    unit.register_new(object())
    with pytest.raises(TypeError, match="no gateway"):
        unit.commit()
