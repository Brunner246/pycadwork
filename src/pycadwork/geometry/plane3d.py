from __future__ import annotations

import math

from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D


class Plane3D:
    """An infinite plane in 3D space defined by a point and unit normal vector.

    Mathematically: n . (P - P0) = 0, or ax + by + cz + d = 0.

    Construct via the static factory methods; the constructor is private.
    """

    __slots__ = ("_point", "_normal")

    # Private constructor ------------------------------------------------

    def __init__(self, point: Point3D, normal: Vector3D) -> None:
        self._point = point
        self._normal = normal

    # ------------------------------------------------------------------
    # Static factory methods
    # ------------------------------------------------------------------

    @staticmethod
    def from_default() -> Plane3D:
        """XY plane at z=0."""
        return Plane3D(Point3D.origin(), Vector3D.unit_z())

    @staticmethod
    def from_point_and_normal(point: Point3D, normal: Vector3D) -> Plane3D:
        return Plane3D(point, normal.normalized())

    @staticmethod
    def from_three_points(p1: Point3D, p2: Point3D, p3: Point3D) -> Plane3D:
        v1 = p2 - p1  # Vector3D
        v2 = p3 - p1  # Vector3D
        cross = v1.cross(v2)
        if cross.is_zero():
            raise ValueError("Cannot create plane from collinear points")
        return Plane3D(p1, cross.normalized())

    @staticmethod
    def from_coefficients(a: float, b: float, c: float, d: float) -> Plane3D:
        normal = Vector3D(a, b, c)
        if normal.is_zero():
            raise ValueError("Plane normal cannot be zero")
        unit_normal = normal.normalized()
        if abs(c) > 1e-10:
            point = Point3D(0.0, 0.0, -d / c)
        elif abs(b) > 1e-10:
            point = Point3D(0.0, -d / b, 0.0)
        else:
            point = Point3D(-d / a, 0.0, 0.0)
        return Plane3D(point, unit_normal)

    @staticmethod
    def xy(z: float = 0.0) -> Plane3D:
        return Plane3D(Point3D(0.0, 0.0, z), Vector3D.unit_z())

    @staticmethod
    def xz(y: float = 0.0) -> Plane3D:
        return Plane3D(Point3D(0.0, y, 0.0), Vector3D.unit_y())

    @staticmethod
    def yz(x: float = 0.0) -> Plane3D:
        return Plane3D(Point3D(x, 0.0, 0.0), Vector3D.unit_x())

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def point(self) -> Point3D:
        return self._point

    @property
    def normal(self) -> Vector3D:
        return self._normal

    def d(self) -> float:
        """Return the d coefficient: d = -n . P0."""
        return -(
            self._normal.x * self._point.x
            + self._normal.y * self._point.y
            + self._normal.z * self._point.z
        )

    def coefficients(self) -> tuple[float, float, float, float]:
        return (self._normal.x, self._normal.y, self._normal.z, self.d())

    # ------------------------------------------------------------------
    # Distance operations
    # ------------------------------------------------------------------

    def signed_distance_to(self, point: Point3D) -> float:
        to_point = point - self._point  # Vector3D
        return self._normal.dot(to_point)

    def distance_to_point(self, point: Point3D) -> float:
        return abs(self.signed_distance_to(point))

    # ------------------------------------------------------------------
    # Point classification
    # ------------------------------------------------------------------

    def contains(self, point: Point3D, tolerance: float = 1e-10) -> bool:
        return abs(self.signed_distance_to(point)) < tolerance

    def is_above(self, point: Point3D) -> bool:
        return self.signed_distance_to(point) > 0.0

    def is_below(self, point: Point3D) -> bool:
        return self.signed_distance_to(point) < 0.0

    # ------------------------------------------------------------------
    # Projection operations
    # ------------------------------------------------------------------

    def project_point(self, point: Point3D) -> Point3D:
        dist = self.signed_distance_to(point)
        return Point3D(
            point.x - dist * self._normal.x,
            point.y - dist * self._normal.y,
            point.z - dist * self._normal.z,
        )

    def project_vector(self, vector: Vector3D) -> Vector3D:
        dot_product = vector.dot(self._normal)
        return Vector3D(
            vector.x - dot_product * self._normal.x,
            vector.y - dot_product * self._normal.y,
            vector.z - dot_product * self._normal.z,
        )

    # ------------------------------------------------------------------
    # Plane relationships
    # ------------------------------------------------------------------

    def is_parallel_to(self, other: Plane3D, tolerance: float = 1e-10) -> bool:
        cross = self._normal.cross(other._normal)
        return cross.dot(cross) < tolerance * tolerance

    def is_perpendicular_to(self, other: Plane3D, tolerance: float = 1e-10) -> bool:
        return abs(self._normal.dot(other._normal)) < tolerance

    def is_coplanar_with(self, other: Plane3D, tolerance: float = 1e-10) -> bool:
        if not self.is_parallel_to(other, tolerance):
            return False
        return self.contains(other._point, tolerance)

    def angle_to(self, other: Plane3D) -> float:
        cos_angle = self._normal.dot(other._normal)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.acos(abs(cos_angle))

    def distance_to_plane(
        self, other: Plane3D, tolerance: float = 1e-10
    ) -> float | None:
        if not self.is_parallel_to(other, tolerance):
            return None
        return abs(self.signed_distance_to(other._point))

    # ------------------------------------------------------------------
    # Line/Ray intersection
    # ------------------------------------------------------------------

    def intersect_line_parameter(
        self, line_point: Point3D, line_dir: Vector3D
    ) -> float | None:
        denominator = self._normal.dot(line_dir)
        if abs(denominator) < 1e-15:
            return None
        to_plane = self._point - line_point  # Vector3D
        return self._normal.dot(to_plane) / denominator

    def intersect_line(self, line_point: Point3D, line_dir: Vector3D) -> Point3D | None:
        t = self.intersect_line_parameter(line_point, line_dir)
        if t is None:
            return None
        return Point3D(
            line_point.x + t * line_dir.x,
            line_point.y + t * line_dir.y,
            line_point.z + t * line_dir.z,
        )

    # ------------------------------------------------------------------
    # Plane transformations
    # ------------------------------------------------------------------

    def offset(self, distance: float) -> Plane3D:
        new_point = Point3D(
            self._point.x + distance * self._normal.x,
            self._point.y + distance * self._normal.y,
            self._point.z + distance * self._normal.z,
        )
        return Plane3D(new_point, self._normal)

    def flipped(self) -> Plane3D:
        return Plane3D(self._point, -self._normal)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Plane3D):
            return NotImplemented
        return self.is_coplanar_with(other)

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        c = self.coefficients()
        return f"Plane3D({c[0]}x + {c[1]}y + {c[2]}z + {c[3]} = 0)"

    def __str__(self) -> str:
        return self.__repr__()
