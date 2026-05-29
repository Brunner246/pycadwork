"""3D spatial indexing for CAD elements.

Two thin protocols describe the contract that consumers should program
against:

* :class:`SpatialQuery3D` -- read-only operations (`intersection`, `nearest`,
  ``len``). Dependencies that only inspect a prebuilt index should accept
  this narrower protocol.
* :class:`SpatialIndex3D` -- adds mutation (`insert`, `remove`, `clear`).

Bounding regions may be either :class:`AxisAlignedBoundingBox` or
:class:`OrientedBoundingBox`. OBBs are reduced to their enclosing AABB
before reaching the backend, so OBB-shaped queries are broad-phase only
and may return a superset of the elements an exact OBB-OBB test would
return.

The concrete :class:`RTreeIndex3D` wraps the ``rtree`` Python binding around
``libspatialindex`` configured for 3D. Swapping in a different backend
(kd-tree, uniform grid, ...) is a matter of implementing the same protocol.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol, runtime_checkable

from rtree import index as _rtree_index

from pycadwork.geometry.aabb import AxisAlignedBoundingBox
from pycadwork.geometry.obb import OrientedBoundingBox
from pycadwork.geometry.point3d import Point3D

BoundingRegion3D = AxisAlignedBoundingBox | OrientedBoundingBox


def _to_aabb(region: BoundingRegion3D) -> AxisAlignedBoundingBox:
    if isinstance(region, AxisAlignedBoundingBox):
        return region
    return region.to_axis_aligned_bounding_box()


@runtime_checkable
class SpatialQuery3D(Protocol):
    """Read-only view of a 3D spatial index."""

    def __len__(self) -> int: ...

    def intersection(
        self, region: BoundingRegion3D
    ) -> Iterator[int]: ...

    def nearest(self, point: Point3D, k: int = 1) -> Iterator[int]: ...


@runtime_checkable
class SpatialIndex3D(SpatialQuery3D, Protocol):
    """Mutable 3D spatial index."""

    def insert(self, element_id: int, bounds: BoundingRegion3D) -> None: ...

    def remove(self, element_id: int, bounds: BoundingRegion3D) -> None: ...

    def clear(self) -> None: ...


def _build_index() -> _rtree_index.Index:
    props = _rtree_index.Property()
    props.dimension = 3
    return _rtree_index.Index(properties=props)


class RTreeIndex3D:
    """R-tree-backed implementation of :class:`SpatialIndex3D`.

    Uses ``libspatialindex`` (via the ``rtree`` Python binding) configured
    for 3D. Element ids must be ``int`` -- this matches cadwork element
    ids and the native id space of the underlying library.
    """

    __slots__ = ("_index", "_count")

    def __init__(
        self,
        items: Iterable[tuple[int, BoundingRegion3D]] = (),
    ) -> None:
        self._index: _rtree_index.Index = _build_index()
        self._count: int = 0
        for element_id, bounds in items:
            self.insert(element_id, bounds)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def insert(self, element_id: int, bounds: BoundingRegion3D) -> None:
        self._index.insert(element_id, _to_aabb(bounds).as_coordinates())
        self._count += 1

    def remove(self, element_id: int, bounds: BoundingRegion3D) -> None:
        """Remove the entry identified by ``element_id`` covering ``bounds``.

        ``libspatialindex`` requires the rectangle to locate the entry.
        Pass the same bounds that were used when inserting -- for OBB
        entries the enclosing AABB must match, so pass the same OBB.
        """
        self._index.delete(element_id, _to_aabb(bounds).as_coordinates())
        self._count -= 1

    def clear(self) -> None:
        self._index = _build_index()
        self._count = 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return self._count

    def intersection(self, region: BoundingRegion3D) -> Iterator[int]:
        return iter(self._index.intersection(_to_aabb(region).as_coordinates()))

    def nearest(self, point: Point3D, k: int = 1) -> Iterator[int]:
        if k < 1:
            raise ValueError("nearest: k must be >= 1")
        query = (point.x, point.y, point.z, point.x, point.y, point.z)
        return iter(self._index.nearest(query, num_results=k))

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"RTreeIndex3D({self._count} entries)"

    def __str__(self) -> str:
        return self.__repr__()
