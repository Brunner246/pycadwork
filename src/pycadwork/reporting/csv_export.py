"""CSV serialization for report rows — stdlib ``csv``, stream-based.

The writers take a text stream, not a path, so callers own the file lifecycle
and tests write to :class:`io.StringIO`. Pass the same ``dimensions`` the
report was built with and each grouping axis becomes one leading column headed
by its :attr:`~pycadwork.reporting.dimensions.Dimension.label`; without them,
leading columns fall back to generic ``group_1`` … headers sized from the
rows' ``group`` tuples.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from typing import TextIO

from pycadwork.reporting.dimensions import Dimension
from pycadwork.reporting.records import MaterialTotalRow, PartRow


def _group_headers(
    dimensions: Sequence[Dimension],
    rows: Sequence[PartRow] | Sequence[MaterialTotalRow],
) -> list[str]:
    if dimensions:
        return [d.label for d in dimensions]
    width = len(rows[0].group) if rows else 0
    return [f"group_{i + 1}" for i in range(width)]


def write_parts_csv(
    rows: Sequence[PartRow],
    stream: TextIO,
    *,
    dimensions: Sequence[Dimension] = (),
) -> None:
    """Write a cutting list as CSV; ``element_ids`` joins with ``";"``."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        _group_headers(dimensions, rows)
        + [
            "element_type",
            "name",
            "material_name",
            "length",
            "width",
            "height",
            "count",
            "total_volume",
            "total_weight",
            "element_ids",
        ]
    )
    for row in rows:
        writer.writerow(
            list(row.group)
            + [
                row.element_type,
                row.name,
                row.material_name,
                row.length,
                row.width,
                row.height,
                row.count,
                row.total_volume,
                row.total_weight,
                ";".join(str(i) for i in row.element_ids),
            ]
        )


def write_material_totals_csv(
    rows: Sequence[MaterialTotalRow],
    stream: TextIO,
    *,
    dimensions: Sequence[Dimension] = (),
) -> None:
    """Write material totals as CSV."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        _group_headers(dimensions, rows)
        + ["material_name", "count", "total_volume", "total_weight"]
    )
    for row in rows:
        writer.writerow(
            list(row.group)
            + [row.material_name, row.count, row.total_volume, row.total_weight]
        )
