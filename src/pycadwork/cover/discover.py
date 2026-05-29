"""Discover existing cover aggregates in the active cadwork model.

Mirrors the canonical scan-the-model loop: bucket elements by ``group`` or
``subgroup`` (whichever the active grouping mode says), then pick the
wall / floor / roof element in each bucket as the aggregate's parent and
wrap it via :func:`pycadwork.element.from_id` so it lands as a typed
``Wall`` / ``Slab`` / ``Roof``. Buckets without a wall/floor/roof element
are silently skipped — they aren't cover aggregates by definition. The
empty grouping key (unaffiliated elements) is also skipped.

All cwapi3d access goes through :data:`pycadwork.cadwork_adapter.cadwork`
to honour the version-isolation seam.
"""
from __future__ import annotations

from collections.abc import Iterable

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import GroupingMode
from pycadwork.cover.aggregate import Aggregate
from pycadwork.element.factory import from_id


def discover_covers(ids: Iterable[int] | None = None) -> list[Aggregate]:
    """Return one aggregate per grouping bucket that contains a cover parent.

    ``ids`` defaults to the active identifiable elements in the model.
    Pass an explicit iterable to scan a custom set.
    """
    grouping = cadwork.grouping
    attrs = cadwork.attributes
    elements = cadwork.elements

    mode = grouping.get_element_grouping_type()
    eids = list(ids) if ids is not None else elements.get_active_identifiable_element_ids()

    read_key = attrs.get_group if mode is GroupingMode.GROUP else attrs.get_subgroup

    buckets: dict[str, list[int]] = {}
    for eid in eids:
        key = read_key(eid)
        if not key:
            continue
        buckets.setdefault(key, []).append(eid)

    covers: list[Aggregate] = []
    for bucket_ids in buckets.values():
        parent_id = next(
            (
                eid
                for eid in bucket_ids
                if (snap := elements.get_element_type(eid))
                and (snap.is_wall or snap.is_floor or snap.is_roof)
            ),
            None,
        )
        if parent_id is None:
            continue
        wrapped = from_id(parent_id)
        if isinstance(wrapped, Aggregate):
            covers.append(wrapped)

    return covers
