from __future__ import annotations

from collections.abc import Iterable

from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D


class AxisAlignedBoundingBox:
    """An axis-aligned bounding box in 3D space.

    Built from an iterable of :class:`Point3D` -- typically the 8 vertices of
    a CAD element's oriented bounding box -- by taking the per-axis minima
    and maxima. A single point yields a zero-volume AABB (still a valid
    region for point-in-region queries).
    """

    __slots__ = ("_min", "_max")

    def __init__(self, points: Iterable[Point3D]) -> None:
        iterator = iter(points)
        try:
            first = next(iterator)
        except StopIteration as exc:
            raise ValueError(
                "AxisAlignedBoundingBox requires at least one point"
            ) from exc

        xmin = xmax = first.x
        ymin = ymax = first.y
        zmin = zmax = first.z
        for p in iterator:
            if p.x < xmin:
                xmin = p.x
            elif p.x > xmax:
                xmax = p.x
            if p.y < ymin:
                ymin = p.y
            elif p.y > ymax:
                ymax = p.y
            if p.z < zmin:
                zmin = p.z
            elif p.z > zmax:
                zmax = p.z

        self._min = Point3D(xmin, ymin, zmin)
        self._max = Point3D(xmax, ymax, zmax)

    # ------------------------------------------------------------------
    # Static factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def from_min_max(min_point: Point3D, max_point: Point3D) -> AxisAlignedBoundingBox:
        """Build an AABB directly from pre-computed extremes.

        Raises:
            ValueError: if any component of ``min_point`` exceeds the
                corresponding component of ``max_point``.
        """
        if (
            min_point.x > max_point.x
            or min_point.y > max_point.y
            or min_point.z > max_point.z
        ):
            raise ValueError(
                "from_min_max: min_point must be <= max_point on every axis"
            )

        return AxisAlignedBoundingBox._from_points(min_point, max_point)

    @classmethod
    def _from_points(
        cls, min_point: Point3D, max_point: Point3D
    ) -> AxisAlignedBoundingBox:
        box = cls.__new__(cls)
        box._min = Point3D(min_point.x, min_point.y, min_point.z)
        box._max = Point3D(max_point.x, max_point.y, max_point.z)
        return box

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def min_point(self) -> Point3D:
        return Point3D(self._min.x, self._min.y, self._min.z)

    @property
    def max_point(self) -> Point3D:
        return Point3D(self._max.x, self._max.y, self._max.z)

    @property
    def center(self) -> Point3D:
        return Point3D(
            0.5 * (self._min.x + self._max.x),
            0.5 * (self._min.y + self._max.y),
            0.5 * (self._min.z + self._max.z),
        )

    @property
    def size(self) -> Vector3D:
        return Vector3D(
            self._max.x - self._min.x,
            self._max.y - self._min.y,
            self._max.z - self._min.z,
        )

    def is_empty(self) -> bool:
        """True if the box has no volume on at least one axis."""
        return (
            self._min.x >= self._max.x
            or self._min.y >= self._max.y
            or self._min.z >= self._max.z
        )

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def contains_point(self, p: Point3D) -> bool:
        return (
            self._min.x <= p.x <= self._max.x
            and self._min.y <= p.y <= self._max.y
            and self._min.z <= p.z <= self._max.z
        )

    def intersects(self, other: AxisAlignedBoundingBox) -> bool:
        return not (
            self._max.x < other._min.x
            or self._min.x > other._max.x
            or self._max.y < other._min.y
            or self._min.y > other._max.y
            or self._max.z < other._min.z
            or self._min.z > other._max.z
        )

    def union(self, other: AxisAlignedBoundingBox) -> AxisAlignedBoundingBox:
        return AxisAlignedBoundingBox.from_min_max(
            Point3D(
                min(self._min.x, other._min.x),
                min(self._min.y, other._min.y),
                min(self._min.z, other._min.z),
            ),
            Point3D(
                max(self._max.x, other._max.x),
                max(self._max.y, other._max.y),
                max(self._max.z, other._max.z),
            ),
        )

    def expanded(self, margin: float) -> AxisAlignedBoundingBox:
        """Return a copy grown by ``margin`` on every axis (each face moves out).

        Useful as a tolerance for contact/proximity queries: two boxes are
        within ``margin`` of touching iff one grown by ``margin`` intersects
        the other.

        Raises:
            ValueError: if ``margin`` is negative.
        """
        if margin < 0.0:
            raise ValueError("expanded: margin must be non-negative")

        return AxisAlignedBoundingBox._from_points(
            Point3D(self._min.x - margin, self._min.y - margin, self._min.z - margin),
            Point3D(self._max.x + margin, self._max.y + margin, self._max.z + margin),
        )

    # ------------------------------------------------------------------
    # Library interop
    # ------------------------------------------------------------------

    def as_coordinates(self) -> tuple[float, float, float, float, float, float]:
        """Return the box as ``(xmin, ymin, zmin, xmax, ymax, zmax)``.

        This is the ordering expected by the ``rtree`` library for 3D
        indices; exposing it here keeps the coordinate format out of the
        index wrapper.
        """
        return (
            self._min.x,
            self._min.y,
            self._min.z,
            self._max.x,
            self._max.y,
            self._max.z,
        )

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AxisAlignedBoundingBox):
            return NotImplemented
        return self._min == other._min and self._max == other._max

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"AxisAlignedBoundingBox(min={self._min}, max={self._max})"

    def __str__(self) -> str:
        return self.__repr__()
