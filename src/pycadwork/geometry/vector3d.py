from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pycadwork.value_types import Angle, Length

if TYPE_CHECKING:
    from pycadwork.geometry.point3d import Point3D

_DIVISION_EPSILON = 1e-15
_COMPARISON_EPSILON = 1e-10


class Vector3D:
    """A 3D vector with direction and magnitude.

    Unlike Point3D, translation does not apply to vectors -- only rotation/scaling.
    """

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.z = z

    # ------------------------------------------------------------------
    # Static factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def zero() -> Vector3D:
        return Vector3D(0.0, 0.0, 0.0)

    @staticmethod
    def unit_x() -> Vector3D:
        return Vector3D(1.0, 0.0, 0.0)

    @staticmethod
    def unit_y() -> Vector3D:
        return Vector3D(0.0, 1.0, 0.0)

    @staticmethod
    def unit_z() -> Vector3D:
        return Vector3D(0.0, 0.0, 1.0)

    @staticmethod
    def from_two_points(from_pt: Point3D, to_pt: Point3D) -> Vector3D:
        """Compute the displacement vector from *from_pt* to *to_pt*."""
        return Vector3D(to_pt.x - from_pt.x, to_pt.y - from_pt.y, to_pt.z - from_pt.z)

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> Vector3D:
        return Vector3D(-self.x, -self.y, -self.z)

    def __mul__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3D:
        if abs(scalar) < _DIVISION_EPSILON:
            raise ValueError("Division by zero in Vector3D")
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def __iadd__(self, other: Vector3D) -> Vector3D:
        self.x += other.x
        self.y += other.y
        self.z += other.z
        return self

    def __isub__(self, other: Vector3D) -> Vector3D:
        self.x -= other.x
        self.y -= other.y
        self.z -= other.z
        return self

    def __imul__(self, scalar: float) -> Vector3D:
        self.x *= scalar
        self.y *= scalar
        self.z *= scalar
        return self

    def __itruediv__(self, scalar: float) -> Vector3D:
        if abs(scalar) < _DIVISION_EPSILON:
            raise ValueError("Division by zero in Vector3D")
        self.x /= scalar
        self.y /= scalar
        self.z /= scalar
        return self

    # ------------------------------------------------------------------
    # Comparison (epsilon-based)
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3D):
            return NotImplemented
        return (
            abs(self.x - other.x) < _COMPARISON_EPSILON
            and abs(self.y - other.y) < _COMPARISON_EPSILON
            and abs(self.z - other.z) < _COMPARISON_EPSILON
        )

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # Vector operations
    # ------------------------------------------------------------------

    def dot(self, other: Vector3D) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3D) -> Vector3D:
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def magnitude(self) -> Length:
        return Length(math.sqrt(self.dot(self)))

    def normalized(self) -> Vector3D:
        magnitude = self.magnitude()
        if magnitude < _DIVISION_EPSILON:
            raise ValueError("Cannot normalize zero-length vector")
        return self / magnitude

    def normalize(self) -> None:
        magnitude = self.magnitude()
        if magnitude < _DIVISION_EPSILON:
            raise ValueError("Cannot normalize zero-length vector")
        self.x /= magnitude
        self.y /= magnitude
        self.z /= magnitude

    def is_normalized(self, tolerance: float = _COMPARISON_EPSILON) -> bool:
        return abs(self.dot(self) - 1.0) < tolerance

    def is_zero(self, tolerance: float = _COMPARISON_EPSILON) -> bool:
        return self.dot(self) < tolerance * tolerance

    def angle_to(self, other: Vector3D) -> Angle:
        magnitude_product = math.sqrt(self.dot(self) * other.dot(other))
        if magnitude_product < _DIVISION_EPSILON:
            return Angle(0.0)
        cos_angle = self.dot(other) / magnitude_product
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return Angle(math.acos(cos_angle))

    def project_onto(self, other: Vector3D) -> Vector3D:
        other_magnitude_squared = other.dot(other)
        if other_magnitude_squared < _DIVISION_EPSILON:
            return Vector3D.zero()
        return other * (self.dot(other) / other_magnitude_squared)

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Vector3D({self.x}, {self.y}, {self.z})"

    def __str__(self) -> str:
        return self.__repr__()
