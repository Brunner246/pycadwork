"""CoverBuilder: batch-attach children to a pre-built cover Aggregate.

The builder does one thing — it collects children and lands them in the
cover's group with a single cadwork API call instead of N round-trips.
The cover (a typed ``Wall`` / ``Slab`` / ``Roof``) must already exist,
already carry the right ``CoverKind`` flag, and already have a non-empty
group/subgroup key under the active ``GroupingMode``. The caller owns
those preconditions::

    cover_beam = Beam.create_rectangular(...)
    cover_beam.attrs.set_group("WallA")
    cadwork.attributes.set_cover_kind([cover_beam.id], CoverKind.FRAMED_WALL)
    wall = Wall(cover_beam.id)

    wall = (
        CoverBuilder(wall)
        .add(Beam.create_rectangular(...))
        .add_all([plate, drilling])
        .build()
    )

Callers that prefer the imperative path use ``Aggregate.add_child`` /
``add_children`` directly and skip the builder entirely.
"""
from __future__ import annotations

from collections.abc import Iterable

from pycadwork.cadwork_adapter.types import GroupingMode
from pycadwork.cover.aggregate import Aggregate
from pycadwork.cover.group import Group
from pycadwork.element.base import Element


class CoverBuilder:
    """Fluent batch-attach of children to a pre-built cover Aggregate."""

    def __init__(self, cover: Aggregate) -> None:
        self._cover = cover
        self._members: list[Element] = []

    def add(self, element: Element) -> "CoverBuilder":
        self._members.append(element)
        return self

    def add_all(self, elements: Iterable[Element]) -> "CoverBuilder":
        self._members.extend(elements)
        return self

    def build(self) -> Aggregate:
        """Attach all collected children to the cover in one batched write."""
        key = Group.of(self._cover).key
        if not key:
            mode = Group.active_mode()
            attr_name = "group" if mode is GroupingMode.GROUP else "subgroup"
            setter = "set_group" if mode is GroupingMode.GROUP else "set_subgroup"
            raise ValueError(
                f"CoverBuilder.build: cover (id={self._cover.id}) has no "
                f"{attr_name} key set. Set it via attrs.{setter}(...) "
                f"before constructing the builder."
            )
        self._cover.add_children(self._members)
        return self._cover
