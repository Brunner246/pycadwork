"""The single common base class for every wrapper in pycadwork.

Every concrete thing -- ``Beam``, ``Plate``, ``Drilling``, ``Node``,
``Wall``, ``Slab``, ``Roof`` -- inherits from :class:`Element`. Aggregate
APIs return ``list[Element]``; type-specific filtering is done with the
generic helper ``Group.members_of(cls)``. There are no ``.beams`` /
``.plates`` / ``.drillings`` accessors anywhere in the package.

``Element`` aggregates two component objects so the per-element surface
stays small:

* :attr:`attrs` — :class:`Attributes`, the cadwork attribute surface
  (``name``, ``group``, ``material_name``, ``user_attribute``, ...)
* :attr:`geometry` — a :class:`Geometry` (or subclass) wrapping
  shape-specific accessors. Each subclass binds the appropriate type via
  the ``_geometry_cls`` class attribute.

All component reads are live queries against the active backend; no
caching except the immutable :class:`ElementTypeSnapshot` held on
:class:`Element` itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId, ElementTypeSnapshot
from pycadwork.element.components import Attributes, Geometry

if TYPE_CHECKING:
    from pycadwork.geometry.plane3d import Plane3D

# Classic ``Generic[GeometryT]`` rather than the PEP 695 ``class Element[G]``
# syntax: PyCharm (and other IDEs) resolve subscripted classic generics plus a
# class-level attribute annotation far more reliably than the 3.12 type-parameter
# form, which is what gives ``beam.geometry.<TAB>`` working completion. The
# ``default=Geometry`` (PEP 696) keeps bare ``Element`` resolving to plain
# ``Geometry``; an IDE that ignores the default still falls back to the bound.
GeometryT = TypeVar("GeometryT", bound=Geometry, default=Geometry)


class Element(Generic[GeometryT]):
    """Live wrapper around a cadwork element ID.

    Generic in its geometry component so subclasses narrow the static type of
    :attr:`geometry`: ``Beam`` is an ``Element[LinearGeometry]``, ``Plate`` an
    ``Element[OrientedGeometry]``, ``Node`` an ``Element[NodeGeometry]``. Bare
    ``Element`` defaults to plain :class:`Geometry`. The runtime component is
    still chosen by the ``_geometry_cls`` class attribute; the type parameter
    only carries the static type — the two are kept in step by each subclass.

    Subclasses add typed creation classmethods, narrow predicates, and
    bind a specific :class:`Geometry` subtype via ``_geometry_cls``; they
    do not duplicate attribute or geometry logic. Equality is by
    ``(type, id)``.

    See :class:`pycadwork.element.linear.LinearElement` and
    :class:`pycadwork.element.oriented.OrientedElement` for shapes that
    bind richer geometry components.
    """

    __slots__ = ("_id", "_type", "attrs", "geometry")

    # Typed ``type[Geometry]`` rather than ``type[GeometryT]``: a type parameter
    # may not annotate a (non-ClassVar) class attribute, so the static link to
    # ``GeometryT`` is made by the one ``cast`` in ``__init__`` instead.
    _geometry_cls: type[Geometry] = Geometry

    # Class-scope annotation (no value — compatible with ``__slots__``) so IDEs
    # narrow ``self.geometry`` to each subclass's bound geometry component.
    geometry: GeometryT

    def __init__(self, element_id: int) -> None:
        self._id: ElementId = ElementId(int(element_id))
        self._type: ElementTypeSnapshot | None = None
        self.attrs: Attributes = Attributes(self._id)
        self.geometry = cast(GeometryT, type(self)._geometry_cls(self._id))

    # ---- identity ----

    @property
    def id(self) -> ElementId:
        return self._id

    @property
    def cadwork_type(self) -> ElementTypeSnapshot:
        if self._type is None:
            self._type = cadwork.elements.get_element_type(self._id)
        return self._type

    def _invalidate_type(self) -> None:
        """Drop the cached snapshot. Use after operations that change the type."""
        self._type = None

    # ---- lifecycle ----

    def delete(self) -> None:
        cadwork.elements.delete_elements([self._id])

    # ---- shape operations ----
    # Only the genuinely unary ops live here; everything multi-element stays
    # in ``pycadwork.ops`` so no operand is arbitrarily privileged. Late
    # imports avoid the base <-> ops cycle. No ``_invalidate_type()``:
    # booleans change shape, never the cadwork type.

    def cut_with_plane(self, plane: Plane3D) -> bool:
        """Cut this element with ``plane``; ``False`` when the plane misses it."""
        from pycadwork.ops import boolean

        return boolean.cut_with_plane(self, plane)

    def slice_with_plane(self, plane: Plane3D) -> list[Element]:
        """Slice this element with ``plane`` and return the new pieces."""
        from pycadwork.ops import boolean

        return boolean.slice_with_plane(self, plane)

    # ---- equality / hashing / repr ----

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Element):
            return NotImplemented
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self), self._id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self._id}, name={self.attrs.name!r})"
