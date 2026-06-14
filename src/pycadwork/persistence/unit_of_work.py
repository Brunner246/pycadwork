"""The Unit of Work — sequence writes across gateways in one transaction.

A :class:`UnitOfWork` collects the records a ``pull`` wants to persist —
``register_new`` / ``register_dirty`` for upserts, ``register_removed`` for
deletes — and applies them all inside a single
:meth:`GatewayConnection.transaction`. Either every change lands or none does:
if any gateway raises mid-:meth:`commit`, the transaction rolls back and the
database is left exactly as it was.

The UoW dispatches each record to its table's gateway by *type*. Upserts run in
the gateways' declared (foreign-key-safe) order so a child never inserts before
its parent; deletes run in reverse for the same reason — and because the schema
cascades, deleting an ``element`` row alone clears its satellites.
"""

from __future__ import annotations

from pycadwork.persistence._connection import GatewayConnection
from pycadwork.persistence.gateways import (
    AttributeGateway,
    BuildingGateway,
    ContainerMemberGateway,
    CoverGateway,
    ElementGateway,
    ElementMaterialGateway,
    GeometryGateway,
    MaterialGateway,
    ProjectGateway,
    StoreyAssignmentGateway,
    StoreyGateway,
    TableDataGateway,
    UserAttributeGateway,
)
from pycadwork.persistence.records import (
    AttributeRecord,
    BuildingRecord,
    ContainerMemberRecord,
    CoverRecord,
    ElementMaterialRecord,
    ElementRecord,
    GeometryRecord,
    MaterialRecord,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
    UserAttributeRecord,
)


class UnitOfWork:
    """Accumulate record changes, then commit them atomically across gateways."""

    __slots__ = ("_connection", "_gateways", "_order", "_new", "_dirty", "_removed")

    def __init__(self, connection: GatewayConnection) -> None:
        self._connection = connection
        # Gateways keyed by the record type they own. The order of this dict is
        # the foreign-key-safe write order: parents before children.
        self._gateways: dict[type, TableDataGateway] = {
            ProjectRecord: ProjectGateway(connection),
            BuildingRecord: BuildingGateway(connection),
            StoreyRecord: StoreyGateway(connection),
            MaterialRecord: MaterialGateway(connection),
            ElementRecord: ElementGateway(connection),
            AttributeRecord: AttributeGateway(connection),
            GeometryRecord: GeometryGateway(connection),
            UserAttributeRecord: UserAttributeGateway(connection),
            CoverRecord: CoverGateway(connection),
            ContainerMemberRecord: ContainerMemberGateway(connection),
            StoreyAssignmentRecord: StoreyAssignmentGateway(connection),
            ElementMaterialRecord: ElementMaterialGateway(connection),
        }
        self._order: list[type] = list(self._gateways)
        self._new: list[object] = []
        self._dirty: list[object] = []
        self._removed: list[object] = []

    # ---- registration ----

    def register_new(self, record: object) -> None:
        """Stage ``record`` for upsert (insert-or-update on key conflict)."""
        self._new.append(record)

    def register_dirty(self, record: object) -> None:
        """Stage a changed ``record`` for upsert.

        Identical mechanics to :meth:`register_new` — the upsert handles both —
        but kept as a separate verb so callers can express intent.
        """
        self._dirty.append(record)

    def register_removed(self, record: object) -> None:
        """Stage ``record`` for deletion (by primary key)."""
        self._removed.append(record)

    # ---- commit / rollback ----

    def commit(self) -> None:
        """Apply every staged change in one transaction; roll back on any error.

        Upserts run first, in gateway (parent→child) order; deletes run last, in
        reverse (child→parent) order. On success the staged lists are cleared so
        the unit can be reused.
        """
        # Unknown types sort last, then surface as a clear TypeError from
        # ``_gateway_for`` (rather than a bare KeyError from the sort key).
        last = len(self._order)
        rank = {record_type: i for i, record_type in enumerate(self._order)}

        upserts = self._new + self._dirty
        upserts.sort(key=lambda r: rank.get(type(r), last))
        deletes = sorted(
            self._removed, key=lambda r: rank.get(type(r), last), reverse=True
        )

        with self._connection.transaction():
            for record in upserts:
                self._gateway_for(record).upsert(record)
            for record in deletes:
                self._gateway_for(record).delete(record)

        self._new.clear()
        self._dirty.clear()
        self._removed.clear()

    def rollback(self) -> None:
        """Discard every staged change without touching the database."""
        self._new.clear()
        self._dirty.clear()
        self._removed.clear()

    # ---- internals ----

    def _gateway_for(self, record: object) -> TableDataGateway:
        try:
            return self._gateways[type(record)]
        except KeyError:
            raise TypeError(
                f"UnitOfWork has no gateway for record type {type(record).__name__!r}"
            ) from None
