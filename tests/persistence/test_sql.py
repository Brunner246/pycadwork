"""The SQL builder renders DDL and DML from table-as-data, no DB needed."""

from __future__ import annotations

from pycadwork.persistence.sql import (
    Column,
    ColumnType,
    Delete,
    ForeignKey,
    Insert,
    Select,
    Table,
    Update,
    create_table,
)

_PEOPLE = Table(
    name="people",
    columns=(
        Column("project_guid", ColumnType.TEXT),
        Column("id", ColumnType.INTEGER),
        Column("name", ColumnType.TEXT, default=""),
        Column("score", ColumnType.REAL, default=0.0),
        Column("parent_id", ColumnType.INTEGER, not_null=False),
    ),
    primary_key=("project_guid", "id"),
    foreign_keys=(ForeignKey(("project_guid",), "project", ("project_guid",)),),
)

# A table whose every column is part of the key — nothing to update on conflict.
_ALL_KEY = Table(
    name="link",
    columns=(
        Column("project_guid", ColumnType.TEXT),
        Column("a", ColumnType.INTEGER),
        Column("b", ColumnType.INTEGER),
    ),
    primary_key=("project_guid", "a", "b"),
)


# ---- table model helpers ----


def test_column_names_and_non_pk_are_in_declaration_order() -> None:
    assert _PEOPLE.column_names == ("project_guid", "id", "name", "score", "parent_id")
    assert _PEOPLE.non_pk_columns() == ("name", "score", "parent_id")


# ---- DDL ----


def test_create_table_renders_columns_pk_and_fk() -> None:
    ddl = create_table(_PEOPLE)
    assert ddl.startswith("CREATE TABLE IF NOT EXISTS people (")
    assert "project_guid TEXT NOT NULL" in ddl
    assert "id INTEGER NOT NULL" in ddl
    assert "PRIMARY KEY (project_guid, id)" in ddl
    assert (
        "FOREIGN KEY (project_guid) REFERENCES project (project_guid) "
        "ON DELETE CASCADE" in ddl
    )
    assert ddl.rstrip().endswith(");")


def test_create_table_renders_defaults_quoted_for_text_bare_for_numeric() -> None:
    ddl = create_table(_PEOPLE)
    assert "name TEXT NOT NULL DEFAULT ''" in ddl
    assert "score REAL NOT NULL DEFAULT 0.0" in ddl


def test_create_table_omits_not_null_for_nullable_column() -> None:
    ddl = create_table(_PEOPLE)
    # The nullable column carries neither NOT NULL nor a DEFAULT clause.
    assert "parent_id INTEGER" in ddl
    assert "parent_id INTEGER NOT NULL" not in ddl
    assert "parent_id INTEGER DEFAULT" not in ddl


# ---- DML: Insert ----


def test_insert_lists_every_column_with_a_placeholder_each() -> None:
    sql = Insert(_PEOPLE).sql()
    assert sql == (
        "INSERT INTO people (project_guid, id, name, score, parent_id) "
        "VALUES (?, ?, ?, ?, ?)"
    )


def test_insert_on_conflict_updates_only_non_key_columns() -> None:
    sql = Insert(_PEOPLE).on_conflict_update().sql()
    assert sql.endswith(
        "ON CONFLICT (project_guid, id) DO UPDATE SET "
        "name = excluded.name, score = excluded.score, parent_id = excluded.parent_id"
    )


def test_insert_on_conflict_does_nothing_when_all_columns_are_keys() -> None:
    sql = Insert(_ALL_KEY).on_conflict_update().sql()
    assert sql.endswith("ON CONFLICT (project_guid, a, b) DO NOTHING")


# ---- DML: Update / Delete ----


def test_update_sets_non_key_columns_matched_by_key() -> None:
    sql = Update(_PEOPLE).sql()
    assert sql == (
        "UPDATE people SET name = ?, score = ?, parent_id = ? "
        "WHERE project_guid = ? AND id = ?"
    )


def test_delete_matches_by_key() -> None:
    sql = Delete(_PEOPLE).sql()
    assert sql == "DELETE FROM people WHERE project_guid = ? AND id = ?"


# ---- DML: Select ----


def test_select_without_conditions_has_no_where() -> None:
    sql = Select(_PEOPLE).sql()
    assert sql == "SELECT project_guid, id, name, score, parent_id FROM people"


def test_select_where_eq_and_combines_conditions_in_order() -> None:
    sql = Select(_PEOPLE).where_eq("project_guid", "id").sql()
    assert sql.endswith("WHERE project_guid = ? AND id = ?")


def test_select_where_in_emits_one_placeholder_per_count() -> None:
    sql = Select(_PEOPLE).where_in("id", 3).sql()
    assert sql.endswith("WHERE id IN (?, ?, ?)")


def test_select_where_eq_then_in_and_combine_in_call_order() -> None:
    sql = Select(_PEOPLE).where_eq("project_guid").where_in("id", 2).sql()
    assert sql.endswith("WHERE project_guid = ? AND id IN (?, ?)")
