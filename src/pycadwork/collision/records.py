"""Collision output — the frozen result DTOs of the collision scan.

A :class:`Clash` is one relationship found between an unordered pair of
elements; a :class:`CollisionReport` is the whole result of a
:func:`~pycadwork.collision.check_collisions` pass. Like the rule report
(:class:`~pycadwork.rules.records.RuleReport`) they are frozen, slotted, and
carry only plain scalars plus tuples — safe to sort, hash into sets, and
serialize, and equality-comparable so the same scan over the same model
produces an equal report.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum


class CollisionKind(IntEnum):
    """What kind of relationship a :class:`Clash` records. Ordered least-to-worst.

    The ordering (``NEAR_MISS < CLEARANCE < CONTACT < OVERLAP``) makes
    :class:`Clash` sort with the most severe finding last and lets a caller
    filter with a single ``>=`` comparison, mirroring
    :class:`~pycadwork.rules.severity.Severity`.
    """

    #: Solids do not touch but lie within the search margin — "should touch
    #: but don't": the bounding-box-extension finder.
    NEAR_MISS = 10
    #: Solids are apart by no more than a requested clearance threshold.
    CLEARANCE = 15
    #: Solids touch (flush faces) without interpenetrating.
    CONTACT = 20
    #: Solids interpenetrate — the classic clash-detection error.
    OVERLAP = 30


@dataclass(frozen=True, slots=True, order=True)
class Clash:
    """One relationship between an unordered pair of elements.

    ``first_id`` / ``second_id`` are the unwrapped ints with
    ``first_id < second_id``, so a pair is recorded once regardless of which
    element the scan started from. ``distance`` is ``0.0`` for
    :attr:`~CollisionKind.CONTACT` and :attr:`~CollisionKind.OVERLAP`, and the
    measured gap for :attr:`~CollisionKind.NEAR_MISS` /
    :attr:`~CollisionKind.CLEARANCE`.

    Field order is the sort order: kind first (so the worst clashes sort last),
    then the pair, then the distance — a report's clashes are deterministic
    regardless of the order elements were scanned in.
    """

    kind: CollisionKind
    first_id: int
    second_id: int
    distance: float


@dataclass(frozen=True, slots=True)
class CollisionReport:
    """The result of one :func:`~pycadwork.collision.check_collisions` pass.

    ``clashes`` is sorted and deterministic. ``checked`` counts the elements
    scanned; ``pairs_tested`` counts the candidate pairs that survived the
    spatial-index broad-phase and reached a narrow-phase test.
    """

    clashes: tuple[Clash, ...] = ()
    checked: int = 0
    pairs_tested: int = 0

    @property
    def ok(self) -> bool:
        """True when no :attr:`~CollisionKind.OVERLAP` clash was found.

        Contacts, near-misses and clearances do not break ``ok`` — it is the
        clean CI gate (``assert check_collisions(...).ok``) for "nothing
        interpenetrates" while the advisory findings still surface in
        :attr:`clashes`.
        """
        return not any(c.kind is CollisionKind.OVERLAP for c in self.clashes)

    def by_kind(self) -> dict[CollisionKind, tuple[Clash, ...]]:
        """Group the clashes by kind, each list in report order."""
        grouped: dict[CollisionKind, list[Clash]] = defaultdict(list)
        for clash in self.clashes:
            grouped[clash.kind].append(clash)
        return {kind: tuple(items) for kind, items in grouped.items()}

    def count(self, kind: CollisionKind | None = None) -> int:
        """Total clashes, or only those of ``kind`` when given."""
        if kind is None:
            return len(self.clashes)
        return sum(1 for c in self.clashes if c.kind is kind)
