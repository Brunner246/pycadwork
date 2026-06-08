"""The database seam — one Protocol, one stdlib implementation.

Everything above this module talks to SQL through :class:`GatewayConnection`, a
narrow Protocol of just ``execute`` plus a ``transaction()`` context manager.
The only implementation today is :class:`SqliteConnection` over stdlib
``sqlite3`` (no new pyproject dependency), but the Protocol is the seam a future
``SqlAlchemyConnection`` drops into without touching gateways or the unit of
work.

:func:`open_sqlite` is the front door: it opens a connection in autocommit mode
(``isolation_level=None`` — so *we* own every ``BEGIN`` / ``COMMIT`` boundary,
not Python's implicit-transaction machinery), turns on foreign-key enforcement,
and applies the idempotent schema.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Protocol, runtime_checkable

from pycadwork.persistence.schema import SCHEMA_SQL


@runtime_checkable
class GatewayConnection(Protocol):
    """The minimal database surface gateways and the unit of work rely on.

    ``execute`` runs one statement and returns the fetched rows (empty for
    writes); ``transaction`` brackets a set of statements so they commit
    together or roll back together. Anything satisfying this shape — a real
    SQLite handle, a SQLAlchemy-backed adapter, an in-memory test double — is a
    valid backend.
    """

    def execute(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[tuple[Any, ...]]: ...

    def transaction(self) -> AbstractContextManager[None]: ...


class SqliteConnection:  # (GatewayConnection)
    """A :class:`GatewayConnection` over a stdlib ``sqlite3`` connection."""

    __slots__ = ("_conn",)

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        # Enforce the schema's foreign keys (off by default in SQLite) so a
        # cascading delete actually cascades and a dangling FK is rejected.
        self._conn.execute("PRAGMA foreign_keys = ON")

    def init_schema(self) -> None:
        """Apply :data:`SCHEMA_SQL`. Idempotent — safe to call on every open."""
        self._conn.executescript(SCHEMA_SQL)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        """Run ``sql`` with ``params`` and return all result rows (``[]`` for writes)."""
        return self._conn.execute(sql, tuple(params)).fetchall()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Bracket a block in one transaction: ``BEGIN`` → ``COMMIT`` / ``ROLLBACK``.

        Any exception rolls the whole block back and re-raises, so a partial
        write never reaches disk. With ``isolation_level=None`` the BEGIN /
        COMMIT are explicit SQL, not implicit Python state.
        """
        self._conn.execute("BEGIN")
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")

    def close(self) -> None:
        self._conn.close()


def open_sqlite(path: str | os.PathLike[str]) -> SqliteConnection:
    """Open (or create) a SQLite database and apply the schema.

    ``path`` may be a filesystem path or ``":memory:"`` for an ephemeral store.
    The connection runs in autocommit mode so :meth:`SqliteConnection.transaction`
    is the single owner of transaction boundaries; the schema is applied via
    ``CREATE TABLE IF NOT EXISTS`` so re-opening an existing database is a no-op.
    """
    raw = sqlite3.connect(path, isolation_level=None)
    connection = SqliteConnection(raw)
    connection.init_schema()
    return connection
