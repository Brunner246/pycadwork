from __future__ import annotations

from collections.abc import Iterable

from pycadwork.geometry.loop import Loop
from pycadwork.geometry.plane3d import Plane3D
from pycadwork.geometry.vector3d import Vector3D


class Face:
    """A planar face described by an outer boundary, optional holes, and a support plane.

    All loops are assumed to lie on ``support_plane`` within tolerance. No
    topological relationship is maintained between faces.
    """

    __slots__ = ("_outer", "_inner", "_plane")

    def __init__(
        self,
        outer_loop: Loop,
        support_plane: Plane3D,
        inner_loops: Iterable[Loop] = (),
    ) -> None:
        self._outer = outer_loop
        self._inner: list[Loop] = list(inner_loops)
        self._plane = support_plane

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def outer_loop(self) -> Loop:
        return self._outer

    @property
    def inner_loops(self) -> list[Loop]:
        return list(self._inner)

    @property
    def support_plane(self) -> Plane3D:
        return self._plane

    @property
    def normal(self) -> Vector3D:
        return self._plane.normal

    def inner_loop_count(self) -> int:
        return len(self._inner)

    def has_holes(self) -> bool:
        return bool(self._inner)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Face):
            return NotImplemented
        if self._outer != other._outer:
            return False
        if len(self._inner) != len(other._inner):
            return False
        if any(a != b for a, b in zip(self._inner, other._inner)):
            return False
        return self._plane == other._plane

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Face(outer={self._outer}, holes={len(self._inner)}, "
            f"plane={self._plane})"
        )

    def __str__(self) -> str:
        return self.__repr__()
