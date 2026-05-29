from __future__ import annotations

from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D


class Line3D:
    """An infinite line in 3D space defined by a point and a unit direction.

    Construct via the static factory methods; the constructor is private.
    """

    __slots__ = ("_point", "_direction")

    # Private constructor ------------------------------------------------

    def __init__(self, point: Point3D, direction: Vector3D) -> None:
        self._point = point
        self._direction = direction

    # ------------------------------------------------------------------
    # Static factory methods
    # ------------------------------------------------------------------

    @staticmethod
    def from_point_and_direction(point: Point3D, direction: Vector3D) -> Line3D:
        if direction.is_zero():
            raise ValueError("Cannot create Line3D from zero-length direction")
        return Line3D(point, direction.normalized())

    @staticmethod
    def from_two_points(p1: Point3D, p2: Point3D) -> Line3D:
        displacement = Vector3D.from_two_points(p1, p2)
        if displacement.is_zero():
            raise ValueError("Cannot create Line3D from coincident points")
        return Line3D(p1, displacement.normalized())

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def point(self) -> Point3D:
        return self._point

    @property
    def direction(self) -> Vector3D:
        return self._direction

    # ------------------------------------------------------------------
    # Parametric evaluation
    # ------------------------------------------------------------------

    def point_at(self, t: float) -> Point3D:
        return Point3D(
            self._point.x + t * self._direction.x,
            self._point.y + t * self._direction.y,
            self._point.z + t * self._direction.z,
        )

    def parameter_at(self, query: Point3D) -> float:
        offset = query - self._point  # Vector3D
        return self._direction.dot(offset)

    # ------------------------------------------------------------------
    # Projection / closest point
    # ------------------------------------------------------------------

    def project_point(self, query: Point3D) -> Point3D:
        return self.point_at(self.parameter_at(query))

    def closest_point(self, query: Point3D) -> Point3D:
        return self.project_point(query)

    # ------------------------------------------------------------------
    # Distance
    # ------------------------------------------------------------------

    def distance_to_point(self, query: Point3D) -> float:
        return query.distance_to(self.project_point(query))

    def distance_squared_to_point(self, query: Point3D) -> float:
        return query.distance_squared_to(self.project_point(query))

    # ------------------------------------------------------------------
    # Containment
    # ------------------------------------------------------------------

    def contains(self, query: Point3D, tolerance: float = 1e-10) -> bool:
        return self.distance_to_point(query) < tolerance

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Line3D):
            return NotImplemented
        if not other.contains(self._point):
            return False
        cross = self._direction.cross(other._direction)
        return cross.is_zero()

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Line3D(point={self._point}, direction={self._direction})"

    def __str__(self) -> str:
        return self.__repr__()
