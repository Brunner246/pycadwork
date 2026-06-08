"""open_sqlite applies the full schema, and re-applying it is idempotent."""

from __future__ import annotations

from pycadwork.persistence import open_sqlite
from pycadwork.persistence.schema import TABLES


def _table_names(connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {row[0] for row in rows}


def test_open_sqlite_creates_all_ten_tables() -> None:
    connection = open_sqlite(":memory:")
    assert len(TABLES) == 10
    assert set(TABLES) <= _table_names(connection)


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
