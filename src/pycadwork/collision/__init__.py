"""pycadwork.collision — clash / contact / near-miss / clearance checks.

Where :mod:`pycadwork.connectivity` answers the single geometric question "do
these touch?", this module audits a model for several collision relationships
at once and reports them as frozen value objects, the sibling of
:mod:`pycadwork.rules`::

    from pycadwork.collision import check_collisions, CollisionKind, highlight_clashes

    report = check_collisions(
        kinds=[CollisionKind.OVERLAP, CollisionKind.NEAR_MISS],
        margin=5.0,                       # "should touch but don't" within 5 mm
    )
    assert report.ok                      # no interpenetration
    highlight_clashes(report, kinds=[CollisionKind.OVERLAP])

The scan prunes far-apart pairs with a spatial index, so passing a large
element set only ever runs the exact test on spatially-near candidates. The
default :attr:`Backend.SOLID` asks cadwork for the exact answer; pass
:attr:`Backend.GEOMETRY` for an offline OBB / bounding-box approximation.
"""

from __future__ import annotations

from pycadwork.collision.csv_export import write_clashes_csv
from pycadwork.collision.engine import (
    DEFAULT_TOUCH_TOLERANCE,
    Backend,
    check_collisions,
    clearance,
    is_near_miss,
    overlaps,
    touches,
)
from pycadwork.collision.highlight import DEFAULT_CLASH_COLOR, highlight_clashes
from pycadwork.collision.records import Clash, CollisionKind, CollisionReport

__all__ = [
    "DEFAULT_CLASH_COLOR",
    "DEFAULT_TOUCH_TOLERANCE",
    "Backend",
    "Clash",
    "CollisionKind",
    "CollisionReport",
    "check_collisions",
    "clearance",
    "highlight_clashes",
    "is_near_miss",
    "overlaps",
    "touches",
    "write_clashes_csv",
]
