"""The serializable detail schema: :class:`MemberSpec` and :class:`DetailDefinition`.

A :class:`DetailDefinition` is a pure, frozen description of a timber-frame
detail — what beams and panels make it up, where they sit, and how each behaves
when the element-module calculation runs it inside a wall. It holds no element
ids and touches no cadwork: it is the artifact that gets authored, serialized,
shared, and later *realized* (see :mod:`pycadwork.detail.realizer`).

``to_dict`` / ``from_dict`` delegate the geometry-bearing parts to
:mod:`pycadwork.detail.serde` and the property bag to
:class:`pycadwork.detail.properties.ModuleProperties`, so the on-disk shape stays
consistent across native and foreign loaders.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pycadwork.cadwork_adapter.types import CoverKind, DetailType
from pycadwork.detail import serde
from pycadwork.detail.properties import ModuleProperties
from pycadwork.geometry.specs import AxisFrame, AxisPoints, PanelSection, RectSection

#: The schema id native definitions carry; recognised by the native loader.
NATIVE_SCHEMA = "pycadwork.detail"
#: The native schema's current version.
NATIVE_VERSION = "1"


class DefinitionError(ValueError):
    """Raised when a :class:`MemberSpec` / :class:`DetailDefinition` is malformed."""


@dataclass(frozen=True, slots=True)
class MemberSpec:
    """One framing member of a detail: its kind, section, placement, semantics.

    Exactly one of ``points`` / ``frame`` is populated (the two placement forms
    the creation classmethods accept). The cross-section type must match the
    geometry kind — a ``"beam"`` carries a :class:`RectSection`, a ``"panel"`` a
    :class:`PanelSection`. Semantics come from a named ``role`` (resolved to a
    :class:`ModuleProperties` preset) and/or an explicit ``properties`` override.
    """

    kind: str  # "beam" | "panel"
    section: RectSection | PanelSection
    points: AxisPoints | None = None
    frame: AxisFrame | None = None
    role: str | None = None
    properties: ModuleProperties | None = None
    name: str | None = None
    material: str | None = None
    group: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("beam", "panel"):
            raise DefinitionError(f"MemberSpec.kind must be beam|panel, got {self.kind!r}")
        if (self.points is None) == (self.frame is None):
            raise DefinitionError(
                "MemberSpec needs exactly one of points/frame"
            )
        if self.kind == "beam" and not isinstance(self.section, RectSection):
            raise DefinitionError("a beam member needs a RectSection")
        if self.kind == "panel" and not isinstance(self.section, PanelSection):
            raise DefinitionError("a panel member needs a PanelSection")

    @property
    def placement(self) -> AxisPoints | AxisFrame:
        """The populated placement, regardless of which form it took."""
        return self.points if self.points is not None else self.frame  # type: ignore[return-value]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": self.kind,
            "section": serde.encode(self.section),
            "placement": serde.encode(self.placement),
        }
        if self.role is not None:
            out["role"] = self.role
        if self.properties is not None:
            out["properties"] = self.properties.to_dict()
        for opt in ("name", "material", "group"):
            value = getattr(self, opt)
            if value is not None:
                out[opt] = value
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemberSpec":
        section = serde.decode(data["section"])
        placement = serde.decode(data["placement"])
        points = placement if isinstance(placement, AxisPoints) else None
        frame = placement if isinstance(placement, AxisFrame) else None
        props = data.get("properties")
        return cls(
            kind=data["kind"],
            section=section,
            points=points,
            frame=frame,
            role=data.get("role"),
            properties=ModuleProperties.from_dict(props) if props is not None else None,
            name=data.get("name"),
            material=data.get("material"),
            group=data.get("group"),
        )


@dataclass(frozen=True, slots=True)
class DetailDefinition:
    """A complete, shareable detail: its members plus the situation they apply to."""

    name: str
    detail_type: DetailType
    cover_kind: CoverKind
    members: tuple[MemberSpec, ...] = ()
    schema: str = NATIVE_SCHEMA
    schema_version: str = NATIVE_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "name": self.name,
            "detail_type": self.detail_type.value,
            "cover_kind": self.cover_kind.value,
            "members": [m.to_dict() for m in self.members],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DetailDefinition":
        return cls(
            name=data["name"],
            detail_type=DetailType(data["detail_type"]),
            cover_kind=CoverKind(data["cover_kind"]),
            members=tuple(MemberSpec.from_dict(m) for m in data.get("members", ())),
            schema=data.get("schema", NATIVE_SCHEMA),
            schema_version=data.get("schema_version", NATIVE_VERSION),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "DetailDefinition":
        return cls.from_dict(json.loads(text))
