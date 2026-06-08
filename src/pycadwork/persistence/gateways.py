"""Table Data Gateways — one per table, all SQL lives here.

Each gateway owns the four statements for its table: ``upsert`` (insert, or
update on PK conflict — the idempotent path a repeated ``pull`` takes),
``update``, ``delete``, and ``select_for_project``. No SQL string appears
anywhere else in the package.

The :class:`TableDataGateway` base does the work generically: a record's field
names match its table's column names one-for-one and in order (enforced by
:mod:`pycadwork.persistence.records` / :mod:`~pycadwork.persistence.schema`),
so a record (de)serializes with a single positional pass. A concrete gateway is
then just three class attributes — ``record_cls``, ``table``, ``columns``,
``pk`` — plus, where a column needs a Python type SQLite can't round-trip on its
own, an override of :meth:`TableDataGateway._from_row` (only the storey-spanning
``bool`` needs this).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from pycadwork.persistence._connection import GatewayConnection
from pycadwork.persistence._ids import ElementId, ProjectGuid
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

R = TypeVar("R")


class TableDataGateway(Generic[R]):
    """Generic Table Data Gateway: maps one record type ↔ one table's rows."""

    record_cls: type[R]
    table: str
    columns: tuple[str, ...]
    pk: tuple[str, ...]

    __slots__ = ("_connection",)

    def __init__(self, connection: GatewayConnection) -> None:
        self._connection = connection

    # ---- row <-> record ----

    def _to_row(self, record: R) -> tuple[Any, ...]:
        return tuple(getattr(record, column) for column in self.columns)

    def _from_row(self, row: tuple[Any, ...]) -> R:
        return self.record_cls(**dict(zip(self.columns, row)))

    def _non_pk_columns(self) -> tuple[str, ...]:
        return tuple(c for c in self.columns if c not in self.pk)

    # ---- operations ----

    def upsert(self, record: R) -> None:
        """Insert ``record``; on PK conflict, update its non-key columns in place.

        This is the idempotent write a ``pull`` uses for both new and changed
        rows. Tables whose columns are *all* part of the key (``building``,
        ``container_member``) have nothing to update, so the conflict resolves
        to ``DO NOTHING``.
        """
        placeholders = ", ".join("?" for _ in self.columns)
        column_list = ", ".join(self.columns)
        conflict = ", ".join(self.pk)
        non_pk = self._non_pk_columns()
        if non_pk:
            assignments = ", ".join(f"{c} = excluded.{c}" for c in non_pk)
            action = f"DO UPDATE SET {assignments}"
        else:
            action = "DO NOTHING"
        sql = (
            f"INSERT INTO {self.table} ({column_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict}) {action}"
        )
        self._connection.execute(sql, self._to_row(record))

    def update(self, record: R) -> None:
        """Update ``record``'s non-key columns, matched by primary key."""
        non_pk = self._non_pk_columns()
        if not non_pk:
            return
        assignments = ", ".join(f"{c} = ?" for c in non_pk)
        where = " AND ".join(f"{c} = ?" for c in self.pk)
        params = [getattr(record, c) for c in non_pk]
        params += [getattr(record, c) for c in self.pk]
        self._connection.execute(
            f"UPDATE {self.table} SET {assignments} WHERE {where}", params
        )

    def delete(self, record: R) -> None:
        """Delete the row matching ``record``'s primary key."""
        where = " AND ".join(f"{c} = ?" for c in self.pk)
        params = [getattr(record, c) for c in self.pk]
        self._connection.execute(f"DELETE FROM {self.table} WHERE {where}", params)

    def _select_where(self, **equals: Any) -> list[R]:
        """Rows whose columns equal the given values (AND-combined), as records."""
        where = " AND ".join(f"{c} = ?" for c in equals)
        column_list = ", ".join(self.columns)
        rows = self._connection.execute(
            f"SELECT {column_list} FROM {self.table} WHERE {where}",
            list(equals.values()),
        )
        return [self._from_row(row) for row in rows]

    def select_for_project(self, project_guid: ProjectGuid) -> list[R]:
        """Every row of this table belonging to ``project_guid``, as records."""
        return self._select_where(project_guid=project_guid)


