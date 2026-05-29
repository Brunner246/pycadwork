from __future__ import annotations

import math
from typing import overload

from pycadwork.geometry.vector3d import Vector3D

_COMPARISON_EPSILON = 1e-10


class Point3D:
    """A position in 3D space.

    Unlike Vector3D, a point does not have a magnitude; it participates in:
      Point + Vector -> Point  (translate)
      Point - Vector -> Point  (translate backwards)
      Point - Point  -> Vector (displacement)
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
    def origin() -> Point3D:
        return Point3D(0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Arithmetic with Vector3D
    # ------------------------------------------------------------------

    def __add__(self, v: Vector3D) -> Point3D:
        return Point3D(self.x + v.x, self.y + v.y, self.z + v.z)

    @overload
    def __sub__(self, other: Vector3D) -> Point3D: ...
    @overload
    def __sub__(self, other: Point3D) -> Vector3D: ...
    def __sub__(self, other: Vector3D | Point3D) -> Point3D | Vector3D:
        if isinstance(other, Vector3D):
            return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)
        if isinstance(other, Point3D):
            return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
        return NotImplemented

    def __iadd__(self, v: Vector3D) -> Point3D:
        self.x += v.x
        self.y += v.y
        self.z += v.z
        return self

    def __isub__(self, v: Vector3D) -> Point3D:
        self.x -= v.x
        self.y -= v.y
        self.z -= v.z
        return self

    # ------------------------------------------------------------------
    # Comparison (epsilon-based)
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point3D):
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
    # Distance
    # ------------------------------------------------------------------

    def distance_to(self, other: Point3D) -> float:
        return math.sqrt(self.distance_squared_to(other))

    def distance_squared_to(self, other: Point3D) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return dx * dx + dy * dy + dz * dz

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Point3D({self.x}, {self.y}, {self.z})"

    def __str__(self) -> str:
        return self.__repr__()
