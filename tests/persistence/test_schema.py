"""open_sqlite applies the full schema, and re-applying it is idempotent."""

from __future__ import annotations

from pycadwork.persistence import open_sqlite
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


def test_schema_survives_reopening_a_file(tmp_path) -> None:
    path = tmp_path / "model.db"
    first = open_sqlite(path)
    first.execute("INSERT INTO project (project_guid, name) VALUES ('g', 'P')")
    first.close()

    second = open_sqlite(path)
    rows = second.execute("SELECT name FROM project WHERE project_guid = 'g'")
    assert rows == [("P",)]
