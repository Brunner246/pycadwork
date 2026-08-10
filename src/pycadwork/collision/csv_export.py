"""CSV serialization for a collision report — stdlib ``csv``, stream-based.

The writer takes a text stream, not a path, so callers own the file lifecycle
and tests write to :class:`io.StringIO` — exactly like
:func:`pycadwork.rules.write_violations_csv`. The kind is written as its name
(``OVERLAP`` / ``CONTACT`` / ``NEAR_MISS`` / ``CLEARANCE``).
"""

from __future__ import annotations

import csv
from typing import TextIO

from pycadwork.collision.records import CollisionKind, CollisionReport


def write_clashes_csv(
    report: CollisionReport,
    stream: TextIO,
    *,
    min_kind: CollisionKind = CollisionKind.NEAR_MISS,
) -> None:
    """Write a collision report's clashes as CSV, one row per clash."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["kind", "first_id", "second_id", "distance"])
    for clash in report.clashes:
        if clash.kind < min_kind:
            continue
        writer.writerow(
            [clash.kind.name, clash.first_id, clash.second_id, clash.distance]
        )
