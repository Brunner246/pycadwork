"""highlight_clashes recolours exactly the elements taking part in a clash."""

from __future__ import annotations

from pycadwork.cadwork_adapter import cadwork
from pycadwork.collision import CollisionKind, check_collisions, highlight_clashes

from tests.collision._helpers import beam


def test_highlight_recolours_the_clashing_elements():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)  # overlaps a
    report = check_collisions([a, b], kinds=[CollisionKind.OVERLAP])

    affected = highlight_clashes(report, color_id=5)

    assert set(affected) == {a.id, b.id}
    assert cadwork.visualization.get_color(a.id) == 5
    assert cadwork.visualization.get_color(b.id) == 5


def test_highlight_writes_a_comment_when_given():
    a = beam(0, 0, 0, 100)
    b = beam(50, 0, 0, 100)
    report = check_collisions([a, b], kinds=[CollisionKind.OVERLAP])

    highlight_clashes(report, color_id=5, comment="CLASH")

    assert cadwork.attributes.get_comment(a.id) == "CLASH"
    assert cadwork.attributes.get_comment(b.id) == "CLASH"


def test_highlight_filters_by_kind():
    a = beam(0, 0, 0, 100)
    overlap = beam(50, 0, 0, 100)  # OVERLAP with a on the X axis
    gapped = beam(0, 15, 0, 100)  # 5-unit Y gap from a — NEAR_MISS, no overlap
    report = check_collisions(
        [a, overlap, gapped],
        kinds=[CollisionKind.OVERLAP, CollisionKind.NEAR_MISS],
        margin=10.0,
    )

    # Only highlight the overlap; the near-miss element keeps its default colour.
    affected = highlight_clashes(report, color_id=5, kinds=[CollisionKind.OVERLAP])

    assert set(affected) == {a.id, overlap.id}
    assert gapped.id not in affected


def test_highlight_no_matching_clashes_is_a_noop():
    a = beam(0, 0, 0, 100)
    b = beam(100, 0, 0, 100)  # flush contact only
    report = check_collisions([a, b], kinds=[CollisionKind.CONTACT])

    affected = highlight_clashes(report, color_id=5, kinds=[CollisionKind.OVERLAP])

    assert affected == []
