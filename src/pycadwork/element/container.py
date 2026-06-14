"""Container: an aggregate backed by cadwork's real containment API.

A container *behaves* like a cover aggregate -- it owns a set of typed
children -- but the link is fundamentally different. A cover (Wall / Slab /
Roof) links its members by a shared ``group`` / ``subgroup`` value; a container
links its members by an actual parent-child relation in the model. So a
container reads its members with ``get_container_content_elements`` and any
element reads its owner with ``get_parent_container_id`` -- there is no grouping
involved. For that reason :class:`Container` does **not** inherit the
grouping-coupled :class:`pycadwork.element.cover.Aggregate`; it merely exposes
the same uniform ``children`` / ``children_of`` surface.

All cwapi3d access goes through :data:`pycadwork.cadwork_adapter.cadwork` to
honour the version-isolation seam.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Self, TypeVar

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element.base import Element
from pycadwork.element.factory import from_id
from pycadwork.element.registry import AGGREGATE, register_element

E = TypeVar("E", bound="Element[Any]")


@register_element(lambda s: s.is_container, priority=AGGREGATE)
class Container(Element):
    """A cadwork container -- a parent element owning a set of child elements."""

    __slots__ = ()

    # ---- children (uniform Element typing) ----

    @property
    def children(self) -> list[Element]:
        """The container's content elements, each wrapped in its typed class."""
        return [
            from_id(eid)
            for eid in cadwork.elements.get_container_content_elements(self.id)
        ]

    def children_of(self, cls: type[E]) -> list[E]:
        """Children narrowed to runtime type ``cls`` (or subclass)."""
        return [e for e in self.children if isinstance(e, cls)]

    # ---- imperative mutation ----

    def add_child(self, element: Element) -> None:
        """Add ``element`` to this container's contents."""
        self.add_children([element])

    def add_children(self, elements: Iterable[Element]) -> None:
        """Add ``elements`` to this container's contents in one batched write."""
        current = cadwork.elements.get_container_content_elements(self.id)
        merged = list(
            dict.fromkeys([*current, *(e.id for e in elements if e.id != self.id)])
        )
        cadwork.elements.set_container_contents(self.id, merged)

    def remove_child(self, element: Element) -> None:
        """Remove ``element`` from this container's contents."""
        current = cadwork.elements.get_container_content_elements(self.id)
        cadwork.elements.set_container_contents(
            self.id, [eid for eid in current if eid != element.id]
        )

    def replace_children(self, elements: Iterable[Element]) -> None:
        """Set the container's contents to exactly ``elements``."""
        cadwork.elements.set_container_contents(self.id, [e.id for e in elements])

    # ---- creation ----

    @classmethod
    def create_from_standard(
        cls,
        elements: Iterable[Element],
        output_name: str,
        standard_element_name: str,
        *,
        reference: Element | None = None,
    ) -> Self:
        """Build a container from ``elements`` using a configured standard.

        ``standard_element_name`` must name a container standard that exists in
        the active cadwork project. Pass ``reference`` to place the container
        relative to an existing element (the cadwork "with reference" variant);
        omit it to let cadwork place the container itself. Returns the new
        :class:`Container`.
        """
        eids = [e.id for e in elements]
        if reference is None:
            eid = cadwork.elements.create_auto_container_from_standard(
                eids, output_name, standard_element_name
            )
        else:
            eid = cadwork.elements.create_auto_container_from_standard_with_reference(
                eids, output_name, standard_element_name, reference.id
            )
        return cls(eid)


def discover_containers(ids: Iterable[int] | None = None) -> list[Container]:
    """Return every model element flagged as a container, typed.

    ``ids`` defaults to the active identifiable elements; pass an iterable to
    scan a custom subset. Each container's children stay a live view via
    :attr:`Container.children` -- discovery only finds the parents.
    """
    elements = cadwork.elements
    eids: Iterable[ElementId] = (
        [ElementId(i) for i in ids]
        if ids is not None
        else elements.get_active_identifiable_element_ids()
    )

    containers: list[Container] = []
    for eid in eids:
        if not elements.get_element_type(eid).is_container:
            continue
        wrapped = from_id(eid)
        if isinstance(wrapped, Container):
            containers.append(wrapped)
    return containers


def parent_container(element: Element) -> Container | None:
    """The :class:`Container` owning ``element``, or ``None`` if it has none."""
    pid = cadwork.elements.get_parent_container_id(element.id)
    if pid <= 0:
        return None
    wrapped = from_id(pid)
    return wrapped if isinstance(wrapped, Container) else None


__all__ = ["Container", "discover_containers", "parent_container"]
