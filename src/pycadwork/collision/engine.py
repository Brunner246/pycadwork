"""Collision checks: pairwise predicates and the spatial-index model scan.

Two layers, mirroring :mod:`pycadwork.connectivity`:

* **Pairwise predicates** — :func:`overlaps`, :func:`touches`,
  :func:`clearance`, :func:`is_near_miss` decide one relationship for one pair.
* **Model scan** — :func:`check_collisions` walks an element set, prunes
  far-apart pairs with an :class:`~pycadwork.geometry.RTreeIndex3D` broad-phase,
  and runs a narrow-phase test only on the spatially-near survivors, returning a
  sorted :class:`~pycadwork.collision.records.CollisionReport`.

Two backends decide each relationship. :attr:`Backend.SOLID` (the default) asks
cadwork for the exact answer on the real solids, through the
:class:`~pycadwork.cadwork_adapter._collision.CollisionAdapter` seam.
:attr:`Backend.GEOMETRY` reuses :mod:`pycadwork.connectivity`'s tolerance-aware
OBB test and the bounding-box distance — no live kernel needed, but it cannot
tell a flush contact from a true interpenetration, so a connected pair is always
reported as :attr:`~pycadwork.collision.records.CollisionKind.CONTACT`.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable
from enum import Enum

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.collision.records import Clash, CollisionKind, CollisionReport
from pycadwork.connectivity.detection import active_elements
from pycadwork.connectivity.detection import connects as geometric_connects
from pycadwork.element import Element
from pycadwork.geometry import RTreeIndex3D
from pycadwork.value_types import Distance

#: Default gap treated as "touching": small enough to mean contact while
#: absorbing floating-point error. Used by the broad-phase and the geometry
#: backend; the solid backend answers contact exactly and ignores it.
DEFAULT_TOUCH_TOLERANCE = 1e-6


class Backend(Enum):
    """How a pair's relationship is computed (not *which* pairs are tested).

    The spatial broad-phase is identical for both backends; ``backend`` only
    changes the narrow-phase test applied to each surviving pair.
    """

    #: Exact cwapi3d queries on the real machined solids (after trims, mitres,
    #: drillings, CSG). Distinguishes interpenetration from flush contact and
    #: reports the true minimum distance — but needs a **live cadwork model**.
    SOLID = "solid"
    #: pycadwork's own OBB / AABB approximation. Needs no kernel, so it runs on a
    #: snapshot / in CI / in tests, but cannot separate overlap from contact and
    #: its distance is the (conservative, lower-bound) box gap.
    GEOMETRY = "geometry"
    #: Resolves to :attr:`SOLID`. The single documented switch point for a
    #: future per-situation heuristic.
    AUTO = "auto"


def _resolve(backend: Backend) -> Backend:
    return Backend.SOLID if backend is Backend.AUTO else backend


# ----------------------------------------------------------------------
# Pairwise predicates
# ----------------------------------------------------------------------


def overlaps(a: Element, b: Element, *, backend: Backend = Backend.AUTO) -> bool:
    """True if ``a`` and ``b`` interpenetrate (share interior volume).

    Under :attr:`Backend.GEOMETRY` true interpenetration is indistinguishable
    from flush contact, so this returns True for any connected pair.
    """
    if _resolve(backend) is Backend.GEOMETRY:
        return geometric_connects(a, b, DEFAULT_TOUCH_TOLERANCE)
    return cadwork.collision.are_in_collision(a.id, b.id)


def touches(
    a: Element,
    b: Element,
    *,
    tolerance: float = DEFAULT_TOUCH_TOLERANCE,
    backend: Backend = Backend.AUTO,
) -> bool:
    """True if ``a`` and ``b`` touch or overlap.

    ``tolerance`` widens the test for :attr:`Backend.GEOMETRY` (a gap up to
    ``tolerance`` still counts as touching); the exact solid backend answers on
    the real faces and ignores it.
    """
    if _resolve(backend) is Backend.GEOMETRY:
        return geometric_connects(a, b, tolerance)
    return cadwork.collision.are_in_contact(a.id, b.id)


def clearance(a: Element, b: Element, *, backend: Backend = Backend.AUTO) -> Distance:
    """The minimum distance between ``a`` and ``b`` (``0.0`` if they touch).

    :attr:`Backend.SOLID` measures between the real solids;
    :attr:`Backend.GEOMETRY` measures between their axis-aligned bounding boxes —
    since a box encloses its solid the box gap is never larger than the true
    gap, i.e. a conservative *lower* bound on the clearance.
    """
    if _resolve(backend) is Backend.GEOMETRY:
        return Distance(a.geometry.aabb.distance_to(b.geometry.aabb))
    return Distance(cadwork.collision.minimum_distance(a.id, b.id))


def is_near_miss(
    a: Element,
    b: Element,
    *,
    margin: float,
    touch_tolerance: float = DEFAULT_TOUCH_TOLERANCE,
    backend: Backend = Backend.AUTO,
) -> bool:
    """True if ``a`` and ``b`` are within ``margin`` but do **not** touch.

    The "should touch but don't" test: a positive gap no larger than ``margin``.
    Equivalent to growing one element by ``margin`` and finding it reaches the
    other, while the un-grown elements stay apart.
    """
    if _resolve(backend) is Backend.GEOMETRY:
        return geometric_connects(a, b, margin) and not geometric_connects(
            a, b, touch_tolerance
        )
    if cadwork.collision.are_in_contact(a.id, b.id):
        return False
    return cadwork.collision.minimum_distance(a.id, b.id) <= margin


# ----------------------------------------------------------------------
# Narrow-phase classifier (shared by the scan)
# ----------------------------------------------------------------------


def _clashes_for_pair(
    a: Element,
    b: Element,
    *,
    backend: Backend,
    kinds: frozenset[CollisionKind],
    margin: float,
    clearance_threshold: float | None,
    touch_tolerance: float,
) -> list[Clash]:
    """Every requested clash between one already-near pair, as ordered ids."""
    lo, hi = (int(a.id), int(b.id)) if a.id < b.id else (int(b.id), int(a.id))
    out: list[Clash] = []

    if backend is Backend.GEOMETRY:
        if geometric_connects(a, b, touch_tolerance):
            # Boxes cannot separate overlap from flush contact: report CONTACT,
            # and surface it for an OVERLAP request too (best the OBB test can do).
            if kinds & {CollisionKind.OVERLAP, CollisionKind.CONTACT}:
                out.append(Clash(CollisionKind.CONTACT, lo, hi, 0.0))
            return out
        gap = a.geometry.aabb.distance_to(b.geometry.aabb)
    else:
        if cadwork.collision.are_in_collision(a.id, b.id):
            if CollisionKind.OVERLAP in kinds:
                out.append(Clash(CollisionKind.OVERLAP, lo, hi, 0.0))
            return out
        if cadwork.collision.are_in_contact(a.id, b.id):
            if CollisionKind.CONTACT in kinds:
                out.append(Clash(CollisionKind.CONTACT, lo, hi, 0.0))
            return out
        gap = cadwork.collision.minimum_distance(a.id, b.id)

    # Apart in either backend: the distance-based checks are independent.
    if CollisionKind.NEAR_MISS in kinds and gap <= margin:
        out.append(Clash(CollisionKind.NEAR_MISS, lo, hi, gap))
    if (
        CollisionKind.CLEARANCE in kinds
        and clearance_threshold is not None
        and gap <= clearance_threshold
    ):
        out.append(Clash(CollisionKind.CLEARANCE, lo, hi, gap))
    return out


def _broad_phase_reach(
    kinds: frozenset[CollisionKind],
    *,
    margin: float,
    clearance_threshold: float | None,
    touch_tolerance: float,
) -> float:
    """How far to grow an element's box so no qualifying partner is pruned."""
    reach = touch_tolerance
    if CollisionKind.NEAR_MISS in kinds:
        reach = max(reach, margin)
    if CollisionKind.CLEARANCE in kinds and clearance_threshold is not None:
        reach = max(reach, clearance_threshold)
    return reach


