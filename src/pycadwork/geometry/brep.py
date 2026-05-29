from __future__ import annotations

from collections.abc import Iterable

from pycadwork.geometry.face import Face


class Brep:
    """A boundary representation: a flat collection of planar Faces.

    This lightweight Brep does not track shared edges or vertices between
    faces; each Face carries its own outer/inner loops and support plane.
    """

    __slots__ = ("_faces",)

    def __init__(self, faces: Iterable[Face] = ()) -> None:
        self._faces: list[Face] = list(faces)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def faces(self) -> list[Face]:
        return list(self._faces)

    def face_count(self) -> int:
        return len(self._faces)

    def is_empty(self) -> bool:
        return not self._faces

    def face_at(self, index: int) -> Face:
        """Return the face at ``index``.

        Raises:
            IndexError: if ``index`` is outside ``[0, face_count())``.
        """
        if index < 0 or index >= len(self._faces):
            raise IndexError("Brep.face_at: index out of range")
        return self._faces[index]

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def add_face(self, face: Face) -> None:
        self._faces.append(face)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Brep):
            return NotImplemented
        if len(self._faces) != len(other._faces):
            return False
        return all(a == b for a, b in zip(self._faces, other._faces))

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Brep({len(self._faces)} faces)"

    def __str__(self) -> str:
        return self.__repr__()
