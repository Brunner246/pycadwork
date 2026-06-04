"""Group: the engine of cover-object aggregation.

A ``Group`` is a value-typed view over the set of elements that share a
``group`` (or ``subgroup``) value. The active mode comes from the backend's
``get_element_grouping_type()`` -- read at call time, so the same code
adapts when the project-wide setting changes.

``Group`` is not an :class:`Element`. It is the implementation detail used
by ``CoverObject.members`` to expose its children polymorphically.
"""
from __future__ import annotations

from typing import Any, TypeVar

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import GroupingMode
from pycadwork.element.base import Element
from pycadwork.element.factory import from_id

# ``Element[Any]`` not bare ``Element``: ``Element`` is generic and invariant in
# its geometry parameter, so ``bound=Element`` (i.e. ``Element[Geometry]``) would
# reject specialized subclasses like ``Beam`` at call sites like ``members_of(Beam)``.
E = TypeVar("E", bound="Element[Any]")


class Group:
    """A view of all cadwork elements sharing one group/subgroup value."""

    __slots__ = ("_key", "_mode")

    def __init__(self, key: str, mode: GroupingMode) -> None:
        self._key = key
        self._mode = mode

    @classmethod
    def active_mode(cls) -> GroupingMode:
        """The project-wide grouping mode, read live from the adapter."""
        return cadwork.grouping.get_element_grouping_type()

    @classmethod
    def of(cls, member: Element) -> "Group":
        """Build a :class:`Group` from ``member``'s value under the active mode."""
        mode = cls.active_mode()
        attrs = cadwork.attributes
        key = (
            attrs.get_group(member.id)
            if mode is GroupingMode.GROUP
            else attrs.get_subgroup(member.id)
        )
        return cls(key, mode)

    @property
    def key(self) -> str:
        return self._key

    @property
    def mode(self) -> GroupingMode:
        return self._mode

    def members(self) -> list[Element]:
        """All elements (including the cover itself) sharing this group key."""
        if not self._key:
            return []
        grouping = cadwork.grouping
        if self._mode is GroupingMode.GROUP:
            eids = grouping.filter_elements_by_group(self._key)
        else:
            eids = grouping.filter_elements_by_subgroup(self._key)
        return [from_id(eid) for eid in eids]

    def members_of(self, cls: type[E]) -> list[E]:
        """Subset of :meth:`members` whose runtime type is ``cls`` or a subclass.

        The parameterized helper subsumes any per-type accessor — adding a new
        element subclass never requires a new method here.
        """
        return [e for e in self.members() if isinstance(e, cls)]

    def __repr__(self) -> str:
        return f"Group(key={self._key!r}, mode={self._mode.name})"
