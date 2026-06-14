"""SnapshotIndex — per-element lookups over one snapshot, built once.

:class:`~pycadwork.persistence.records.ModelSnapshot` deliberately rebuilds its
``*_by_element()`` dicts on every call (the snapshot is immutable, so it caches
nothing). A report pass touches every element and consults several satellites
per element, so it needs those dicts exactly once — :class:`SnapshotIndex`
builds them up front and serves O(1) lookups for the rest of the pass.

The index also answers the one question the snapshot's own helpers do not:
which cover parent a grouping key belongs to. Cover membership in cadwork is a
shared ``group``/``subgroup`` value, and the snapshot stores both attribute
fields but not the project's active :class:`~pycadwork.cadwork_adapter.types.GroupingMode` —
so :meth:`cover_label_by_link_key` is parameterized by which field carries the
link.
"""

from __future__ import annotations

from pycadwork.persistence._ids import ElementId
from pycadwork.persistence.records import (
    AttributeRecord,
    GeometryRecord,
    ModelSnapshot,
    StoreyAssignmentRecord,
)

#: The attribute fields that may carry the cover-membership link.
COVER_LINKS = ("group", "subgroup")


class SnapshotIndex:
    """Per-element lookups over one :class:`ModelSnapshot`, built once (O(n))."""

    __slots__ = (
        "_attributes",
        "_geometries",
        "_assignments",
        "_snapshot",
        "_cover_labels",
    )

    def __init__(self, snapshot: ModelSnapshot) -> None:
        self._snapshot = snapshot
        self._attributes = snapshot.attributes_by_element()
        self._geometries = snapshot.geometry_by_element()
        self._assignments = snapshot.assignments_by_element()
        self._cover_labels: dict[str, dict[str, str]] = {}

    def attribute(self, element_id: ElementId) -> AttributeRecord | None:
        return self._attributes.get(element_id)

    def geometry(self, element_id: ElementId) -> GeometryRecord | None:
        return self._geometries.get(element_id)

    def assignment(self, element_id: ElementId) -> StoreyAssignmentRecord | None:
        return self._assignments.get(element_id)

    def cover_label_by_link_key(self, link: str = "group") -> dict[str, str]:
        """Map each cover's grouping key to a display label for its parent.

        ``link`` names the attribute field that carries the membership link —
        ``"group"`` or ``"subgroup"`` — mirroring the project setting the
        snapshot cannot store. The label is the parent's ``name``; an unnamed
        parent falls back to ``"<cover_kind>:<key>"``. Covers whose parent has
        no value in the link field are unreachable through that field and are
        omitted.
        """
        if link not in COVER_LINKS:
            raise ValueError(f"link must be one of {COVER_LINKS}, got {link!r}")
        cached = self._cover_labels.get(link)
        if cached is not None:
            return cached

        labels: dict[str, str] = {}
        for cover in self._snapshot.covers:
            attribute = self._attributes.get(cover.element_id)
            if attribute is None:
                continue
            key = attribute.group_name if link == "group" else attribute.subgroup
            if not key:
                continue
            labels[key] = attribute.name or f"{cover.cover_kind}:{key}"
        self._cover_labels[link] = labels
        return labels
