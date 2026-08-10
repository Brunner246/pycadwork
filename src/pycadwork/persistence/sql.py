"""The SQL dialect — table-as-data plus the statement builders.

This is the one place SQL text is assembled. A table is modelled as data
(:class:`Table` of :class:`Column` / :class:`ForeignKey`), and every statement
the package runs is *generated* from that model: :func:`create_table` emits the
DDL, and :class:`Insert` / :class:`Update` / :class:`Delete` / :class:`Select`
emit the DML. Nothing above this module writes a SQL string by hand.

The builders produce SQL **text only**. Values stay caller-supplied as positional
``?`` placeholders — the builder never interpolates a value, so the existing
parameter-binding discipline (and its injection safety) is untouched. The fluent
shape mirrors :class:`pycadwork.element.cover.builder.CoverBuilder`: configuration
methods return ``self`` and :meth:`~Insert.sql` is the terminal.

The schema model is the *single source of truth* a table is declared with:
:mod:`pycadwork.persistence.schema` builds its ``Table`` literals here, and the
gateways in :mod:`pycadwork.persistence.gateways` read their column / key sets
off the very same objects — so a table's shape lives in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Final


class ColumnType(str, Enum):
    """The three storage classes the schema uses (SQLite's affinity names)."""

    TEXT = "TEXT"
    INTEGER = "INTEGER"
    REAL = "REAL"


# Sentinel for "this column has no DEFAULT clause" — distinct from ``None``,
# which is itself a legitimate (NULL) default we never need to emit here.
_NO_DEFAULT: Final[object] = object()


@dataclass(frozen=True, slots=True)
class Column:
    """One column: its name, storage type, nullability, and optional default."""

    name: str
    type: ColumnType
    not_null: bool = True
    default: Any = _NO_DEFAULT

    @property
    def has_default(self) -> bool:
        return self.default is not _NO_DEFAULT


@dataclass(frozen=True, slots=True)
class ForeignKey:
    """A (possibly composite) foreign key to ``references`` (``ref_columns``)."""

    columns: tuple[str, ...]
    references: str
    ref_columns: tuple[str, ...]
    on_delete: str = "CASCADE"


@dataclass(frozen=True, slots=True)
class Table:
    """A table's full shape: columns, primary key, and foreign keys."""

    name: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKey, ...] = ()

    @property
    def column_names(self) -> tuple[str, ...]:
        """Every column name, in declaration order."""
        return tuple(column.name for column in self.columns)

    def non_pk_columns(self) -> tuple[str, ...]:
        """The column names that are *not* part of the primary key, in order."""
        return tuple(c.name for c in self.columns if c.name not in self.primary_key)


# ---- DDL ----


def _render_default(value: Any) -> str:
    """The literal for a ``DEFAULT`` clause: text is quoted, numerics are bare."""
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def _render_column(column: Column) -> str:
    parts = [column.name, column.type.value]
    if column.not_null:
        parts.append("NOT NULL")
    if column.has_default:
        parts.append(f"DEFAULT {_render_default(column.default)}")
    return " ".join(parts)


def _render_foreign_key(fk: ForeignKey) -> str:
    columns = ", ".join(fk.columns)
    ref_columns = ", ".join(fk.ref_columns)
    return (
        f"FOREIGN KEY ({columns}) "
        f"REFERENCES {fk.references} ({ref_columns}) ON DELETE {fk.on_delete}"
    )


def create_table(table: Table) -> str:
    """The idempotent ``CREATE TABLE IF NOT EXISTS`` statement for ``table``.

    The primary key is always emitted as a table-level ``PRIMARY KEY (...)``
    constraint (valid for single and composite keys alike), followed by any
    foreign-key constraints.
    """
    clauses = [_render_column(column) for column in table.columns]
    clauses.append(f"PRIMARY KEY ({', '.join(table.primary_key)})")
    clauses.extend(_render_foreign_key(fk) for fk in table.foreign_keys)
    body = ",\n    ".join(clauses)
    return f"CREATE TABLE IF NOT EXISTS {table.name} (\n    {body}\n);"


# ---- DML ----


class Insert:
    """``INSERT INTO table (cols) VALUES (?, ...)``, optionally upserting."""

    __slots__ = ("_table", "_on_conflict")

    def __init__(self, table: Table) -> None:
        self._table = table
        self._on_conflict = False

    def on_conflict_update(self) -> Insert:
        """On primary-key conflict, update the non-key columns from the new row.

        A table whose columns are *all* part of its key has nothing to update,
        so the conflict resolves to ``DO NOTHING`` — a repeated insert is then a
        clean no-op rather than an error.
        """
        self._on_conflict = True
        return self

    def sql(self) -> str:
        columns = self._table.column_names
        column_list = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        statement = (
            f"INSERT INTO {self._table.name} ({column_list}) "
            f"VALUES ({placeholders})"
        )
        if not self._on_conflict:
            return statement
        conflict = ", ".join(self._table.primary_key)
        non_pk = self._table.non_pk_columns()
        if non_pk:
            assignments = ", ".join(f"{c} = excluded.{c}" for c in non_pk)
            action = f"DO UPDATE SET {assignments}"
        else:
            action = "DO NOTHING"
        return f"{statement} ON CONFLICT ({conflict}) {action}"


class Update:
    """``UPDATE table SET nonpk = ? ... WHERE pk = ? ...`` (matched by key)."""

    __slots__ = ("_table",)

    def __init__(self, table: Table) -> None:
        self._table = table

    def sql(self) -> str:
        assignments = ", ".join(f"{c} = ?" for c in self._table.non_pk_columns())
        where = " AND ".join(f"{c} = ?" for c in self._table.primary_key)
        return f"UPDATE {self._table.name} SET {assignments} WHERE {where}"


class Delete:
    """``DELETE FROM table WHERE pk = ? ...`` (matched by key)."""

    __slots__ = ("_table",)

    def __init__(self, table: Table) -> None:
        self._table = table

    def sql(self) -> str:
        where = " AND ".join(f"{c} = ?" for c in self._table.primary_key)
        return f"DELETE FROM {self._table.name} WHERE {where}"


class Select:
    """``SELECT cols FROM table`` with AND-combined equality / IN conditions.

    Conditions accumulate in call order; the caller supplies the parameters in
    that same order. ``where_in(col, n)`` emits ``n`` placeholders, so the caller
    must pass exactly ``n`` values for it (an empty ``IN ()`` is invalid SQL).
    """

    __slots__ = ("_table", "_conditions")

    def __init__(self, table: Table) -> None:
        self._table = table
        self._conditions: list[str] = []

    def where_eq(self, *columns: str) -> Select:
        """Add ``column = ?`` for each of ``columns``."""
        self._conditions.extend(f"{column} = ?" for column in columns)
        return self

    def where_in(self, column: str, count: int) -> Select:
        """Add ``column IN (?, ...)`` with ``count`` placeholders."""
        placeholders = ", ".join("?" for _ in range(count))
        self._conditions.append(f"{column} IN ({placeholders})")
        return self

    def sql(self) -> str:
        column_list = ", ".join(self._table.column_names)
        statement = f"SELECT {column_list} FROM {self._table.name}"
        if self._conditions:
            statement += " WHERE " + " AND ".join(self._conditions)
        return statement


# ---- transaction control ----

PRAGMA_FOREIGN_KEYS_ON: Final = "PRAGMA foreign_keys = ON"
BEGIN: Final = "BEGIN"
COMMIT: Final = "COMMIT"
ROLLBACK: Final = "ROLLBACK"
