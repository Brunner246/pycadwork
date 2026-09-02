"""open_sqlite applies the full schema, and re-applying it is idempotent."""

from __future__ import annotations

import sqlite3

from pycadwork.persistence import open_sqlite
from pycadwork.persistence.gateways import (
    AttributeGateway,
    ElementGateway,
    ProjectGateway,
)
from pycadwork.persistence.records import AttributeRecord, ElementRecord, ProjectRecord
from pycadwork.persistence.schema import ELEMENT_MATERIAL, MATERIAL, TABLES


def _table_names(connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {row[0] for row in rows}


def test_open_sqlite_creates_all_tables() -> None:
    connection = open_sqlite(":memory:")
    assert len(TABLES) == 12
    assert set(TABLES) <= _table_names(connection)


def test_material_tables_are_present_and_shaped() -> None:
    connection = open_sqlite(":memory:")
    assert {"material", "element_material"} <= _table_names(connection)

    # The master is keyed by (project_guid, material_name); the link is keyed by
    # the element and carries the element's cadwork GUID + the joining name.
    assert MATERIAL.primary_key == ("project_guid", "material_name")
    assert "modulus_elasticity_1" in MATERIAL.column_names
    assert "cadwork_guid" in ELEMENT_MATERIAL.column_names

    # The link table references both element and material (two composite FKs).
    referenced = {fk.references for fk in ELEMENT_MATERIAL.foreign_keys}
    assert referenced == {"element", "material"}


def test_schema_is_idempotent() -> None:
    connection = open_sqlite(":memory:")
    # Re-running CREATE TABLE IF NOT EXISTS must not raise or duplicate.
    connection.init_schema()
    connection.init_schema()
    assert set(TABLES) <= _table_names(connection)


def test_attribute_table_has_ifc_type_column() -> None:
    connection = open_sqlite(":memory:")
    columns = {row[1] for row in connection.execute("PRAGMA table_info(attribute)")}
    assert "ifc_type" in columns


def test_opening_pre_column_sqlite_adds_ifc_type_and_round_trips_empty(
    tmp_path,
) -> None:
    path = tmp_path / "old.db"
    raw = sqlite3.connect(path)
    raw.executescript("""
        CREATE TABLE attribute (
            project_guid TEXT,
            element_id INTEGER,
            name TEXT DEFAULT '',
            group_name TEXT DEFAULT '',
            subgroup TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            material_name TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            production_number INTEGER DEFAULT 0,
            part_number TEXT DEFAULT '',
            assembly_number TEXT DEFAULT '',
            PRIMARY KEY (project_guid, element_id)
        );
        INSERT INTO attribute (project_guid, element_id, name)
        VALUES ('g', 1, 'Stud');
        """)
    raw.commit()
    raw.close()

    connection = open_sqlite(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(attribute)")}
    assert "ifc_type" in columns
    records = AttributeGateway(connection).select_for_project("g")
    assert len(records) == 1
    assert records[0].name == "Stud"
    assert records[0].ifc_type == ""

    ProjectGateway(connection).upsert(ProjectRecord("g"))
    ElementGateway(connection).upsert(ElementRecord("g", 1, "beam"))
    AttributeGateway(connection).upsert(
        AttributeRecord("g", 1, name="Stud", ifc_type="")
    )
    again = AttributeGateway(connection).select_for_project("g")
    assert again[0].ifc_type == ""


def test_attribute_gateway_roundtrips_ifc_type() -> None:
    connection = open_sqlite(":memory:")
    ProjectGateway(connection).upsert(ProjectRecord("g"))
    ElementGateway(connection).upsert(ElementRecord("g", 1, "beam"))
    record = AttributeRecord("g", 1, name="Stud", ifc_type="IfcBeam")
    AttributeGateway(connection).upsert(record)
    assert AttributeGateway(connection).select_for_project("g") == [record]


def test_schema_survives_reopening_a_file(tmp_path) -> None:
    path = tmp_path / "model.db"
    first = open_sqlite(path)
    first.execute("INSERT INTO project (project_guid, name) VALUES ('g', 'P')")
    first.close()

    second = open_sqlite(path)
    rows = second.execute("SELECT name FROM project WHERE project_guid = 'g'")
    assert rows == [("P",)]
