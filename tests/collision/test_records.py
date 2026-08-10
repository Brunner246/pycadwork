"""The frozen result DTOs: CollisionKind, Clash, CollisionReport."""

from __future__ import annotations

import io

from pycadwork.collision import Clash, CollisionKind, CollisionReport, write_clashes_csv


def test_clashes_sort_by_kind_then_pair():
    overlap = Clash(CollisionKind.OVERLAP, 1, 2, 0.0)
    contact = Clash(CollisionKind.CONTACT, 3, 4, 0.0)
    near = Clash(CollisionKind.NEAR_MISS, 5, 6, 4.0)
    # Ascending kind: NEAR_MISS (10) < CONTACT (20) < OVERLAP (30).
    assert sorted([overlap, near, contact]) == [near, contact, overlap]


def test_ok_is_false_only_with_an_overlap():
    clean = CollisionReport((Clash(CollisionKind.CONTACT, 1, 2, 0.0),))
    assert clean.ok is True
    dirty = CollisionReport((Clash(CollisionKind.OVERLAP, 1, 2, 0.0),))
    assert dirty.ok is False


def test_by_kind_groups_in_report_order():
    clashes = (
        Clash(CollisionKind.OVERLAP, 1, 2, 0.0),
        Clash(CollisionKind.NEAR_MISS, 3, 4, 2.0),
        Clash(CollisionKind.OVERLAP, 5, 6, 0.0),
    )
    grouped = CollisionReport(clashes).by_kind()
    assert len(grouped[CollisionKind.OVERLAP]) == 2
    assert len(grouped[CollisionKind.NEAR_MISS]) == 1


def test_count_total_and_by_kind():
    clashes = (
        Clash(CollisionKind.OVERLAP, 1, 2, 0.0),
        Clash(CollisionKind.CONTACT, 3, 4, 0.0),
    )
    report = CollisionReport(clashes)
    assert report.count() == 2
    assert report.count(CollisionKind.OVERLAP) == 1
    assert report.count(CollisionKind.NEAR_MISS) == 0


def test_csv_export_writes_one_row_per_clash_above_min_kind():
    report = CollisionReport(
        (
            Clash(CollisionKind.OVERLAP, 1, 2, 0.0),
            Clash(CollisionKind.NEAR_MISS, 3, 4, 4.5),
        )
    )
    stream = io.StringIO()
    write_clashes_csv(report, stream, min_kind=CollisionKind.CONTACT)
    lines = stream.getvalue().splitlines()
    assert lines[0] == "kind,first_id,second_id,distance"
    # NEAR_MISS is below CONTACT and is filtered out.
    assert lines == ["kind,first_id,second_id,distance", "OVERLAP,1,2,0.0"]
