"""The Synchronizer facade — the two operations the package exposes.

:meth:`Synchronizer.pull` projects the live model into SQL; :meth:`push` writes
SQL back into the model. There is no automatic conflict-merge — the direction is
always the caller's explicit choice — and each call returns a :class:`SyncReport`
tallying what changed.

* **pull** reads the model once (:class:`ModelReader`), then upserts every record
  through a :class:`UnitOfWork` in a single transaction; element rows present in
  the store but absent from the model are deleted (their satellites cascade).
  The whole write is atomic.
* **push** loads the stored snapshot, diffs it against the live model, and lets
  :class:`ModelWriter` reconstruct / update / delete elements. The model has no
  transaction, so this is best-effort under display suppression — the report
  records what was applied.
"""

from __future__ import annotations

from dataclasses import dataclass

from pycadwork.document import Document
from pycadwork.persistence._connection import GatewayConnection
from pycadwork.persistence._diff import diff
from pycadwork.persistence._ids import ProjectGuid
from pycadwork.persistence.gateways import (
    AttributeGateway,
    BuildingGateway,
    ContainerMemberGateway,
    CoverGateway,
    ElementGateway,
    GeometryGateway,
    ProjectGateway,
    StoreyAssignmentGateway,
    StoreyGateway,
    UserAttributeGateway,
)
from pycadwork.persistence.mappers import ModelReader, ModelWriter
from pycadwork.persistence.records import ElementRecord, ModelSnapshot, ProjectRecord
from pycadwork.persistence.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class SyncReport:
    """What one :meth:`Synchronizer.pull` / :meth:`push` changed, by element.

    Counts are element-level: ``created`` and ``deleted`` are elements added or
    removed on the receiving side, ``updated`` is elements present on both sides
    and re-written, ``skipped`` is target elements a ``push`` could not
    reconstruct (always 0 for a ``pull``).
    """

    created: int
    updated: int
    deleted: int
    skipped: int = 0


def load_snapshot(
    connection: GatewayConnection, project_guid: ProjectGuid
) -> ModelSnapshot:
    """Reassemble the stored :class:`ModelSnapshot` for ``project_guid`` from SQL.

    Each gateway contributes its table's rows for the project; a missing project
    row yields a default :class:`ProjectRecord` so the snapshot always has a
    project to anchor on.
    """
    projects = ProjectGateway(connection).select_for_project(project_guid)
    project = projects[0] if projects else ProjectRecord(project_guid)

    return ModelSnapshot(
        project=project,
        elements=tuple(ElementGateway(connection).select_for_project(project_guid)),
        attributes=tuple(AttributeGateway(connection).select_for_project(project_guid)),
        geometries=tuple(GeometryGateway(connection).select_for_project(project_guid)),
        user_attributes=tuple(
            UserAttributeGateway(connection).select_for_project(project_guid)
        ),
        covers=tuple(CoverGateway(connection).select_for_project(project_guid)),
        container_members=tuple(
            ContainerMemberGateway(connection).select_for_project(project_guid)
        ),
        buildings=tuple(BuildingGateway(connection).select_for_project(project_guid)),
        storeys=tuple(StoreyGateway(connection).select_for_project(project_guid)),
        storey_assignments=tuple(
            StoreyAssignmentGateway(connection).select_for_project(project_guid)
        ),
    )


class Synchronizer:
    """Bidirectional model ↔ SQL sync via two explicit operations."""

    __slots__ = ("_reader", "_writer")

    def __init__(
        self,
        reader: ModelReader | None = None,
        writer: ModelWriter | None = None,
    ) -> None:
        self._reader = reader or ModelReader()
        self._writer = writer or ModelWriter()

    def pull(self, connection: GatewayConnection) -> SyncReport:
        """Project the live model into ``connection``'s store (model → SQL).

        Idempotent: re-pulling an unchanged model upserts the same rows. Element
        rows for ids no longer in the model are deleted, cascading to their
        satellites. All writes commit in one transaction.
        """
        snapshot = self._reader.read()
        guid = snapshot.project.project_guid

        existing_ids = {
            e.id for e in ElementGateway(connection).select_for_project(guid)
        }
        model_ids = {e.id for e in snapshot.elements}
        removed_ids = existing_ids - model_ids

        unit = UnitOfWork(connection)
        for record in snapshot.all_records():
            unit.register_new(record)
        for removed_id in sorted(removed_ids):
            unit.register_removed(ElementRecord(guid, removed_id, ""))
        unit.commit()

        return SyncReport(
            created=len(model_ids - existing_ids),
            updated=len(model_ids & existing_ids),
            deleted=len(removed_ids),
        )

    def push(self, connection: GatewayConnection) -> SyncReport:
        """Write the stored snapshot back into the live model (SQL → model).

        The target is the snapshot stored for the active project's GUID; the
        current state is a fresh model read. The diff drives create / update /
        delete via :class:`ModelWriter` (itself display-suppressed).
        """
        guid = ProjectGuid(Document().guid)
        target = load_snapshot(connection, guid)
        current = self._reader.read()

        result = self._writer.apply(diff(current, target))

        return SyncReport(
            created=result.created,
            updated=result.updated,
            deleted=result.deleted,
            skipped=result.skipped,
        )
