"""The report functions — cutting list and material totals over one snapshot.

Both reports are pure functions over a
:class:`~pycadwork.persistence.records.ModelSnapshot`, so the same call serves
both data sources: the live model via
:meth:`pycadwork.persistence.ModelReader.read` and a pulled SQL store via
:func:`pycadwork.persistence.load_snapshot`. Nothing here touches cadwork or
SQL.

Which elements count as *parts* is the ``part_types`` filter over the
snapshot's ``element_type`` tokens. The default covers the path-anchored stock
(beams, plates, MEP runs) and naturally excludes cover parents (``wall`` /
``slab`` / ``roof`` tokens), containers, drillings, openings, and the other
non-stock types. Output ordering is deterministic — sorted on every key field
— regardless of the snapshot's internal order.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pycadwork.persistence._ids import ElementId
from pycadwork.persistence.records import ModelSnapshot
from pycadwork.reporting.dimensions import Dimension
from pycadwork.reporting.index import SnapshotIndex
from pycadwork.reporting.records import MaterialTotalRow, PartRow

#: Element-type tokens counted as parts by default — the path-anchored stock.
DEFAULT_PART_TYPES: frozenset[str] = frozenset(
    {"beam", "plate", "circularmep", "rectangularmep"}
)


@dataclass(frozen=True, slots=True)
class _PartKey:
    """The part identity — what makes two elements the *same* cutting-list line."""

    element_type: str
    material_name: str
    name: str
    length: float
    width: float
    height: float


class _Accumulator:
    __slots__ = ("count", "volume", "weight", "element_ids")

    def __init__(self) -> None:
        self.count = 0
        self.volume = 0.0
        self.weight = 0.0
        self.element_ids: list[int] = []

    def add(self, element_id: ElementId, volume: float, weight: float) -> None:
        self.count += 1
        self.volume += volume
        self.weight += weight
        self.element_ids.append(int(element_id))


def cutting_list(
    snapshot: ModelSnapshot,
    *,
    dimensions: Sequence[Dimension] = (),
    part_types: frozenset[str] = DEFAULT_PART_TYPES,
    precision: int = 1,
) -> list[PartRow]:
    """Aggregate the snapshot's parts into one cutting list.

    Elements sharing the same part identity — type, material, name, and the
    dimensions rounded to ``precision`` decimals — collapse into one
    :class:`PartRow` with a count, summed volume/weight, and the sorted ids of
    every aggregated element. ``dimensions`` prepend composable grouping axes:
    the same part in two storeys is two rows when grouped ``by_storey()``.
    """
    index = SnapshotIndex(snapshot)
    buckets: dict[tuple[tuple[str, ...], _PartKey], _Accumulator] = {}

    for element in snapshot.elements:
        if element.element_type not in part_types:
            continue
        attribute = index.attribute(element.id)
        geometry = index.geometry(element.id)
        group = tuple(d.key_of(index, element.id) for d in dimensions)
        key = _PartKey(
            element_type=element.element_type,
            material_name=attribute.material_name if attribute else "",
            name=attribute.name if attribute else "",
            length=round(geometry.length, precision) if geometry else 0.0,
            width=round(geometry.width, precision) if geometry else 0.0,
            height=round(geometry.height, precision) if geometry else 0.0,
        )
        bucket = buckets.setdefault((group, key), _Accumulator())
        bucket.add(
            element.id,
            geometry.volume if geometry else 0.0,
            geometry.weight if geometry else 0.0,
        )

    rows = [
        PartRow(
            group=group,
            element_type=key.element_type,
            name=key.name,
            material_name=key.material_name,
            length=key.length,
            width=key.width,
            height=key.height,
            count=bucket.count,
            total_volume=bucket.volume,
            total_weight=bucket.weight,
            element_ids=tuple(sorted(bucket.element_ids)),
        )
        for (group, key), bucket in buckets.items()
    ]
    rows.sort(
        key=lambda r: (
            r.group,
            r.material_name,
            r.element_type,
            r.name,
            r.length,
            r.width,
            r.height,
        )
    )
    return rows


def material_totals(
    snapshot: ModelSnapshot,
    *,
    dimensions: Sequence[Dimension] = (),
    part_types: frozenset[str] = DEFAULT_PART_TYPES,
) -> list[MaterialTotalRow]:
    """Total count, volume, and weight per material over the snapshot's parts.

    The same pass as :func:`cutting_list`, keyed by ``(group, material)``
    only — part dimensions and names do not split rows here.
    """
    index = SnapshotIndex(snapshot)
    buckets: dict[tuple[tuple[str, ...], str], _Accumulator] = {}

    for element in snapshot.elements:
        if element.element_type not in part_types:
            continue
        attribute = index.attribute(element.id)
        geometry = index.geometry(element.id)
        group = tuple(d.key_of(index, element.id) for d in dimensions)
        material = attribute.material_name if attribute else ""
        bucket = buckets.setdefault((group, material), _Accumulator())
        bucket.add(
            element.id,
            geometry.volume if geometry else 0.0,
            geometry.weight if geometry else 0.0,
        )

    rows = [
        MaterialTotalRow(
            group=group,
            material_name=material,
            count=bucket.count,
            total_volume=bucket.volume,
            total_weight=bucket.weight,
        )
        for (group, material), bucket in buckets.items()
    ]
    rows.sort(key=lambda r: (r.group, r.material_name))
    return rows
