"""Pure snapshot diff — classify elements as new, dirty, or removed.

:func:`diff` compares a ``current`` snapshot against a ``target`` snapshot,
keyed by element id, and reports which elements appear only in the target (to
*create*), in both (to *update*), or only in the current model (to *remove*).
It does no I/O and touches neither cadwork nor SQL, so it is trivially
unit-testable in isolation.

Direction is the caller's to assign by choosing the arguments. For a ``push``,
``current`` is the live model and ``target`` is the desired state loaded from
SQL: new ⇒ create, dirty ⇒ update, removed ⇒ delete. The satellite records
(attributes, geometry, container links, …) ride along on the ``target``
snapshot, which the diff carries through unchanged for the writer to consult.
"""

from __future__ import annotations

from dataclasses import dataclass

from pycadwork.persistence._ids import ElementId
from pycadwork.persistence.records import ElementRecord, ModelSnapshot


@dataclass(frozen=True, slots=True)
class SnapshotDiff:
    """The element-level classification of two snapshots, plus the target.

    ``new_ids`` and ``dirty_ids`` are stored element ids drawn from ``target``;
    ``removed`` are the full element records from ``current`` that the target no
    longer contains (the writer needs only their ids, but carrying the record
    keeps the type honest). ``target`` is the whole desired snapshot, so the
    writer can reach every satellite record it must apply.
    """

    target: ModelSnapshot
    new_ids: tuple[ElementId, ...]
    dirty_ids: tuple[ElementId, ...]
    removed: tuple[ElementRecord, ...]


def diff(current: ModelSnapshot, target: ModelSnapshot) -> SnapshotDiff:
    """Classify ``target``'s elements against ``current``, keyed by element id.

    * **new** — in ``target`` but not ``current``
    * **dirty** — in both
    * **removed** — in ``current`` but not ``target``

    Ids are returned sorted so the result is deterministic regardless of the
    snapshots' internal ordering.
    """
    current_ids = {e.id: e for e in current.elements}
    target_ids = {e.id for e in target.elements}

    new_ids = tuple(sorted(i for i in target_ids if i not in current_ids))
    dirty_ids = tuple(sorted(i for i in target_ids if i in current_ids))
    removed = tuple(current_ids[i] for i in sorted(current_ids) if i not in target_ids)
    return SnapshotDiff(target, new_ids, dirty_ids, removed)
