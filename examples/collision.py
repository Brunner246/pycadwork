"""Collision checks — clash, contact, near-miss ("should touch but don't"), clearance.

Where ``connectivity`` answers the single question "do these touch?", this
module audits a model for several collision relationships at once and reports
them as frozen value objects (the sibling of ``rules``). The scan prunes
far-apart pairs with a spatial index, so only spatially-near candidates ever
reach the exact test. The default ``Backend.SOLID`` asks cadwork for the exact
answer on the real solids; ``Backend.GEOMETRY`` is an offline OBB / bounding-box
approximation.

    uv run python -m examples.collision
"""

from __future__ import annotations

import io

from pycadwork import (
    Aggregate,
    AxisPoints,
    Backend,
    Beam,
    CollisionKind,
    CoverKind,
    Point3D,
    RectSection,
    check_collisions,
    clearance,
    from_id,
    highlight_clashes,
    is_near_miss,
    overlaps,
    touches,
    write_clashes_csv,
)
from pycadwork.cadwork_adapter import cadwork


def _beam(x: float, y: float = 0.0, length: float = 100.0) -> Beam:
    """A 10x10 beam along +x spanning [x, x + length] at row ``y``."""
    return Beam.create_rectangular(
        RectSection(10.0, 10.0),
        AxisPoints(Point3D(x, y, 0), Point3D(x + length, y, 0), Point3D(x, y, 1)),
    )


def demo_overlap_clash() -> None:
    """`check_collisions` finds interpenetrating solids — the classic clash."""
    a = _beam(0)  # [0, 100]
    b = _beam(50)  # interpenetrates a on [50, 100]
    far = _beam(10_000)  # nowhere near either

    report = check_collisions([a, b, far], kinds=[CollisionKind.OVERLAP])
    print("ok (no overlaps)?", report.ok)  # False
    print("overlaps:", report.count(CollisionKind.OVERLAP))  # 1
    # The far beam was pruned by the spatial index: 3 elements, 1 pair tested.
    print("checked / pairs_tested:", report.checked, "/", report.pairs_tested)
    for clash in report.clashes:
        print(" ", clash.kind.name, clash.first_id, clash.second_id)


def demo_should_touch_but_dont() -> None:
    """Near-miss: elements within a margin that do NOT touch — a missing contact."""
    a = _beam(0)  # ends at x=100
    gapped = _beam(105)  # starts at x=105 -> a 5-unit gap

    found = check_collisions([a, gapped], kinds=[CollisionKind.NEAR_MISS], margin=10.0)
    print("near-misses within 10:", found.count(CollisionKind.NEAR_MISS))  # 1
    print("gap:", found.clashes[0].distance)  # 5.0

    tight = check_collisions([a, gapped], kinds=[CollisionKind.NEAR_MISS], margin=2.0)
    print("near-misses within 2:", tight.count(CollisionKind.NEAR_MISS))  # 0


def demo_clearance() -> None:
    """Clearance: flag every pair closer than a required minimum gap."""
    a = _beam(0)
    c = _beam(105)  # gap 5

    report = check_collisions(
        [a, c], kinds=[CollisionKind.CLEARANCE], clearance_threshold=10.0
    )
    print("too-close pairs:", report.count(CollisionKind.CLEARANCE))  # 1
    print("clearance:", report.clashes[0].distance)  # 5.0


def demo_pairwise_predicates() -> None:
    """The single-pair predicates behind the scan."""
    a = _beam(0)
    print("overlaps(a, [50,150])?", overlaps(a, _beam(50)))  # True
    print("touches(a, flush)?", touches(a, _beam(100)))  # True
    print("clearance(a, [105,205]) =", clearance(a, _beam(105)))  # 5.0
    print("is_near_miss(a, gap5, margin=10)?", is_near_miss(a, _beam(105), margin=10.0))


def demo_exclude_types() -> None:
    """Skip elements from the scan with an (element) -> bool predicate."""
    a = _beam(0)
    overlapping_wall = _beam(50)  # geometrically overlaps a
    # Flag the beam as a wall (setup the cadwork UI normally does), then re-wrap.
    cadwork.attributes.set_cover_kind([overlapping_wall.id], CoverKind.SOLID_WALL)
    wall = from_id(overlapping_wall.id)  # now an Aggregate (Wall)

    full = check_collisions([a, wall], kinds=[CollisionKind.OVERLAP])
    print("overlaps without exclusion:", full.count(CollisionKind.OVERLAP))  # 1

    # Exclude every cover (Wall / Slab / Roof all subclass Aggregate)...
    no_covers = check_collisions(
        [a, wall],
        kinds=[CollisionKind.OVERLAP],
        exclude=lambda e: isinstance(e, Aggregate),
    )
    print("overlaps excluding aggregates:", no_covers.count(CollisionKind.OVERLAP))

    # ...or only a specific CoverKind, via the aggregate's `.kind`.
    no_solid = check_collisions(
        [a, wall],
        kinds=[CollisionKind.OVERLAP],
        exclude=lambda e: isinstance(e, Aggregate) and e.kind is CoverKind.SOLID_WALL,
    )
    print("overlaps excluding solid walls:", no_solid.count(CollisionKind.OVERLAP))


def demo_geometry_backend() -> None:
    """The offline backend needs no live kernel; overlap folds into contact."""
    a, b = _beam(0), _beam(50)  # interpenetrate
    report = check_collisions(
        [a, b], kinds=[CollisionKind.OVERLAP], backend=Backend.GEOMETRY
    )
    # Bounding boxes can't separate overlap from flush contact -> reported CONTACT.
    print("geometry kinds:", [c.kind.name for c in report.clashes])  # ['CONTACT']


def demo_highlight_and_csv() -> None:
    """Act on a report: recolour clashing elements, and export to CSV."""
    a, b = _beam(0), _beam(50)
    report = check_collisions([a, b], kinds=[CollisionKind.OVERLAP])

    affected = highlight_clashes(report, color_id=6, comment="CLASH")
    print("recoloured ids:", sorted(affected))

    stream = io.StringIO()
    write_clashes_csv(report, stream)  # kind, first_id, second_id, distance
    print(stream.getvalue().strip())


def run() -> None:
    """Run every collision demo in order."""
    demo_overlap_clash()
    demo_should_touch_but_dont()
    demo_clearance()
    demo_pairwise_predicates()
    demo_exclude_types()
    demo_geometry_backend()
    demo_highlight_and_csv()


if __name__ == "__main__":
    run()
