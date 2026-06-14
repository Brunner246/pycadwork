"""Realize a :class:`DetailDefinition` into live cadwork elements.

``build_detail`` is the end-to-end pipeline: create the framing members, label
them, anchor them under a host cover, push each member's element-module
properties, optionally point cadwork at the detail directory, and run the
calculation. Every step goes through the version-isolation seam
(:data:`pycadwork.cadwork_adapter.cadwork`); nothing here imports cwapi3d.

The step order is deliberate and guards two real hazards (see the inline
comments): a cover's *children* are the elements sharing its grouping value, not
a container — so the host must share that key with the members **before** the
calculation reads them, and the host's cover *kind* must be flagged before the
grouping is written.

A note on the host cover: in production a detail is calculated inside a wall the
modeller already drew. To keep ``build_detail`` self-contained (and runnable
against the fake with no UI), it fabricates a placeholder host cover flagged with
the definition's ``cover_kind`` and groups the members onto it. Pass an existing
cover to :func:`run_calculation` directly when driving a real model.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId, GroupingMode
from pycadwork.detail.definition import DetailDefinition, MemberSpec
from pycadwork.detail.properties import ModuleProperties
from pycadwork.detail.roles import resolve
from pycadwork.element.base import Element
from pycadwork.element.beam import Beam
from pycadwork.element.cover.aggregate import Aggregate
from pycadwork.element.cover.group import Group
from pycadwork.element.factory import from_id
from pycadwork.element.plate import Plate
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.specs import AxisPoints, RectSection
from pycadwork.utility import DisplayRefreshScope

#: Prefix for the grouping key a fabricated host cover uses.
_HOST_GROUP_PREFIX = "detail"


@dataclass(frozen=True, slots=True)
class DetailResult:
    """The outcome of :func:`build_detail`."""

    member_ids: tuple[ElementId, ...]
    cover_id: ElementId | None
    calculated: bool
    detail_path: str | None = None


def _create_member(spec: MemberSpec) -> Element:
    """Create one beam/panel from its spec via the existing creation classmethods."""
    if spec.kind == "beam":
        assert isinstance(spec.section, RectSection)
        if spec.points is not None:
            return Beam.create_rectangular(spec.section, spec.points)
        assert spec.frame is not None
        return Beam.create_rectangular_from_vectors(spec.section, spec.frame)
    # panel
    if spec.points is not None:
        return Plate.create_rectangular(spec.section, spec.points)  # type: ignore[arg-type]
    assert spec.frame is not None
    return Plate.create_rectangular_from_vectors(spec.section, spec.frame)  # type: ignore[arg-type]


def _apply_member_attributes(spec: MemberSpec, element: Element) -> None:
    if spec.name is not None:
        element.attrs.name = spec.name
    if spec.material is not None:
        element.attrs.material_name = spec.material
    if spec.group is not None:
        element.attrs.group = spec.group


def _set_group_key(eids: list[ElementId], key: str) -> None:
    if Group.active_mode() is GroupingMode.GROUP:
        cadwork.attributes.set_group(eids, key)
    else:
        cadwork.attributes.set_subgroup(eids, key)


def _create_host_cover(definition: DetailDefinition) -> Aggregate:
    """Fabricate a placeholder cover element flagged with the definition's kind."""
    host = Beam.create_rectangular(
        RectSection(100.0, 100.0),
        AxisPoints(Point3D(0.0, 0.0, 0.0), Point3D(1000.0, 0.0, 0.0), Point3D(0.0, 0.0, 1.0)),
    )
    # Hazard 1: flag the cover *kind* before anything reads the element type.
    cadwork.attributes.set_cover_kind([host.id], definition.cover_kind)
    # Hazard 2: give the host its grouping key now, so add_children can copy it.
    _set_group_key([host.id], f"{_HOST_GROUP_PREFIX}::{definition.name}")
    cover = from_id(host.id)
    assert isinstance(cover, Aggregate)
    return cover


def _batch_properties(
    pairs: list[tuple[MemberSpec, Element]],
) -> dict[ModuleProperties, list[ElementId]]:
    """Bucket member ids by their resolved (and thus identical) properties value."""
    buckets: dict[ModuleProperties, list[ElementId]] = {}
    for spec, element in pairs:
        props = resolve(spec.role, spec.properties)
        buckets.setdefault(props, []).append(element.id)
    return buckets


def build_detail(
    definition: DetailDefinition,
    *,
    detail_path: str | None = None,
    calculate: bool = True,
    silent: bool = True,
) -> DetailResult:
    """Create, group, configure, and (optionally) calculate a detail definition.

    Returns a :class:`DetailResult` recording the created member ids, the host
    cover id (``None`` if the definition has no members), and whether the
    element-module calculation actually ran. ``detail_path`` — when given — is set
    once via the seam (project-global state, never auto-stomped). ``silent``
    defaults to ``True`` so scripted realizes never block on a cadwork dialog.
    """
    with DisplayRefreshScope() as scope:
        # 1. Create every member.
        pairs: list[tuple[MemberSpec, Element]] = [
            (spec, _create_member(spec)) for spec in definition.members
        ]
        members = [element for _, element in pairs]
        scope.track(members)

        cover: Aggregate | None = None
        if members:
            # 2. Per-member attributes (name/material/group) before grouping.
            for spec, element in pairs:
                _apply_member_attributes(spec, element)

            # 3. Host cover: kind is flagged, then members are grouped onto it.
            cover = _create_host_cover(definition)
            scope.track(cover)
            cover.add_children(members)

            # 4. Element-module properties, batched one call per distinct value.
            for props, eids in _batch_properties(pairs).items():
                cadwork.module.apply_properties(eids, props)

        # 5. Detail path: opt-in, project-global — set once if supplied.
        if detail_path is not None:
            cadwork.module.set_detail_path(detail_path)

        # 6. Calculation last; skipped on an empty cover or calculate=False.
        calculated = False
        if calculate and cover is not None and members:
            run_calculation([cover], silent=silent)
            calculated = True

    return DetailResult(
        member_ids=tuple(e.id for e in members),
        cover_id=cover.id if cover is not None else None,
        calculated=calculated,
        detail_path=detail_path,
    )


def _cover_ids(covers: Element | Iterable[Element]) -> list[ElementId]:
    if isinstance(covers, Element):
        return [covers.id]
    return [c.id for c in covers]


def run_calculation(
    covers: Element | Iterable[Element], *, silent: bool = False
) -> None:
    """Run the element-module calculation over ``covers`` (a cover or iterable)."""
    ids = _cover_ids(covers)
    if not ids:
        return
    if silent:
        cadwork.module.start_calculation_silently(ids)
    else:
        cadwork.module.start_calculation(ids)


def set_detail_path(path: str) -> None:
    """Point cadwork at the directory holding detail definition files."""
    cadwork.module.set_detail_path(path)


def save_detail(definition: DetailDefinition, path: str) -> None:
    """Serialize ``definition`` to ``path`` as native-schema JSON."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(definition.to_dict(), fh, indent=2)
