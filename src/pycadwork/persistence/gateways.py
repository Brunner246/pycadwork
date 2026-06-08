"""Table Data Gateways — one per table, all DML built by the SQL builder.

Each gateway owns the four statements for its table: ``upsert`` (insert, or
update on PK conflict — the idempotent path a repeated ``pull`` takes),
``update``, ``delete``, and ``select_for_project``. None of them write SQL by
hand: every statement is assembled by :mod:`pycadwork.persistence.sql` from the
gateway's :class:`~pycadwork.persistence.sql.Table` definition.

That ``Table`` is the *single source of truth* for the table's shape — the same
object :mod:`pycadwork.persistence.schema` renders to DDL. A record's field names
match its table's column names one-for-one and in order, so a record
(de)serializes with a single positional pass. A concrete gateway is then just two
class attributes — ``record_cls`` and ``schema`` — plus, where a column needs a
Python type SQLite can't round-trip on its own, an override of
:meth:`TableDataGateway._from_row` (only the storey-spanning ``bool`` needs this).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from pycadwork.persistence._connection import GatewayConnection
from pycadwork.persistence._ids import ElementId, ProjectGuid
from pycadwork.persistence.sql import Delete, Insert, Select, Table, Update
from pycadwork.persistence.records import (
    AttributeRecord,
    BuildingRecord,
    ContainerMemberRecord,
    CoverRecord,
    ElementRecord,
    GeometryRecord,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
    UserAttributeRecord,
)
from pycadwork.persistence.schema import (
    ATTRIBUTE,
    BUILDING,
    CONTAINER_MEMBER,
    COVER,
    ELEMENT,
    GEOMETRY,
    PROJECT,
    STOREY,
    STOREY_ASSIGNMENT,
    USER_ATTRIBUTE,
)

R = TypeVar("R")


class TableDataGateway(Generic[R]):
    """Generic Table Data Gateway: maps one record type ↔ one table's rows."""

    record_cls: type[R]
    schema: Table

    __slots__ = ("_connection",)

    def __init__(self, connection: GatewayConnection) -> None:
        self._connection = connection

    # ---- row <-> record ----

    def _to_row(self, record: R) -> tuple[Any, ...]:
        return tuple(getattr(record, column) for column in self.schema.column_names)

    def _from_row(self, row: tuple[Any, ...]) -> R:
        return self.record_cls(**dict(zip(self.schema.column_names, row)))

    # ---- operations ----

    def upsert(self, record: R) -> None:
        """Insert ``record``; on PK conflict, update its non-key columns in place.

        This is the idempotent write a ``pull`` uses for both new and changed
        rows. Tables whose columns are *all* part of the key (``building``,
        ``container_member``) have nothing to update, so the conflict resolves
        to ``DO NOTHING``.
        """
        sql = Insert(self.schema).on_conflict_update().sql()
        self._connection.execute(sql, self._to_row(record))

    def update(self, record: R) -> None:
        """Update ``record``'s non-key columns, matched by primary key."""
        non_pk = self.schema.non_pk_columns()
        if not non_pk:
            return
        params = [getattr(record, c) for c in non_pk]
        params += [getattr(record, c) for c in self.schema.primary_key]
        self._connection.execute(Update(self.schema).sql(), params)

    def delete(self, record: R) -> None:
        """Delete the row matching ``record``'s primary key."""
        params = [getattr(record, c) for c in self.schema.primary_key]
        self._connection.execute(Delete(self.schema).sql(), params)

    def _select_where(self, **equals: Any) -> list[R]:
        """Rows whose columns equal the given values (AND-combined), as records."""
        sql = Select(self.schema).where_eq(*equals).sql()
        rows = self._connection.execute(sql, list(equals.values()))
        return [self._from_row(row) for row in rows]

    def select_for_project(self, project_guid: ProjectGuid) -> list[R]:
        """Every row of this table belonging to ``project_guid``, as records."""
        return self._select_where(project_guid=project_guid)


class ProjectGateway(TableDataGateway[ProjectRecord]):
    record_cls = ProjectRecord
    schema = PROJECT


class ElementGateway(TableDataGateway[ElementRecord]):
    record_cls = ElementRecord
    schema = ELEMENT

    def select_for_ids(
        self, project_guid: ProjectGuid, ids: Sequence[ElementId]
    ) -> list[ElementRecord]:
        """The element rows for ``ids`` within ``project_guid`` (``id`` is the key).

        ``_select_where`` cannot serve this — it tests equality, and this needs an
        ``IN`` set — so the one ``IN`` clause in the package is built here.
        An empty ``ids`` short-circuits to ``[]`` (an empty ``IN ()`` is invalid SQL).
        """
        if not ids:
            return []
        sql = (
            Select(self.schema)
            .where_eq("project_guid")
            .where_in("id", len(ids))
            .sql()
        )
        rows = self._connection.execute(sql, [project_guid, *ids])
        return [self._from_row(row) for row in rows]


class AttributeGateway(TableDataGateway[AttributeRecord]):
    record_cls = AttributeRecord
    schema = ATTRIBUTE


class GeometryGateway(TableDataGateway[GeometryRecord]):
    record_cls = GeometryRecord
    schema = GEOMETRY


class UserAttributeGateway(TableDataGateway[UserAttributeRecord]):
    record_cls = UserAttributeRecord
    schema = USER_ATTRIBUTE


class CoverGateway(TableDataGateway[CoverRecord]):
    record_cls = CoverRecord
    schema = COVER


class ContainerMemberGateway(TableDataGateway[ContainerMemberRecord]):
    record_cls = ContainerMemberRecord
    schema = CONTAINER_MEMBER


class BuildingGateway(TableDataGateway[BuildingRecord]):
    record_cls = BuildingRecord
    schema = BUILDING


class StoreyGateway(TableDataGateway[StoreyRecord]):
    record_cls = StoreyRecord
    schema = STOREY

    def select_for_building(
        self, project_guid: ProjectGuid, building_name: str
    ) -> list[StoreyRecord]:
        """The storeys under ``building_name`` within ``project_guid``."""
        return self._select_where(
            project_guid=project_guid, building_name=building_name
        )


class StoreyAssignmentGateway(TableDataGateway[StoreyAssignmentRecord]):
    record_cls = StoreyAssignmentRecord
    schema = STOREY_ASSIGNMENT

    def select_for_storey(
        self, project_guid: ProjectGuid, building_name: str, storey_name: str
    ) -> list[StoreyAssignmentRecord]:
        """The assignments for one storey of one building within ``project_guid``."""
        return self._select_where(
            project_guid=project_guid,
            building_name=building_name,
            storey_name=storey_name,
        )

    def _from_row(self, row: tuple[Any, ...]) -> StoreyAssignmentRecord:
        # SQLite stores the ``spans`` bool as 0/1 and reads it back as int;
        # coerce it to bool so the record round-trips to the same type.
        values = dict(zip(self.schema.column_names, row))
        values["spans"] = bool(values["spans"])
        return StoreyAssignmentRecord(**values)
