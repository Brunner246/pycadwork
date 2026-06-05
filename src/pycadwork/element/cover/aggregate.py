"""Aggregate: the shared base for Wall, Slab, and Roof.

An aggregate is itself a cadwork element flagged with the appropriate
``CoverKind``. Its *children* are the siblings sharing the active grouping
value -- the link is the grouping attribute, not a container relation.

All aggregation logic lives here once and is shared by every subclass.
Subclasses narrow only the allowed ``CoverKind`` set; they do not duplicate
child-collection code.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar, TypeVar

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode
from pycadwork.element.base import Element
from pycadwork.element.cover.group import Group

E = TypeVar("E", bound="Element[Any]")


class Aggregate(Element):
    """Base for grouping-driven aggregates (Wall / Slab / Roof)."""

    _ALLOWED_KINDS: ClassVar[frozenset[CoverKind]] = frozenset()

    # ---- kind ----

    @property
    def kind(self) -> CoverKind:  # TODO: this can be derived from the element itself!
        snap = self.cadwork_type
        mapping = {
            CoverKind.FRAMED_WALL: snap.is_framed_wall,
            CoverKind.SOLID_WALL: snap.is_solid_wall,
            CoverKind.LOG_WALL: snap.is_log_wall,
            CoverKind.FRAMED_FLOOR: snap.is_framed_floor,
            CoverKind.SOLID_FLOOR: snap.is_solid_floor,
            CoverKind.FRAMED_ROOF: snap.is_framed_roof,
            CoverKind.SOLID_ROOF: snap.is_solid_roof,
        }
        for kind, flag in mapping.items():
            if flag:
                return kind
        raise ValueError(
            f"{type(self).__name__}(id={self.id}) is not flagged as any CoverKind"
        )

    def set_kind(self, kind: CoverKind) -> None:
        """Re-flag this aggregate. Subclasses restrict ``kind`` to their family."""
        if self._ALLOWED_KINDS and kind not in self._ALLOWED_KINDS:
            raise ValueError(
                f"{type(self).__name__}.set_kind: {kind} not allowed; "
                f"must be one of {sorted(k.name for k in self._ALLOWED_KINDS)}"
            )
        cadwork.attributes.set_cover_kind([self.id], kind)
        self._invalidate_type()

    # ---- grouping ----

    def _group(self) -> Group:
        return Group.of(self)

    def _group_key(self) -> str:
        return self._group().key

    def _set_group_key(self, eids: list[int], key: str) -> None:
        if Group.active_mode() is GroupingMode.GROUP:
            cadwork.attributes.set_group(eids, key)
        else:
            cadwork.attributes.set_subgroup(eids, key)

    # ---- children (uniform Element typing) ----

    @property
    def children(self) -> list[Element]:
        """Siblings sharing the active grouping value, minus self."""
        return [e for e in self._group().members() if e.id != self.id]

    def children_of(self, cls: type[E]) -> list[E]:
        """Children narrowed to runtime type ``cls`` (or subclass)."""
        return [e for e in self.children if isinstance(e, cls)]

    def children_by_type(self) -> dict[type[Element], list[Element]]:
        """Children grouped by their concrete wrapper class.

        One model scan; the keys answer "what types are in here?" and the values
        are the elements of each type -- subsuming repeated ``children_of`` probing.
        """
        grouped: dict[type[Element], list[Element]] = {}
        for e in self.children:
            grouped.setdefault(type(e), []).append(e)
        return grouped

    @property
    def child_types(self) -> set[type[Element]]:
        """Distinct concrete wrapper classes present among the children."""
        return set(self.children_by_type())

    # ---- imperative mutation ----

    def add_child(self, element: Element) -> None:
        """Set ``element``'s group/subgroup to match this aggregate's."""
        self._set_group_key([element.id], self._group_key())

    def add_children(self, elements: Iterable[Element]) -> None:
        """Attach ``elements`` to this aggregate's group in one batched write."""
        ids = [e.id for e in elements if e.id != self.id]
        if not ids:
            return
        self._set_group_key(ids, self._group_key())

    def remove_child(self, element: Element) -> None:
        """Clear ``element``'s grouping link to this aggregate."""
        self._set_group_key([element.id], "")

    def replace_children(self, elements: Iterable[Element]) -> None:
        """Detach all current children and attach the given ones in one pass."""
        current = [e.id for e in self.children]
        if current:
            self._set_group_key(current, "")
        new_ids = [e.id for e in elements]
        if new_ids:
            self._set_group_key(new_ids, self._group_key())
