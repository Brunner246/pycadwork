"""CoverAssigner: attach loose elements to the cover they spatially sit in.

Given a set of loose elements and a set of covers (walls/floors/roofs), decide
which cover each element belongs to by bounding-box overlap and attach it via
the grouping link. A spatial index prunes the candidate covers per element
(broad phase); an exact OBB-OBB test confirms real overlap (narrow phase); when
several covers overlap, the one with the largest enclosing-AABB overlap wins.

The winner is always attached, but an assignment that **can't be made surely**
is **marked** in an indexed ``user_attribute`` (``mark_attribute_index`` /
``mark_value``) so a human can review it — mirroring how
:class:`pycadwork.building.StoreyAssigner` flags elements that straddle a storey
plane. An assignment is uncertain when the element overlaps more than one cover,
or when the winning cover only overlaps once the boxes are grown by ``tolerance``
(a grazing/soft match). Elements that overlap no cover at all are skipped.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element import Element
from pycadwork.element.cover.aggregate import Aggregate
from pycadwork.element.cover.discover import discover_covers
from pycadwork.geometry import (
    AxisAlignedBoundingBox,
    RTreeIndex3D,
)
from pycadwork.geometry.spatial_index import (
    BoundingRegion3D,
    as_axis_aligned,
    as_oriented,
)
from pycadwork.utility import suppressed_display

# Indexed user_attribute slot that carries the uncertain marker by default.
_DEFAULT_MARK_ATTRIBUTE_INDEX = 1


@dataclass(frozen=True, slots=True)
class CoverAssignment:
    """An inspectable record of one element attached to a cover.

    ``uncertain`` is ``True`` when the assignment couldn't be made surely — the
    element overlapped more than one cover, or the winning cover matched only
    after the boxes were grown by ``tolerance``.
    """

    element: Element
    cover: Aggregate
    uncertain: bool


def _aabb_overlap_volume(a: AxisAlignedBoundingBox, b: AxisAlignedBoundingBox) -> float:
    """Volume of the axis-aligned overlap of ``a`` and ``b`` (0 if disjoint)."""
    amin, amax = a.min_point, a.max_point
    bmin, bmax = b.min_point, b.max_point
    dx = max(0.0, min(amax.x, bmax.x) - max(amin.x, bmin.x))
    dy = max(0.0, min(amax.y, bmax.y) - max(amin.y, bmin.y))
    dz = max(0.0, min(amax.z, bmax.z) - max(amin.z, bmin.z))
    return dx * dy * dz


class CoverAssigner:
    """Attach loose elements to the overlapping cover, largest overlap wins."""

    def __init__(
        self,
        covers: Iterable[Aggregate] | None = None,
        *,
        tolerance: float = 0.0,
        mark_attribute_index: int = _DEFAULT_MARK_ATTRIBUTE_INDEX,
        mark_value: str = "uncertain-cover",
    ) -> None:
        self._covers = None if covers is None else list(covers)
        self._tolerance = tolerance
        self._mark_index = mark_attribute_index
        self._mark_value = mark_value

    @suppressed_display
    def assign(self, elements: Iterable[Element]) -> list[CoverAssignment]:
        """Attach each loose element to its best-overlapping cover.

        Elements that are themselves covers/aggregates, and elements with no
        overlapping cover, are skipped. Elements whose assignment is uncertain
        (overlapping several covers, or matched only within ``tolerance``) are
        marked in the configured ``user_attribute``. Returns one
        :class:`CoverAssignment` per attached element as a report.
        """
        covers = self._covers if self._covers is not None else discover_covers()

        by_index: dict[int, tuple[Aggregate, BoundingRegion3D]] = {}
        items: list[tuple[int, BoundingRegion3D]] = []
        for i, cover in enumerate(covers):
            region = cover.geometry.bounding_region
            by_index[i] = (cover, region)
            items.append((i, region))
        index = RTreeIndex3D(items)

        results: list[CoverAssignment] = []
        to_mark: list[ElementId] = []
        for element in elements:
            if isinstance(element, Aggregate):
                continue
            region = element.geometry.bounding_region

            best, uncertain = self._best_cover(element, region, index, by_index)
            if best is None:
                continue
            best.add_child(element)
            if uncertain:
                to_mark.append(element.id)
            results.append(CoverAssignment(element, best, uncertain))

        if to_mark:
            cadwork.attributes.set_user_attribute(
                to_mark, self._mark_index, self._mark_value
            )

        return results

    # ---- internals ----

    def _best_cover(
        self,
        element: Element,
        region: BoundingRegion3D,
        index: RTreeIndex3D,
        by_index: dict[int, tuple[Aggregate, BoundingRegion3D]],
    ) -> tuple[Aggregate | None, bool]:
        """Pick the best-overlapping cover and whether the pick is uncertain.

        Each candidate is tested at two levels: the tight (un-inflated) cover
        OBB, and the cover OBB grown by ``tolerance``. A cover overlaps when it
        passes the inflated test; the winner is a soft match when it passes only
        the inflated test, not the tight one. Returns ``(cover, uncertain)`` —
        uncertain when more than one cover overlapped, or the winner is a soft
        match. ``(None, False)`` when nothing overlaps.
        """
        element_obb = as_oriented(region)
        element_aabb = as_axis_aligned(region)
        query = region.expanded(self._tolerance) if self._tolerance > 0.0 else region

        best_cover: Aggregate | None = None
        best_overlap = -1.0
        best_is_tight = False
        overlapping = 0
        for idx in index.intersection(query):
            cover, cover_region = by_index[idx]
            cover_obb = as_oriented(cover_region)
            tight_hit = cover_obb.intersects(element_obb)
            inflated_hit = (
                cover_obb.expanded(self._tolerance).intersects(element_obb)
                if self._tolerance > 0.0
                else tight_hit
            )
            if not inflated_hit:
                continue
            overlapping += 1
            overlap = _aabb_overlap_volume(as_axis_aligned(cover_region), element_aabb)
            if overlap > best_overlap:
                best_overlap = overlap
                best_cover = cover
                best_is_tight = tight_hit
        if best_cover is None:
            return None, False
        return best_cover, (overlapping > 1 or not best_is_tight)