class ProjectGateway(TableDataGateway[ProjectRecord]):
    record_cls = ProjectRecord
    table = "project"
    columns = (
        "project_guid",
        "name",
        "number",
        "part",
        "architect",
        "customer",
        "designer",
        "deadline",
        "description",
        "address",
        "postal_code",
        "city",
        "country",
        "latitude",
        "longitude",
        "elevation",
    )
    pk = ("project_guid",)


class ElementGateway(TableDataGateway[ElementRecord]):
    record_cls = ElementRecord
    table = "element"
    columns = (
        "project_guid",
        "id",
        "element_type",
        "cadwork_guid",
        "parent_container_id",
    )
    pk = ("project_guid", "id")

    def select_for_ids(
        self, project_guid: ProjectGuid, ids: Sequence[ElementId]
    ) -> list[ElementRecord]:
        """The element rows for ``ids`` within ``project_guid`` (``id`` is the key).

        ``_select_where`` cannot serve this — it tests equality, and this needs an
        ``IN`` set — so the one variadic ``IN`` clause in the package lives here.
        An empty ``ids`` short-circuits to ``[]`` (an empty ``IN ()`` is invalid SQL).
        """
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        column_list = ", ".join(self.columns)
        rows = self._connection.execute(
            f"SELECT {column_list} FROM {self.table} "
            f"WHERE project_guid = ? AND id IN ({placeholders})",
            [project_guid, *ids],
        )
        return [self._from_row(row) for row in rows]


class AttributeGateway(TableDataGateway[AttributeRecord]):
    record_cls = AttributeRecord
    table = "attribute"
    columns = (
        "project_guid",
        "element_id",
        "name",
        "group_name",
        "subgroup",
        "comment",
        "material_name",
        "sku",
        "production_number",
        "part_number",
        "assembly_number",
    )
    pk = ("project_guid", "element_id")


class GeometryGateway(TableDataGateway[GeometryRecord]):
    record_cls = GeometryRecord
    table = "geometry"
    columns = (
        "project_guid",
        "element_id",
        "p1x",
        "p1y",
        "p1z",
        "p2x",
        "p2y",
        "p2z",
        "p3x",
        "p3y",
        "p3z",
        "length",
        "width",
        "height",
        "volume",
        "weight",
        "cog_x",
        "cog_y",
        "cog_z",
        "aabb_min_x",
        "aabb_min_y",
        "aabb_min_z",
        "aabb_max_x",
        "aabb_max_y",
        "aabb_max_z",
    )
    pk = ("project_guid", "element_id")


class UserAttributeGateway(TableDataGateway[UserAttributeRecord]):
    record_cls = UserAttributeRecord
    table = "user_attribute"
    columns = ("project_guid", "element_id", "attr_index", "value")
    pk = ("project_guid", "element_id", "attr_index")


class CoverGateway(TableDataGateway[CoverRecord]):
    record_cls = CoverRecord
    table = "cover"
    columns = ("project_guid", "element_id", "cover_kind")
    pk = ("project_guid", "element_id")


class ContainerMemberGateway(TableDataGateway[ContainerMemberRecord]):
    record_cls = ContainerMemberRecord
    table = "container_member"
    columns = ("project_guid", "container_id", "member_id")
    pk = ("project_guid", "container_id", "member_id")


class BuildingGateway(TableDataGateway[BuildingRecord]):
    record_cls = BuildingRecord
    table = "building"
    columns = ("project_guid", "name")
    pk = ("project_guid", "name")


class StoreyGateway(TableDataGateway[StoreyRecord]):
    record_cls = StoreyRecord
    table = "storey"
    columns = ("project_guid", "building_name", "name", "elevation")
    pk = ("project_guid", "building_name", "name")

    def select_for_building(
        self, project_guid: ProjectGuid, building_name: str
    ) -> list[StoreyRecord]:
        """The storeys under ``building_name`` within ``project_guid``."""
        return self._select_where(
            project_guid=project_guid, building_name=building_name
        )


class StoreyAssignmentGateway(TableDataGateway[StoreyAssignmentRecord]):
    record_cls = StoreyAssignmentRecord
    table = "storey_assignment"
    columns = ("project_guid", "element_id", "building_name", "storey_name", "spans")
    pk = ("project_guid", "element_id")

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
        values = dict(zip(self.columns, row))
        values["spans"] = bool(values["spans"])
        return StoreyAssignmentRecord(**values)
