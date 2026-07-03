"""Content-fingerprint reconciliation for smart branch switching.

Pure module — no cadwork, no git — so it is unit-testable directly against
hand-built :class:`~pycadwork.persistence.records.ModelSnapshot` objects. It
answers one question: given what is currently live and what a target version
looks like, which live elements can be left completely alone, which are stale
and must go, and what target content is missing and must be brought in.

Because ``file_controller.import_3dc_file`` is additive-only and always mints
fresh ids **and** fresh cadwork GUIDs for everything it imports, identity
cannot survive a reimport. So pairing is done by **content fingerprint**
instead — never by id or GUID. A fingerprint carries no identity fields at
all (not ``id``, not ``cadwork_guid``, not ``parent_container_id``), only real
content: element type plus every field of the attribute / geometry / user
attribute / cover / storey-assignment satellites, plus the linked material
name. Geometry floats are quantized the same way :class:`~pycadwork.versioning._codec.SnapshotCodec`
quantizes them for JSONL, so cross-environment ULP drift between an unquantized
live read and a quantized on-disk target never registers as a spurious change.

A **container's** fingerprint additionally folds in the sorted multiset of its
members' own fingerprints, so container identity is content-only too — a
design that tried to translate ``parent_container_id`` into the container's
GUID breaks, because a freshly-reimported container's GUID never matches the
target's recorded one. The consequence, documented as an explicit limitation:
a container is atomic for change detection — if the container or any one
member changes, the whole group is treated as one changed unit and
re-brought-in together (see docs/versioning.md).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from pycadwork.persistence._ids import ElementId
from pycadwork.persistence.records import (
    AttributeRecord,
    CoverRecord,
    GeometryRecord,
    ModelSnapshot,
    StoreyAssignmentRecord,
    UserAttributeRecord,
)
from pycadwork.versioning._codec import FLOAT_SIGNIFICANT_DIGITS, _quantize

#: A hashable, content-only signature for one element (or one container plus
#: its members' own fingerprints).
ElementFingerprint = tuple[Any, ...]


def _attribute_fields(record: AttributeRecord | None) -> tuple[Any, ...]:
    if record is None:
        return ()
    return (
        record.name,
        record.group_name,
        record.subgroup,
        record.comment,
        record.material_name,
        record.sku,
        record.production_number,
        record.part_number,
        record.assembly_number,
    )


def _geometry_fields(record: GeometryRecord | None) -> tuple[Any, ...]:
    if record is None:
        return ()
    raw = (
        record.p1x,
        record.p1y,
        record.p1z,
        record.p2x,
        record.p2y,
        record.p2z,
        record.p3x,
        record.p3y,
        record.p3z,
        record.length,
        record.width,
        record.height,
        record.volume,
        record.weight,
        record.cog_x,
        record.cog_y,
        record.cog_z,
        record.aabb_min_x,
        record.aabb_min_y,
        record.aabb_min_z,
        record.aabb_max_x,
        record.aabb_max_y,
        record.aabb_max_z,
    )
    return tuple(_quantize(v, FLOAT_SIGNIFICANT_DIGITS) for v in raw)


def _cover_fields(record: CoverRecord | None) -> tuple[Any, ...]:
    return () if record is None else (record.cover_kind,)


def _assignment_fields(record: StoreyAssignmentRecord | None) -> tuple[Any, ...]:
    if record is None:
        return ()
    return (record.building_name, record.storey_name, record.spans)


def _user_attribute_fields(records: list[UserAttributeRecord]) -> tuple[Any, ...]:
    return tuple(sorted((r.attr_index, r.value) for r in records))


def fingerprint_snapshot(
    snapshot: ModelSnapshot,
) -> dict[ElementId, ElementFingerprint]:
    """Every element's content-only fingerprint.

    A container's fingerprint additionally folds in the sorted multiset of its
    members' own fingerprints (see the module docstring for why).
    """
    attrs_by = snapshot.attributes_by_element()
    geom_by = snapshot.geometry_by_element()
    covers_by = snapshot.covers_by_element()
    assignments_by = snapshot.assignments_by_element()
    uattrs_by = snapshot.user_attributes_by_element()
    materials_by = snapshot.element_materials_by_element()
    members_by_container = snapshot.members_by_container()

    fingerprints: dict[ElementId, ElementFingerprint] = {}
    for element in snapshot.elements:
        eid = element.id
        material = materials_by.get(eid)
        fingerprints[eid] = (
            element.element_type,
            _attribute_fields(attrs_by.get(eid)),
            _geometry_fields(geom_by.get(eid)),
            _user_attribute_fields(uattrs_by.get(eid, [])),
            _cover_fields(covers_by.get(eid)),
            _assignment_fields(assignments_by.get(eid)),
            material.material_name if material is not None else "",
        )

    for container_id, member_ids in members_by_container.items():
        base = fingerprints.get(container_id)
        if base is None:
            continue
        member_fps = tuple(
            sorted(fingerprints[m] for m in member_ids if m in fingerprints)
        )
        fingerprints[container_id] = (*base, member_fps)

    return fingerprints


@dataclass(frozen=True, slots=True)
class SyncPlan:
    """The classification of a live/target comparison, ready to execute.

    ``unchanged`` current ids are left completely untouched (same id, same
    GUID). ``stale`` current ids no longer match anything in the target and
    must be deleted. ``missing`` target fingerprints have no live counterpart
    and must be brought in — by importing the target binary and filtering out
    the resulting duplicates of anything unchanged (see
    :meth:`pycadwork.document.Document.apply_sync`).
    """

    unchanged: tuple[ElementId, ...]
    stale: tuple[ElementId, ...]
    missing: tuple[ElementFingerprint, ...]


def classify(current: ModelSnapshot, target: ModelSnapshot) -> SyncPlan:
    """Pair current elements against the target: GUID fast path, then fingerprint.

    An element with the same ``cadwork_guid`` in both snapshots *and* a
    matching fingerprint is unchanged — the common "edited normally, never
    reimported" case. Everything left unpaired falls back to multiset
    fingerprint matching (``collections.Counter``), which also resolves
    duplicates and elements whose GUID history was itself broken by an
    earlier smart-switch.

    A container's folded fingerprint (see :func:`fingerprint_snapshot`)
    guarantees it differs whenever any of its members differ, so a changed
    container is always independently detected. But the reverse pass matters
    too: once a container is classified as changed, every one of its *current*
    members is swept into ``stale`` as well — even one whose own content is
    byte-identical — because :meth:`pycadwork.document.Document.apply_sync`
    cannot surgically graft one preserved member into a freshly re-imported
    container; keeping it alone would orphan it from the new container
    instance. This is the documented container-atomicity limitation.
    """
    current_fps = fingerprint_snapshot(current)
    target_fps = fingerprint_snapshot(target)

    current_guid_by_id = {e.id: e.cadwork_guid for e in current.elements}
    target_guid_by_id = {e.id: e.cadwork_guid for e in target.elements}
    target_fp_by_guid = {
        target_guid_by_id[eid]: fp
        for eid, fp in target_fps.items()
        if target_guid_by_id.get(eid)
    }

    unchanged: set[ElementId] = set()
    unmatched_current: list[ElementId] = []
    matched_target_fps: list[ElementFingerprint] = []

    for eid in sorted(current_fps):
        fp = current_fps[eid]
        guid = current_guid_by_id.get(eid)
        if guid and target_fp_by_guid.get(guid) == fp:
            unchanged.add(eid)
            matched_target_fps.append(fp)
        else:
            unmatched_current.append(eid)

    remaining_target: Counter[ElementFingerprint] = Counter(target_fps.values())
    remaining_target.subtract(matched_target_fps)

    stale: set[ElementId] = set()
    for eid in unmatched_current:
        fp = current_fps[eid]
        if remaining_target.get(fp, 0) > 0:
            remaining_target[fp] -= 1
            unchanged.add(eid)  # fallback-paired: still left alone, no churn
        else:
            stale.add(eid)

    # Container atomicity: sweep every current member of a stale container into
    # stale too, even an individually-unchanged one — repeat to a fixed point
    # so nested containers (a container that is itself a member) cascade.
    extra_missing: list[ElementFingerprint] = []
    members_by_container = current.members_by_container()
    swept = True
    while swept:
        swept = False
        for container_id, member_ids in members_by_container.items():
            if container_id not in stale:
                continue
            for member_id in member_ids:
                if member_id in unchanged:
                    unchanged.discard(member_id)
                    stale.add(member_id)
                    extra_missing.append(current_fps[member_id])
                    swept = True

    missing = tuple(
        fp for fp, count in remaining_target.items() for _ in range(max(count, 0))
    ) + tuple(extra_missing)

    return SyncPlan(
        unchanged=tuple(sorted(unchanged)),
        stale=tuple(sorted(stale)),
        missing=missing,
    )
