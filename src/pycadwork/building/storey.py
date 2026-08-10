"""Pure, cadwork-free storey classification.

A :class:`StoreyStack` turns a set of storeys (each at an absolute Z elevation)
into a partition of the vertical axis: storey *i* owns the half-open interval
``[elev_i, elev_{i+1})`` and the topmost storey owns ``[elev_top, +inf)``. Given
the vertical extent ``[z_lo, z_hi]`` of an element, :meth:`StoreyStack.classify`
picks the storey it mostly sits in (largest overlap — the >50% majority rule)
and reports whether the extent *spans* more than one storey (or falls below the
lowest floor), so callers can flag it for human review.

Nothing here touches cadwork; the whole algorithm is unit-testable as plain
geometry.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from pycadwork.building.names import StoreyName

# Tolerance for the "touches more than one interval" test: an extent that merely
# grazes a storey plane should not count as spanning.
_EPSILON = 1e-6


@dataclass(frozen=True, slots=True)
class Storey:
    """A storey identified by name, anchored at the absolute Z of its base plane."""

    name: StoreyName
    elevation: float


@dataclass(frozen=True, slots=True)
class StoreyClassification:
    """The storey to which an extent belongs, plus whether it straddles a plane."""

    storey: Storey
    spans: bool


class StoreyStack:
    """An elevation-sorted partition of the vertical axis into storeys."""

    __slots__ = ("_storeys", "_elevations")

    def __init__(self, storeys: Iterable[Storey]) -> None:
        ordered = sorted(storeys, key=lambda s: s.elevation)
        if not ordered:
            raise ValueError("StoreyStack requires at least one storey")
        self._storeys: tuple[Storey, ...] = tuple(ordered)
        self._elevations: tuple[float, ...] = tuple(s.elevation for s in ordered)

    # ---- accessors ----

    @property
    def storeys(self) -> tuple[Storey, ...]:
        """The storeys, ascending by elevation."""
        return self._storeys

    def __len__(self) -> int:
        return len(self._storeys)

    # ---- classification ----

    def classify(self, z_lo: float, z_hi: float) -> StoreyClassification:
        """Assign the extent ``[z_lo, z_hi]`` to its majority storey.

        ``spans`` is ``True`` when the extent has positive overlap with more
        than one storey interval, or extends below the lowest floor. A
        degenerate extent (``z_hi == z_lo``, e.g. a node) is assigned to the
        interval containing it and never marked as spanning.
        """
        if z_hi < z_lo:
            z_lo, z_hi = z_hi, z_lo

        if z_hi - z_lo <= _EPSILON:
            return StoreyClassification(self._containing(z_lo), spans=False)

        overlaps = [
            self._overlap(storey_index, z_lo, z_hi)
            for storey_index in range(len(self._storeys))
        ]
        best = max(range(len(self._storeys)), key=lambda i: overlaps[i])

        touched = sum(1 for o in overlaps if o > _EPSILON)
        below_lowest = z_lo < self._elevations[0] - _EPSILON
        spans = touched > 1 or below_lowest

        return StoreyClassification(self._storeys[best], spans=spans)

    # ---- internals ----

    def _ceiling(self, storey_index: int) -> float:
        """Top of a storey's interval; +inf for the topmost storey."""
        if storey_index + 1 < len(self._elevations):
            return self._elevations[storey_index + 1]
        return math.inf

    def _overlap(self, storey_index: int, z_lo: float, z_hi: float) -> float:
        floor = self._elevations[storey_index]
        ceiling = self._ceiling(storey_index)
        return max(0.0, min(z_hi, ceiling) - max(z_lo, floor))

    def _containing(self, z: float) -> Storey:
        """The storey whose interval contains ``z`` (storey 0 if below the lowest)."""
        idx = 0
        for i, floor in enumerate(self._elevations):
            if floor <= z:
                idx = i
            else:
                break
        return self._storeys[idx]
