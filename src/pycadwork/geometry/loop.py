from __future__ import annotations

from collections.abc import Iterable

from pycadwork.geometry.point3d import Point3D


class Loop:
    """An ordered, closed polyline of Point3D vertices.

    The closing edge between the last and first vertex is implicit and not
    stored. A Loop describes either the outer boundary of a Face or one of
    its holes.
    """

    __slots__ = ("_vertices",)

    def __init__(self, vertices: Iterable[Point3D] = ()) -> None:
        self._vertices: list[Point3D] = list(vertices)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def vertices(self) -> list[Point3D]:
        return list(self._vertices)

    def vertex_count(self) -> int:
        return len(self._vertices)

    def is_empty(self) -> bool:
        return not self._vertices

    def vertex_at(self, index: int) -> Point3D:
        """Return the vertex at ``index``.

        Raises:
            IndexError: if ``index`` is outside ``[0, vertex_count())``.
        """
        if index < 0 or index >= len(self._vertices):
            raise IndexError("Loop.vertex_at: index out of range")
        return self._vertices[index]

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Loop):
            return NotImplemented
        if len(self._vertices) != len(other._vertices):
            return False
        return all(a == b for a, b in zip(self._vertices, other._vertices))

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Loop({len(self._vertices)} vertices)"

    def __str__(self) -> str:
        return self.__repr__()
