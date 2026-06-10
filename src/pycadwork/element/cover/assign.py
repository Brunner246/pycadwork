"""CoverAssigner: attach loose elements to the cover they spatially sit in.

Given a set of loose elements and a set of covers (walls/floors/roofs), decide
which cover each element belongs to by bounding-box overlap and attach it via
the grouping link. A spatial index prunes the candidate covers per element
(broad phase); an exact OBB-OBB test confirms real overlap (narrow phase); when
several covers overlap, the one with the largest enclosing-AABB overlap wins.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class CoverAssignment:
    """An inspectable record of one element attached to a cover."""

    element: Element
    cover: Aggregate


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
    ) -> None:
        self._covers = None if covers is None else list(covers)
        self._tolerance = tolerance

    @suppressed_display
    def assign(self, elements: Iterable[Element]) -> list[CoverAssignment]:
        """Attach each loose element to its best-overlapping cover.

        Elements that are themselves covers/aggregates, and elements with no
        overlapping cover, are skipped. Returns one :class:`CoverAssignment`
        per attached element as a report.
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
        for element in elements:
            if isinstance(element, Aggregate):
                continue
            region = element.geometry.bounding_region

            best = self._best_cover(element, region, index, by_index)
            if best is None:
                continue
            best.add_child(element)
            results.append(CoverAssignment(element, best))

        return results

    # ---- internals ----

    def _best_cover(
        self,
        element: Element,
        region: BoundingRegion3D,
        index: RTreeIndex3D,
        by_index: dict[int, tuple[Aggregate, BoundingRegion3D]],
    ) -> Aggregate | None:
        element_obb = as_oriented(region)
        element_aabb = as_axis_aligned(region)
        query = region.expanded(self._tolerance) if self._tolerance > 0.0 else region

        best_cover: Aggregate | None = None
        best_overlap = -1.0
        for idx in index.intersection(query):
            cover, cover_region = by_index[idx]
            cover_obb = as_oriented(cover_region)
            if self._tolerance > 0.0:
                cover_obb = cover_obb.expanded(self._tolerance)
            if not cover_obb.intersects(element_obb):
                continue
            overlap = _aabb_overlap_volume(as_axis_aligned(cover_region), element_aabb)
            if overlap > best_overlap:
                best_overlap = overlap
                best_cover = cover
        return best_cover
