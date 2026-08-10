"""Model scan: check_collisions over small, deterministically-placed beam sets."""

from __future__ import annotations

from pycadwork import Aggregate, from_id
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind
from pycadwork.collision import Backend, CollisionKind, check_collisions
from pycadwork.element import Element

from tests.collision._helpers import beam


def _as_cover(element: Element, kind: CoverKind) -> Aggregate:
    """Flag a beam as a cover and re-resolve it to the matching wrapper."""
    cadwork.attributes.set_cover_kind([element.id], kind)
    cover = from_id(element.id)
    assert isinstance(cover, Aggregate)
    return cover


def test_overlap_is_reported_and_breaks_ok():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)  # interpenetrates a
    report = check_collisions([a, b], kinds=[CollisionKind.OVERLAP])
    assert report.count(CollisionKind.OVERLAP) == 1
    assert report.ok is False
    clash = report.clashes[0]
    assert (clash.first_id, clash.second_id) == (min(a.id, b.id), max(a.id, b.id))
    assert clash.distance == 0.0


def test_flush_pair_is_contact_not_overlap():
    a = beam(0, 0, 0, 100)
    b = beam(100, 0, 0, 100)  # flush
    overlap = check_collisions([a, b], kinds=[CollisionKind.OVERLAP])
    assert overlap.clashes == ()
    assert overlap.ok is True
    contact = check_collisions([a, b], kinds=[CollisionKind.CONTACT])
    assert contact.count(CollisionKind.CONTACT) == 1


def test_near_miss_respects_margin():
    a = beam(0, 0, 0, 100)
    c = beam(105, 0, 0, 100)  # 5-unit gap
    wide = check_collisions([a, c], kinds=[CollisionKind.NEAR_MISS], margin=10.0)
    assert wide.count(CollisionKind.NEAR_MISS) == 1
    assert wide.clashes[0].distance == 5.0
    narrow = check_collisions([a, c], kinds=[CollisionKind.NEAR_MISS], margin=2.0)
    assert narrow.clashes == ()


def test_clearance_threshold_flags_close_pairs():
    a = beam(0, 0, 0, 100)
    c = beam(105, 0, 0, 100)  # gap 5
    report = check_collisions(
        [a, c], kinds=[CollisionKind.CLEARANCE], clearance_threshold=10.0
    )
    assert report.count(CollisionKind.CLEARANCE) == 1
    assert report.clashes[0].distance == 5.0


def test_far_elements_are_pruned_by_the_spatial_index():
    # Three elements would be three pairs under a naive O(n^2) scan; the far
    # beam must be pruned by the broad-phase so only the near pair is tested.
    a = beam(0, 0, 0, 100)
    overlap = beam(50, 0, 0, 100)
    far = beam(10_000, 0, 0, 100)
    report = check_collisions([a, overlap, far], kinds=[CollisionKind.OVERLAP])
    assert report.checked == 3
    assert report.pairs_tested == 1  # only (a, overlap) survived broad-phase
    assert report.count(CollisionKind.OVERLAP) == 1


def test_unordered_pairs_are_tested_once():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)
    report = check_collisions([a, b], kinds=[CollisionKind.OVERLAP])
    # (a, b) and (b, a) are the same pair — recorded once, tested once.
    assert report.pairs_tested == 1
    assert len(report.clashes) == 1


def test_among_scopes_the_candidate_universe():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)  # overlaps a
    on_top = beam(0, 0, 10, 100)  # also touches a, but excluded from `among`
    report = check_collisions([a], kinds=[CollisionKind.OVERLAP], among=[a, b])
    assert report.count(CollisionKind.OVERLAP) == 1
    assert on_top.id not in {report.clashes[0].first_id, report.clashes[0].second_id}


def test_default_scans_the_active_model():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)  # overlaps a
    _far = beam(10_000, 0, 0, 100)
    report = check_collisions(kinds=[CollisionKind.OVERLAP])
    assert report.checked == 3
    assert report.count(CollisionKind.OVERLAP) == 1
    clash = report.clashes[0]
    assert (clash.first_id, clash.second_id) == (min(a.id, b.id), max(a.id, b.id))


def test_geometry_backend_reports_connection_as_contact():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)  # interpenetrates
    report = check_collisions(
        [a, b], kinds=[CollisionKind.OVERLAP], backend=Backend.GEOMETRY
    )
    # Geometry can't assert interpenetration; the connection surfaces as CONTACT.
    assert report.count(CollisionKind.CONTACT) == 1
    assert report.count(CollisionKind.OVERLAP) == 0


def test_empty_kinds_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="kinds must not be empty"):
        check_collisions([beam(0, 0, 0, 100)], kinds=[])


def test_exclude_drops_a_type_from_the_scan():
    a = beam(0, 0, 0, 100)
    wall = _as_cover(beam(50, 0, 0, 100), CoverKind.FRAMED_WALL)  # overlaps a

    # Geometrically the wall still overlaps a — flagging it didn't move it.
    full = check_collisions([a, wall], kinds=[CollisionKind.OVERLAP])
    assert full.count(CollisionKind.OVERLAP) == 1

    pruned = check_collisions(
        [a, wall],
        kinds=[CollisionKind.OVERLAP],
        exclude=lambda e: isinstance(e, Aggregate),
    )
    assert pruned.clashes == ()
    assert pruned.checked == 1  # only `a` survived the exclusion


def test_exclude_by_cover_kind():
    a = beam(0, 0, 0, 100)  # row y=0
    solid = _as_cover(beam(50, 0, 0, 100), CoverKind.SOLID_WALL)  # overlaps a
    a2 = beam(0, 20, 0, 100)  # row y=20, clear of a
    framed = _as_cover(beam(50, 20, 0, 100), CoverKind.FRAMED_WALL)  # overlaps a2

    report = check_collisions(
        [a, solid, a2, framed],
        kinds=[CollisionKind.OVERLAP],
        exclude=lambda e: isinstance(e, Aggregate) and e.kind is CoverKind.SOLID_WALL,
    )

    # The solid wall is dropped; only the framed-wall overlap remains.
    assert report.count(CollisionKind.OVERLAP) == 1
    pair = {report.clashes[0].first_id, report.clashes[0].second_id}
    assert solid.id not in pair
    assert pair == {min(a2.id, framed.id), max(a2.id, framed.id)}
