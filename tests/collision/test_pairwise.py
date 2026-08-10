"""Pairwise predicates: overlaps / touches / clearance / is_near_miss.

Beam boxes (width=height=10, running along +X):
    a       = [0, 100]
    flush   = [100, 200]   touches a's far end
    overlap = [50, 150]    interpenetrates a on [50, 100]
    gapped  = [105, 205]   5-unit gap from a
    far     = [1000, 1100] nowhere near a
"""

from __future__ import annotations

from pycadwork.collision import Backend, clearance, is_near_miss, overlaps, touches

from tests.collision._helpers import beam

# ---- SOLID backend (default) ----


def test_solid_overlaps_only_for_interpenetration():
    a = beam(0, 0, 0, 100)
    assert overlaps(a, beam(50, 0, 0, 100)) is True
    assert overlaps(a, beam(100, 0, 0, 100)) is False  # flush contact, not overlap
    assert overlaps(a, beam(105, 0, 0, 100)) is False  # gap


def test_solid_touches_includes_flush_and_overlap():
    a = beam(0, 0, 0, 100)
    assert touches(a, beam(100, 0, 0, 100)) is True  # flush
    assert touches(a, beam(50, 0, 0, 100)) is True  # overlap counts as contact
    assert touches(a, beam(105, 0, 0, 100)) is False  # gap


def test_solid_clearance_is_the_gap():
    a = beam(0, 0, 0, 100)
    assert clearance(a, beam(105, 0, 0, 100)) == 5.0
    assert clearance(a, beam(100, 0, 0, 100)) == 0.0  # touching
    assert clearance(a, beam(1000, 0, 0, 100)) == 900.0


def test_solid_near_miss_is_gap_within_margin_and_not_touching():
    a = beam(0, 0, 0, 100)
    gapped = beam(105, 0, 0, 100)
    assert is_near_miss(a, gapped, margin=10.0) is True
    assert is_near_miss(a, gapped, margin=2.0) is False  # gap exceeds margin
    assert is_near_miss(a, beam(100, 0, 0, 100), margin=10.0) is False  # touching


# ---- GEOMETRY backend (offline OBB / AABB approximation) ----


def test_geometry_overlaps_reports_any_connection():
    a = beam(0, 0, 0, 100)
    # Boxes can't separate overlap from contact: a flush pair reads as overlap.
    assert overlaps(a, beam(100, 0, 0, 100), backend=Backend.GEOMETRY) is True
    assert overlaps(a, beam(105, 0, 0, 100), backend=Backend.GEOMETRY) is False


def test_geometry_touches_respects_tolerance():
    a = beam(0, 0, 0, 100)
    gapped = beam(105, 0, 0, 100)
    assert touches(a, gapped, tolerance=10.0, backend=Backend.GEOMETRY) is True
    assert touches(a, gapped, backend=Backend.GEOMETRY) is False  # default tiny tol


def test_geometry_clearance_uses_bounding_boxes():
    a = beam(0, 0, 0, 100)
    assert clearance(a, beam(105, 0, 0, 100), backend=Backend.GEOMETRY) == 5.0


def test_geometry_near_miss_matches_solid():
    a = beam(0, 0, 0, 100)
    gapped = beam(105, 0, 0, 100)
    assert is_near_miss(a, gapped, margin=10.0, backend=Backend.GEOMETRY) is True
    assert is_near_miss(a, gapped, margin=2.0, backend=Backend.GEOMETRY) is False
