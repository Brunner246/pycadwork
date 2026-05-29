from __future__ import annotations

from pycadwork.geometry.line3d import Line3D
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D


class Segment3D:
    """A bounded line segment in 3D space defined by two endpoints.

    Construct via the static factory methods; the constructor is private.
    """

    __slots__ = ("_p1", "_p2")

    # Private constructor ------------------------------------------------

    def __init__(self, p1: Point3D, p2: Point3D) -> None:
        self._p1 = p1
        self._p2 = p2

    # ------------------------------------------------------------------
    # Static factory methods
    # ------------------------------------------------------------------

    @staticmethod
    def from_two_points(p1: Point3D, p2: Point3D) -> Segment3D:
        if Vector3D.from_two_points(p1, p2).is_zero():
            raise ValueError("Cannot create Segment3D from coincident points")
        return Segment3D(p1, p2)

    @staticmethod
    def from_point_and_vector(start: Point3D, displacement: Vector3D) -> Segment3D:
        if displacement.is_zero():
            raise ValueError("Cannot create Segment3D from zero displacement")
        return Segment3D(start, start + displacement)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def p1(self) -> Point3D:
        return self._p1

    @property
    def p2(self) -> Point3D:
        return self._p2

    # ------------------------------------------------------------------
    # Derived quantities
    # ------------------------------------------------------------------

    def length(self) -> float:
        return self._p1.distance_to(self._p2)

    def length_squared(self) -> float:
        return self._p1.distance_squared_to(self._p2)

    def direction(self) -> Vector3D:
        return Vector3D.from_two_points(self._p1, self._p2).normalized()

    def midpoint(self) -> Point3D:
        return Point3D(
            0.5 * (self._p1.x + self._p2.x),
            0.5 * (self._p1.y + self._p2.y),
            0.5 * (self._p1.z + self._p2.z),
        )

    # ------------------------------------------------------------------
    # Parametric evaluation (t=0 -> p1, t=1 -> p2; unclamped)
    # ------------------------------------------------------------------

    def point_at(self, t: float) -> Point3D:
        return Point3D(
            self._p1.x + t * (self._p2.x - self._p1.x),
            self._p1.y + t * (self._p2.y - self._p1.y),
            self._p1.z + t * (self._p2.z - self._p1.z),
        )

    def parameter_at(self, query: Point3D) -> float:
        offset = query - self._p1  # Vector3D
        segment = Vector3D.from_two_points(self._p1, self._p2)
        return offset.dot(segment) / self.length_squared()

    # ------------------------------------------------------------------
    # Closest point (clamped to [0, 1]) and distance
    # ------------------------------------------------------------------

    def closest_point(self, query: Point3D) -> Point3D:
        t = self.parameter_at(query)
        if t <= 0.0:
            return self._p1
        if t >= 1.0:
            return self._p2
        return self.point_at(t)

    def distance_to_point(self, query: Point3D) -> float:
        return query.distance_to(self.closest_point(query))

    def distance_squared_to_point(self, query: Point3D) -> float:
        return query.distance_squared_to(self.closest_point(query))

    # ------------------------------------------------------------------
    # Containment
    # ------------------------------------------------------------------

    def contains(self, query: Point3D, tolerance: float = 1e-10) -> bool:
        return self.distance_to_point(query) < tolerance

    # ------------------------------------------------------------------
    # Bridge to infinite line
    # ------------------------------------------------------------------

    def to_line(self) -> Line3D:
        return Line3D.from_two_points(self._p1, self._p2)

    # ------------------------------------------------------------------
    # Comparison (endpoint-order-insensitive, epsilon-based via Point3D.__eq__)
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Segment3D):
            return NotImplemented
        return (self._p1 == other._p1 and self._p2 == other._p2) or (
            self._p1 == other._p2 and self._p2 == other._p1
        )

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Segment3D(p1={self._p1}, p2={self._p2})"

    def __str__(self) -> str:
        return self.__repr__()
