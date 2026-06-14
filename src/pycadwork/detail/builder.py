"""``DetailBuilder``: fluent authoring of a :class:`DetailDefinition`.

Mirrors ``CoverBuilder`` — chain setters, then ``build()`` validates and freezes
the result. The builder is where two authoring concerns are enforced:

* **role resolution** — a member added with a ``role`` is checked against the
  role registry now, so an unknown role fails at authoring time, not at realize
  time;
* **detail_type ↔ cover_kind coherence** — a ``floor_*`` detail must target a
  slab kind, a ``roof_detail`` a roof kind, the wall situations a wall kind. The
  required families reuse ``WALL_KINDS`` / ``SLAB_KINDS`` / ``ROOF_KINDS``.
"""

from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter.types import (
    ROOF_KINDS,
    SLAB_KINDS,
    WALL_KINDS,
    CoverKind,
    DetailType,
)
from pycadwork.detail.definition import DetailDefinition, MemberSpec
from pycadwork.detail.properties import ModuleProperties
from pycadwork.detail.roles import get_role
from pycadwork.geometry.specs import AxisFrame, AxisPoints, PanelSection, RectSection

# Every CoverKind — the family allowed for the situation-agnostic NO_DETAIL.
_ALL_KINDS = WALL_KINDS | SLAB_KINDS | ROOF_KINDS


def required_kinds(detail_type: DetailType) -> frozenset[CoverKind]:
    """The cover-kind family a ``detail_type`` may be hosted by."""
    if detail_type is DetailType.NO_DETAIL:
        return frozenset(_ALL_KINDS)
    name = detail_type.value
    if name.startswith("floor_"):
        return SLAB_KINDS
    if name.startswith("roof_"):
        return ROOF_KINDS
    return WALL_KINDS


class DetailBuilder:
    """Assemble a :class:`DetailDefinition` fluently, validating on ``build()``."""

    __slots__ = ("_name", "_detail_type", "_cover_kind", "_members", "_metadata")

    def __init__(self) -> None:
        self._name: str | None = None
        self._detail_type: DetailType | None = None
        self._cover_kind: CoverKind | None = None
        self._members: list[MemberSpec] = []
        self._metadata: dict[str, object] = {}

    def named(self, name: str) -> Self:
        self._name = name
        return self

    def of_type(self, detail_type: DetailType) -> Self:
        self._detail_type = detail_type
        return self

    def cover(self, cover_kind: CoverKind) -> Self:
        self._cover_kind = cover_kind
        return self

    def metadata(self, **entries: object) -> Self:
        self._metadata.update(entries)
        return self

    def add_beam(
        self,
        section: RectSection,
        axis: AxisPoints | AxisFrame,
        *,
        role: str | None = None,
        properties: ModuleProperties | None = None,
        name: str | None = None,
        material: str | None = None,
        group: str | None = None,
    ) -> Self:
        self._add("beam", section, axis, role, properties, name, material, group)
        return self

    def add_panel(
        self,
        section: PanelSection,
        axis: AxisPoints | AxisFrame,
        *,
        role: str | None = None,
        properties: ModuleProperties | None = None,
        name: str | None = None,
        material: str | None = None,
        group: str | None = None,
    ) -> Self:
        self._add("panel", section, axis, role, properties, name, material, group)
        return self

    def _add(
        self,
        kind: str,
        section: RectSection | PanelSection,
        axis: AxisPoints | AxisFrame,
        role: str | None,
        properties: ModuleProperties | None,
        name: str | None,
        material: str | None,
        group: str | None,
    ) -> None:
        if role is not None:
            get_role(role)  # fail fast on an unknown role
        points = axis if isinstance(axis, AxisPoints) else None
        frame = axis if isinstance(axis, AxisFrame) else None
        self._members.append(
            MemberSpec(
                kind=kind,
                section=section,
                points=points,
                frame=frame,
                role=role,
                properties=properties,
                name=name,
                material=material,
                group=group,
            )
        )

    def build(self) -> DetailDefinition:
        """Validate the accumulated state and return a frozen definition."""
        if not self._name:
            raise ValueError("DetailBuilder: name not set; call .named(...)")
        if self._detail_type is None:
            raise ValueError("DetailBuilder: detail type not set; call .of_type(...)")
        if self._cover_kind is None:
            raise ValueError("DetailBuilder: cover kind not set; call .cover(...)")

        allowed = required_kinds(self._detail_type)
        if self._cover_kind not in allowed:
            raise ValueError(
                f"detail type {self._detail_type.name} is incompatible with cover "
                f"kind {self._cover_kind.name}; allowed: "
                f"{sorted(k.name for k in allowed)}"
            )

        return DetailDefinition(
            name=self._name,
            detail_type=self._detail_type,
            cover_kind=self._cover_kind,
            members=tuple(self._members),
            metadata=dict(self._metadata),
        )
