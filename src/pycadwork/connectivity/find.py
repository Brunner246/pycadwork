"""Find the elements that connect (touch or intersect) a given element."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.connectivity.detection import (
    DEFAULT_TOLERANCE,
    active_elements,
    connects as geometric_connects,
)
from pycadwork.element import Element
from pycadwork.geometry import RTreeIndex3D

Predicate = Callable[[Element, Element], bool]


def find_connected(
    element: Element,
    *,
    among: Iterable[Element] | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
    connects: Predicate | None = None,  # noqa: A002 — deliberate public name
) -> list[Element]:
    """Return every element that touches or intersects ``element``.

    ``among`` is the set to search within; it defaults to the active
    identifiable elements in the model. ``element`` itself is never returned.

    By default contact is decided geometrically (tightest bounding region,
    grown by ``tolerance``) accelerated by a spatial index. Pass ``connects``
    to supply your own ``(a, b) -> bool`` predicate — ``tolerance`` is then
    ignored and every candidate is tested directly.
    """
    candidates = list(among) if among is not None else active_elements()
    others = [e for e in candidates if e != element]

    if connects is not None:
        return [other for other in others if connects(element, other)]

    return _find_geometric(element, others, tolerance)


def _find_geometric(
    element: Element, others: list[Element], tolerance: float
) -> list[Element]:
    by_id = {other.id: other for other in others}
    index = RTreeIndex3D((other.id, other.geometry.aabb) for other in others)

    query = element.geometry.aabb.expanded(tolerance)
    # The spatial index speaks raw ints; re-tag them as element ids on the way out.
    candidates = [ElementId(cand_id) for cand_id in index.intersection(query)]
    return [
        by_id[cand_id]
        for cand_id in candidates
        if geometric_connects(element, by_id[cand_id], tolerance)
    ]
