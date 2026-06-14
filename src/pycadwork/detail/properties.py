"""``ModuleProperties`` — the serializable mirror of cadwork's element-module
property bag.

cwapi3d exposes ~30 loosely-related setters on its ``element_module_properties``
object. Authoring against that flat surface is error-prone: the
``distribute_*`` / ``*_use_number`` / ``*_use_max_distance`` modes are mutually
exclusive, ``cutting_element`` carries a priority, and several flags contradict
one another. This module collapses those relationships into small *frozen*
dataclasses that simply cannot represent an illegal state — the invariants are
enforced in ``__post_init__``, so an instance that exists is an instance the
seam can apply verbatim.

The type is pure (stdlib only, no cadwork import): it is the shareable schema
the seam consumes. The cwapi3d setter names live in exactly one place —
``cadwork_adapter/_module.py`` — never here.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any


class ModulePropertyError(ValueError):
    """Raised when ``ModuleProperties`` (or one of its parts) is contradictory."""


@dataclass(frozen=True, slots=True)
class Distribution:
    """One axis of a member's distribution within a wall.

    A distribution is *off*, or *on* in exactly one of three mutually-exclusive
    modes: by fixed ``distance``, by ``count``, or by ``max_distance``. The
    ``__post_init__`` invariant makes any other combination unconstructable, so
    the seam can branch on which field is populated with no further checks.
    """

    active: bool = False
    distance: float | None = None
    count: int | None = None
    max_distance: float | None = None

    def __post_init__(self) -> None:
        chosen = [
            name
            for name, value in (
                ("distance", self.distance),
                ("count", self.count),
                ("max_distance", self.max_distance),
            )
            if value is not None
        ]
        if len(chosen) > 1:
            raise ModulePropertyError(
                "Distribution: at most one of distance/count/max_distance may be "
                f"set; got {chosen}"
            )
        if self.active and not chosen:
            raise ModulePropertyError(
                "Distribution.active requires exactly one of "
                "distance/count/max_distance"
            )
        if not self.active and chosen:
            raise ModulePropertyError(
                f"Distribution is inactive but {chosen[0]} is set; activate it or "
                "drop the value"
            )
        if self.count is not None and self.count <= 0:
            raise ModulePropertyError("Distribution.count must be positive")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"active": self.active}
        if self.distance is not None:
            out["distance"] = self.distance
        if self.count is not None:
            out["count"] = self.count
        if self.max_distance is not None:
            out["max_distance"] = self.max_distance
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Distribution":
        return cls(
            active=bool(data.get("active", False)),
            distance=data.get("distance"),
            count=data.get("count"),
            max_distance=data.get("max_distance"),
        )


@dataclass(frozen=True, slots=True)
class CuttingElement:
    """Whether a member cuts its neighbours, and at what priority.

    A higher ``priority`` wins when two cutting elements overlap. ``priority`` is
    meaningful only while ``active``; it is rejected otherwise.
    """

    active: bool = False
    priority: int | None = None

    def __post_init__(self) -> None:
        if self.priority is not None:
            if not self.active:
                raise ModulePropertyError(
                    "CuttingElement.priority set while inactive"
                )
            if self.priority < 0:
                raise ModulePropertyError("CuttingElement.priority must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"active": self.active}
        if self.priority is not None:
            out["priority"] = self.priority
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CuttingElement":
        return cls(active=bool(data.get("active", False)), priority=data.get("priority"))


@dataclass(frozen=True, slots=True)
class NamedFlag:
    """A boolean flag that, when active, also carries an associated layer name.

    Used for ``unique_layername`` (the name being the layer to emit on) and the
    ``keep_in_center_of_layer_*`` flags. ``name`` is ignored while inactive.
    """

    active: bool = False
    name: str = ""

    def __post_init__(self) -> None:
        if self.name and not self.active:
            raise ModulePropertyError(
                f"NamedFlag carries name {self.name!r} but is inactive"
            )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"active": self.active}
        if self.name:
            out["name"] = self.name
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NamedFlag":
        return cls(active=bool(data.get("active", False)), name=str(data.get("name", "")))


# Output-only flags deliberately excluded from authoring (the audit list):
#   * ``element_from_detail`` — cwapi3d reports "this element was produced by a
#     detail calculation". It is read-only state, not an authoring choice, so it
#     has no field here and is never written by the seam.
_GROUPED = {
    "distribute_in_axis": Distribution,
    "distribute_perpendicular": Distribution,
    "cutting_element": CuttingElement,
    "unique_layername": NamedFlag,
    "keep_in_center_of_layer_current_wall": NamedFlag,
    "keep_in_center_of_layer_neighbour_wall": NamedFlag,
}


@dataclass(frozen=True, slots=True)
class ModuleProperties:
    """The full, serializable element-module property bag for one member.

    Independent boolean flags sit alongside the grouped triads
    (:class:`Distribution`, :class:`CuttingElement`, :class:`NamedFlag`).
    ``__post_init__`` rejects the cross-field contradictions cadwork would also
    reject. Authoring is by ordinary keyword construction; ``with_(...)`` returns
    an edited copy without mutating the frozen original.
    """

    # ---- independent stretch / move flags ----
    stretch_with_top_of_wall: bool = False
    stretch_with_bottom_of_wall: bool = False
    move_with_top_of_wall: bool = False
    move_with_bottom_of_wall: bool = False
    # ---- independent behaviour flags ----
    auxiliary: bool = False
    not_cut_with_cutting_element: bool = False
    solder_in_axis_direction: bool = False
    no_collision_control: bool = False
    no_inside_control: bool = False
    use_for_detail_coordinate_system: bool = False
    # ---- grouped parametric fields ----
    distribute_in_axis: Distribution = Distribution()
    distribute_perpendicular: Distribution = Distribution()
    cutting_element: CuttingElement = CuttingElement()
    unique_layername: NamedFlag = NamedFlag()
    keep_in_center_of_layer_current_wall: NamedFlag = NamedFlag()
    keep_in_center_of_layer_neighbour_wall: NamedFlag = NamedFlag()

    def __post_init__(self) -> None:
        if self.cutting_element.active and self.not_cut_with_cutting_element:
            raise ModulePropertyError(
                "a member cannot be a cutting_element and also "
                "not_cut_with_cutting_element"
            )

    def with_(self, **changes: Any) -> "ModuleProperties":
        """Return a copy with ``changes`` applied (frozen-safe edit)."""
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        """Sparse encoding: only fields that differ from the default appear."""
        default = ModuleProperties()
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value == getattr(default, f.name):
                continue
            if f.name in _GROUPED:
                out[f.name] = value.to_dict()
            else:
                out[f.name] = value
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModuleProperties":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ModulePropertyError(
                f"unknown ModuleProperties field(s): {sorted(unknown)}"
            )
        kwargs: dict[str, Any] = {}
        for name, value in data.items():
            grouped_cls = _GROUPED.get(name)
            kwargs[name] = grouped_cls.from_dict(value) if grouped_cls else value
        return cls(**kwargs)