# ----------------------------------------------------------------------
# Model scan
# ----------------------------------------------------------------------


def check_collisions(
    elements: Iterable[Element] | None = None,
    *,
    kinds: Collection[CollisionKind] = (CollisionKind.OVERLAP,),
    among: Iterable[Element] | None = None,
    margin: float = 10.0,
    clearance_threshold: float | None = None,
    touch_tolerance: float = DEFAULT_TOUCH_TOLERANCE,
    backend: Backend = Backend.AUTO,
    exclude: Callable[[Element], bool] | None = None,
) -> CollisionReport:
    """Scan ``elements`` for the requested collision ``kinds`` and report them.

    ``elements`` is the focus set (defaults to the active identifiable model);
    ``among`` is the universe each focus element is tested against (defaults to
    the focus set itself, i.e. the set against itself). An
    :class:`~pycadwork.geometry.RTreeIndex3D` over ``among`` prunes far-apart
    pairs first: only elements whose box — grown by the largest relevant
    distance (``margin`` for near-miss, ``clearance_threshold`` for clearance,
    else ``touch_tolerance``) — reaches a focus element reach the narrow-phase
    test, so a distant element is never compared. Each unordered pair is tested
    once.

    ``exclude`` drops elements from the scan entirely — an excluded element is
    neither a subject nor a partner. It is an ``(element) -> bool`` predicate, so
    a type or property filters cleanly; e.g. ``exclude=lambda e: isinstance(e,
    Aggregate)`` skips every cover, and ``exclude=lambda e: isinstance(e,
    Aggregate) and e.kind is CoverKind.SOLID_WALL`` skips only solid walls.

    ``margin`` bounds the near-miss search ("should touch but don't");
    ``clearance_threshold`` (required for :attr:`~CollisionKind.CLEARANCE`)
    flags pairs closer than it.

    ``backend`` chooses how each surviving pair is decided — not which pairs are
    tested (the broad-phase above is identical either way). :attr:`Backend.SOLID`
    (the default, via :attr:`Backend.AUTO`) runs cadwork's exact solid kernel, so
    it separates :attr:`~CollisionKind.OVERLAP` from :attr:`~CollisionKind.CONTACT`
    and reports the true gap, but needs a **live cadwork model**.
    :attr:`Backend.GEOMETRY` decides from pycadwork's OBB / AABB instead: it needs
    no kernel (so it runs on a snapshot or in tests) but cannot tell
    interpenetration from flush contact — a connected pair is reported as
    :attr:`~CollisionKind.CONTACT` — and its distance is the conservative
    bounding-box gap. ``touch_tolerance`` is the gap treated as "touching": it
    only affects :attr:`Backend.GEOMETRY` (the solid backend answers contact
    exactly) and also sets the broad-phase reach when no distance kind is
    requested.

    The returned report is sorted and deterministic.
    """
    backend = _resolve(backend)
    requested = frozenset(kinds)
    if not requested:
        raise ValueError("check_collisions: kinds must not be empty")

    focus = list(elements) if elements is not None else active_elements()
    candidates = list(among) if among is not None else list(focus)
    if exclude is not None:
        focus = [e for e in focus if not exclude(e)]
        candidates = [c for c in candidates if not exclude(c)]
    by_id: dict[ElementId, Element] = {c.id: c for c in candidates}
    index = RTreeIndex3D((int(c.id), c.geometry.aabb) for c in candidates)

    reach = _broad_phase_reach(
        requested,
        margin=margin,
        clearance_threshold=clearance_threshold,
        touch_tolerance=touch_tolerance,
    )

    seen: set[tuple[int, int]] = set()
    clashes: list[Clash] = []
    pairs_tested = 0
    for element in focus:
        query = element.geometry.aabb.expanded(reach)
        for raw_id in index.intersection(query):
            candidate_id = ElementId(raw_id)
            if candidate_id == element.id:
                continue
            key = (
                (int(element.id), int(candidate_id))
                if element.id < candidate_id
                else (int(candidate_id), int(element.id))
            )
            if key in seen:
                continue
            seen.add(key)
            pairs_tested += 1
            clashes.extend(
                _clashes_for_pair(
                    element,
                    by_id[candidate_id],
                    backend=backend,
                    kinds=requested,
                    margin=margin,
                    clearance_threshold=clearance_threshold,
                    touch_tolerance=touch_tolerance,
                )
            )

    clashes.sort()
    return CollisionReport(
        clashes=tuple(clashes),
        checked=len(focus),
        pairs_tested=pairs_tested,
    )
