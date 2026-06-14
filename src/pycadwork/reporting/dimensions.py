"""Grouping dimensions — composable axes for the report functions.

A :class:`Dimension` is one grouping axis: a ``label`` (the column header) and
a ``key_of`` function mapping an element to its bucket label via the
:class:`~pycadwork.reporting.index.SnapshotIndex`. Reports take a *sequence*
of dimensions and group by the tuple of their keys, so axes compose freely —
``dimensions=(by_storey(), by_material())`` buckets per storey *and* material
with no hardcoded per-storey-per-material variant anywhere.

The ``by_*`` factories are module-level free functions, like the package's
``discover_*`` APIs. A custom axis is one ``Dimension(label, fn)`` away —
e.g. over an indexed user attribute — without touching this module.

Every key function returns ``""`` for an element the axis cannot place
(no attribute satellite, no storey assignment, no cover sharing its key), so
unplaceable elements collect in one visible empty-labelled bucket instead of
being dropped.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pycadwork.persistence._ids import ElementId
from pycadwork.reporting.index import COVER_LINKS, SnapshotIndex


@dataclass(frozen=True, slots=True)
class Dimension:
    """One grouping axis: a column label plus an element → bucket-label function."""

    label: str
    key_of: Callable[[SnapshotIndex, ElementId], str]


def by_material() -> Dimension:
    """Group by the element's material name."""

    def key(index: SnapshotIndex, element_id: ElementId) -> str:
        attribute = index.attribute(element_id)
        return attribute.material_name if attribute else ""

    return Dimension("material", key)


def by_group() -> Dimension:
    """Group by the element's ``group`` attribute."""

    def key(index: SnapshotIndex, element_id: ElementId) -> str:
        attribute = index.attribute(element_id)
        return attribute.group_name if attribute else ""

    return Dimension("group", key)


def by_subgroup() -> Dimension:
    """Group by the element's ``subgroup`` attribute."""

    def key(index: SnapshotIndex, element_id: ElementId) -> str:
        attribute = index.attribute(element_id)
        return attribute.subgroup if attribute else ""

    return Dimension("subgroup", key)


def by_storey(separator: str = "/") -> Dimension:
    """Group by the element's storey assignment, as ``"<building><sep><storey>"``."""

    def key(index: SnapshotIndex, element_id: ElementId) -> str:
        assignment = index.assignment(element_id)
        if assignment is None:
            return ""
        return f"{assignment.building_name}{separator}{assignment.storey_name}"

    return Dimension("storey", key)


def by_cover(link: str = "group") -> Dimension:
    """Group by the owning cover (wall/slab/roof), linked through ``link``.

    Cover membership is a shared grouping value, and the snapshot does not
    record whether the project links by ``group`` or ``subgroup`` — pass the
    field that matches the project setting. Elements whose key matches no
    cover parent land in the ``""`` bucket.
    """
    if link not in COVER_LINKS:
        raise ValueError(f"link must be one of {COVER_LINKS}, got {link!r}")

    def key(index: SnapshotIndex, element_id: ElementId) -> str:
        attribute = index.attribute(element_id)
        if attribute is None:
            return ""
        own_key = attribute.group_name if link == "group" else attribute.subgroup
        return index.cover_label_by_link_key(link).get(own_key, "")

    return Dimension("cover", key)
