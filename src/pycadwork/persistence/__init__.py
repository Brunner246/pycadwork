"""pycadwork.persistence — map the running cadwork model to a SQL database.

A normalized (3NF) SQL mirror of the active document, written with the classic
Fowler PoEAA patterns: **Table Data Gateways** (one per table), a **Unit of
Work** that sequences writes in one transaction, frozen **Record** DTOs as the
lingua franca, and **Mappers** (``ModelReader`` / ``ModelWriter``) that are the
sole cadwork seam. The sync is bidirectional through two explicit operations —
:meth:`Synchronizer.pull` (model → SQL) and :meth:`~Synchronizer.push`
(SQL → model) — with no automatic conflict-merge.

The default backend is stdlib ``sqlite3`` behind the :class:`GatewayConnection`
Protocol (no new dependency); :func:`open_sqlite` opens a database and applies
the schema. The package never imports cwapi3d — it reads and writes the model
only through ``Document`` / ``Element`` and the adapter, honouring the project's
version-isolation rule.

Typical use::

    from pycadwork.persistence import Synchronizer, open_sqlite

    connection = open_sqlite("model.db")
    Synchronizer().pull(connection)   # snapshot the model into SQL
    ...
    Synchronizer().push(connection)   # rebuild a model from the snapshot
"""

from __future__ import annotations

from pycadwork.persistence._connection import (
    GatewayConnection,
    SqliteConnection,
    open_sqlite,
)
from pycadwork.persistence._diff import SnapshotDiff, diff
from pycadwork.persistence._ids import (
    CadworkGuid,
    ContainerId,
    ElementId,
    MemberId,
    ProjectGuid,
)
from pycadwork.persistence.mappers import ModelReader, ModelWriter, WriteResult
from pycadwork.persistence.query import BuildingQuery
from pycadwork.persistence.records import (
    AttributeRecord,
    BuildingRecord,
    ContainerMemberRecord,
    CoverRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
    UserAttributeRecord,
)
from pycadwork.persistence.sync import SyncReport, Synchronizer, load_snapshot
from pycadwork.persistence.unit_of_work import UnitOfWork

__all__ = [
    "AttributeRecord",
    "BuildingQuery",
    "BuildingRecord",
    "CadworkGuid",
    "ContainerId",
    "ContainerMemberRecord",
    "CoverRecord",
    "ElementId",
    "ElementRecord",
    "GatewayConnection",
    "GeometryRecord",
    "MemberId",
    "ModelReader",
    "ModelSnapshot",
    "ModelWriter",
    "ProjectGuid",
    "ProjectRecord",
    "SnapshotDiff",
    "SqliteConnection",
    "StoreyAssignmentRecord",
    "StoreyRecord",
    "SyncReport",
    "Synchronizer",
    "UnitOfWork",
    "UserAttributeRecord",
    "WriteResult",
    "diff",
    "load_snapshot",
    "open_sqlite",
]
