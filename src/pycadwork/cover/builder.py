"""CoverBuilder: assemble cover aggregates from a set of elements.

The builder takes a bunch of elements, lets you set assembly options fluently,
then ``build()`` returns the assembled covers as ``list[Aggregate]``. The only
assembly strategy today is *aggregate by grouping* — bucket the elements by
their active ``group`` / ``subgroup`` key and turn each bucket that holds a
wall/floor/roof element into a typed ``Wall`` / ``Slab`` / ``Roof``::

    covers = CoverBuilder(elements).aggregate_by_grouping().build()
    walls = CoverBuilder(elements).aggregate_by_grouping().only(Wall).build()

The strategy is read-only — it identifies and types existing covers, it does
not write grouping. To attach children to a cover, use the imperative
``Aggregate.add_children(...)`` directly.

All cwapi3d access goes through :data:`pycadwork.cadwork_adapter.cadwork` to
honour the version-isolation seam.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import GroupingMode
from pycadwork.cover.aggregate import Aggregate
from pycadwork.cover.group import Group
from pycadwork.element.base import Element
from pycadwork.element.factory import from_id

class CoverBuilder:
    """Assemble cover aggregates from a set of elements via a chosen strategy."""

    def __init__(self, elements: Iterable[Element]) -> None:
        self._elements = list(elements)
        self._assemble: Callable[[], list[Aggregate]] | None = None
        self._only: tuple[type[Aggregate], ...] = ()

    def aggregate_by_grouping(self) -> "CoverBuilder":
        """Bucket elements by their active group/subgroup key; each bucket that
        holds a wall/floor/roof element yields one typed Aggregate."""
        self._assemble = self._by_grouping
        return self

    def only(self, *types: type[Aggregate]) -> "CoverBuilder":
        """Keep only assembled covers whose runtime type is one of ``types``
        (e.g. ``.only(Wall)`` or ``.only(Wall, Roof)``)."""
        self._only = types
        return self

    def build(self) -> list[Aggregate]:
        """Assemble and return the covers under the chosen strategy and filters."""
        if self._assemble is None:
            raise ValueError(
                "CoverBuilder.build: no assembly strategy set; "
                "call aggregate_by_grouping() first"
            )
        covers = self._assemble()
        if self._only:
            covers = [c for c in covers if isinstance(c, self._only)]
        return covers

    def _by_grouping(self) -> list[Aggregate]:
        mode = Group.active_mode()
        read_key = (
            cadwork.attributes.get_group
            if mode is GroupingMode.GROUP
            else cadwork.attributes.get_subgroup
        )
        buckets: dict[str, list[Element]] = {}
        for el in self._elements:
            key = read_key(el.id)
            if not key:
                continue
            buckets.setdefault(key, []).append(el)

        covers: list[Aggregate] = []
        for members in buckets.values():
            parent = next(
                (
                    m
                    for m in members
                    if (s := m.cadwork_type) and (s.is_wall or s.is_floor or s.is_roof)
                ),
                None,
            )
            if parent is None:
                continue
            wrapped = from_id(parent.id)
            if isinstance(wrapped, Aggregate):
                covers.append(wrapped)
        return covers
