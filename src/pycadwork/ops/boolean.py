"""Boolean solids and cutting operations with intention-revealing names.

cwapi3d calls these ``solder`` and ``subtract`` and orders the subtract
arguments cutters-first (``hard`` = the elements that do the cutting,
``soft`` = the elements being cut). Here the names say what happens to the
model — :func:`union`, :func:`difference` — and every (targets, cutters)
pair reads left-to-right as ``targets − cutters``; the flip to cwapi3d's
order happens in this layer, the adapter keeps the raw vocabulary.
"""

from __future__ import annotations

from collections.abc import Iterable

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.factory import from_id
from pycadwork.geometry.plane3d import Plane3D
from pycadwork.ops._common import _as_elements, _ids


def union(*elements: Element) -> list[Element]:
    """Solder ``elements`` into as few solids as their geometry allows.

    Returns the surviving elements — several when the inputs don't all
    touch each other.
    """
    if len(elements) < 2:
        raise ValueError("union() needs at least two elements")
    merged = cadwork.operations.solder_elements(_ids(elements))
    return [from_id(eid) for eid in merged]


def difference(
    targets: Element | Iterable[Element],
    cutters: Element | Iterable[Element],
    *,
    undo: bool = False,
) -> list[Element]:
    """``targets − cutters``: subtract the cutters' volume from the targets.

    Targets are cut in place and keep their ids. The returned list contains
    only the split-off pieces created when a target falls apart into
    disconnected solids — usually empty. With ``undo=True`` the operation is
    added to cadwork's undo stack.
    """
    target_ids = _ids(_as_elements(targets))
    cutter_ids = _ids(_as_elements(cutters))
    if undo:
        pieces = cadwork.operations.subtract_elements_with_undo(
            cutter_ids, target_ids, True
        )
    else:
        pieces = cadwork.operations.subtract_elements(cutter_ids, target_ids)
    return [from_id(eid) for eid in pieces]


def split(elements: Element | Iterable[Element]) -> None:
    """Split ``elements`` along their internal cut surfaces."""
    cadwork.operations.split_elements(_ids(_as_elements(elements)))


def cut_with_plane(element: Element, plane: Plane3D) -> bool:
    """Cut ``element`` with an infinite plane, keeping both halves.

    Returns ``False`` when the plane misses the element — a normal outcome,
    not an error.
    """
    return cadwork.operations.cut_element_with_plane(element.id, plane)


def slice_with_plane(element: Element, plane: Plane3D) -> list[Element]:
    """Slice ``element`` with an infinite plane and return the new pieces.

    An empty list means the plane missed the element.
    """
    new_ids = cadwork.operations.slice_element_with_plane_get_new(element.id, plane)
    return [from_id(eid) for eid in new_ids]


def cut_with_miter(first: Element, second: Element) -> bool:
    """Join two elements with a miter cut; ``False`` when the cut fails."""
    return cadwork.operations.cut_elements_with_miter(first.id, second.id)


def cut_with_overmeasure(
    targets: Element | Iterable[Element],
    cutters: Element | Iterable[Element],
) -> None:
    """Cut ``targets`` with ``cutters``, leaving cadwork's overmeasure."""
    target_ids = _ids(_as_elements(targets))
    cutter_ids = _ids(_as_elements(cutters))
    cadwork.operations.cut_elements_with_overmeasure(cutter_ids, target_ids)


def cut_cross_lap(
    elements: Element | Iterable[Element],
    *,
    depth: float,
    clearance_base: float = 0.0,
    clearance_side: float = 0.0,
    drilling_count: int = 0,
    drilling_diameter: float = 0.0,
    drilling_tolerance: float = 0.0,
) -> None:
    """Cut a housed cross-lap between the crossing ``elements``.

    cadwork computes the interlocking half-depth housings from where the
    elements cross; ``depth`` is the housing depth (typically half the member
    height). When ``drilling_count`` is positive, that many fastener holes are
    drilled through the joint.
    """
    cadwork.operations.cut_cross_lap(
        _ids(_as_elements(elements)),
        depth,
        clearance_base,
        clearance_side,
        drilling_count,
        drilling_diameter,
        drilling_tolerance,
    )


def cut_with_processing_group(target: Element, processing: Element) -> None:
    """Cut ``target`` with the processing group ``processing``."""
    cadwork.operations.cut_element_with_processing_group(target.id, processing.id)
