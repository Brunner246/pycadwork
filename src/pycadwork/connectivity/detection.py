"""The default geometric contact predicate and model-scan helper.

Two elements *connect* when their solids touch or overlap. We approximate
each solid by its tightest available bounding region — the oriented box
(OBB) for axis-anchored elements (beams, plates, drillings, ...), or the
world-aligned box lifted into OBB form for everything else (nodes,
surfaces, bare elements) — and test those for intersection via the OBB
separating-axis theorem. A ``tolerance`` grows one region before the test,
so flush-touching faces register despite float error and callers can widen
it to catch small designed gaps (e.g. ``tolerance=2.0`` for ~2 mm).

All cwapi3d access goes through :data:`pycadwork.cadwork_adapter.cadwork`
to honour the version-isolation seam.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element import Element, LinearElement, from_id
from pycadwork.geometry import OrientedBoundingBox

#: Default contact tolerance. Small enough to mean "touching or overlapping"
#: while absorbing floating-point error; widen it to treat near-misses as
#: connections.
DEFAULT_TOLERANCE = 1e-6


def _region_of(element: Element) -> OrientedBoundingBox:
    """Return the element's tightest bounding region as an OBB.

    Axis-anchored elements (``LinearElement`` and its ``OrientedElement``
    subclasses) carry a tight, frame-aligned OBB. Everything else only
    exposes an AABB, which we lift into OBB form so a single SAT test
    handles both.
    """
    if isinstance(element, LinearElement):
        return element.geometry.obb
    return OrientedBoundingBox.from_axis_aligned(element.geometry.aabb)


def connects(a: Element, b: Element, tolerance: float = DEFAULT_TOLERANCE) -> bool:
    """True if ``a`` and ``b`` touch or overlap within ``tolerance``.

    The default contact predicate used by :func:`find_connected` and
    :func:`build_connection_graph`. Symmetric; a region grown by
    ``tolerance`` intersecting the other means the gap between them is at
    most ``tolerance``.
    """
    return _region_of(a).expanded(tolerance).intersects(_region_of(b))


def active_elements() -> list[Element]:
    """Wrap every active identifiable element in the model as an ``Element``.

    Mirrors the scan-the-model idiom of :func:`pycadwork.discover_covers`.
    """
    eids = cadwork.elements.get_active_identifiable_element_ids()
    return [from_id(eid) for eid in eids]
