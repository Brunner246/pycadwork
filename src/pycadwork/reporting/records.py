"""Report rows — the frozen output DTOs of the reporting functions.

Each row is an aggregation result, not a model object: a :class:`PartRow` is
one line of a cutting list (every element sharing the same part identity,
collapsed to a count), a :class:`MaterialTotalRow` is one line of a material
summary. Like the persistence records they are frozen, slotted, and carry only
plain scalars plus tuples — safe to sort, hash into sets, and serialize.

``group`` holds one label per composed grouping :class:`~pycadwork.reporting.dimensions.Dimension`,
in the order the dimensions were passed to the report; it is the empty tuple
when no dimensions were requested. ``element_ids`` keeps the sorted ids of
every element aggregated into the row, so each line traces back to the model
or the SQL store.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PartRow:
    """One cutting-list line — identical parts collapsed to a count.

    Part identity is ``(element_type, material_name, name, length, width,
    height)`` with the dimensions rounded to the report's ``precision``; the
    name is part of the identity on purpose — two same-sized parts named
    differently are different lines, not one line with an arbitrary name.
    """

    group: tuple[str, ...]
    element_type: str
    name: str
    material_name: str
    length: float
    width: float
    height: float
    count: int
    total_volume: float
    total_weight: float
    element_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MaterialTotalRow:
    """One material-summary line — totals over every part carrying the material."""

    group: tuple[str, ...]
    material_name: str
    count: int
    total_volume: float
    total_weight: float
