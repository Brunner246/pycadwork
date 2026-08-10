"""Discover existing cover aggregates in the active cadwork model.

A cover is any element cadwork has flagged as a wall, floor, or roof, so
discovery is a plain filter over the scanned ids: keep the ones whose type
snapshot reports ``is_wall`` / ``is_floor`` / ``is_roof`` and wrap each via
:func:`pycadwork.element.from_id` so it lands as a typed ``Wall`` / ``Slab`` /
``Roof``. Each cover's children stay a live view through
:attr:`pycadwork.element.cover.Aggregate.children` — discovery only finds the
parents, it does not assemble groups. (Assembling loose elements into covers is
the job of :class:`pycadwork.element.cover.CoverBuilder`.)

All cwapi3d access goes through :data:`pycadwork.cadwork_adapter.cadwork` to
honour the version-isolation seam.
"""

from __future__ import annotations

from collections.abc import Iterable

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element.cover.aggregate import Aggregate
from pycadwork.element.factory import from_id


def discover_covers(ids: Iterable[int] | None = None) -> list[Aggregate]:
    """Return every model element flagged as a cover (wall/floor/roof), typed.

    ``ids`` defaults to the active identifiable elements; pass an iterable to
    scan a custom subset. Each cover's children stay a live view via
    ``Aggregate.children`` — discovery only finds the parents.
    """
    elements = cadwork.elements
    eids: Iterable[ElementId] = (
        [ElementId(i) for i in ids]
        if ids is not None
        else elements.get_active_identifiable_element_ids()
    )

    covers: list[Aggregate] = []
    for eid in eids:
        snap = elements.get_element_type(eid)
        if not (snap.is_wall or snap.is_floor or snap.is_roof):
            continue
        wrapped = from_id(eid)
        if isinstance(wrapped, Aggregate):
            covers.append(wrapped)
    return covers
