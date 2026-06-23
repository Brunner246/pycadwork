"""Bill of materials: cutting lists and material totals over a snapshot.

:mod:`pycadwork.reporting` answers the quantity-takeoff questions with pure
functions over a :class:`~pycadwork.persistence.records.ModelSnapshot` — the
same frozen-record aggregate the persistence layer reads and writes. That
gives every report two interchangeable sources:

* the **live model**, via ``ModelReader().read()``
* a **pulled SQL store**, via ``load_snapshot(connection, guid)``

Grouping is composable: each ``by_*`` factory yields one
:class:`~pycadwork.reporting.Dimension` axis, and a report groups by the tuple
of the axes you pass — per material, per group, per storey, per owning cover,
or any combination.

    uv run python -m examples.reporting

Reading the live model needs a backend, so ``run()`` executes inside cadwork
or under the test suite's fake adapter.
"""

from __future__ import annotations

import io

from pycadwork import (
    AxisPoints,
    Beam,
    BuildingName,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    StoreyAssigner,
    by_cover,
    by_material,
    by_storey,
    cutting_list,
    material_totals,
)

# Seam access — only to seed BMT storeys and the wall flag (mimics the cadwork UI).
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode
from pycadwork.persistence import ModelReader, Synchronizer, load_snapshot, open_sqlite
from pycadwork.reporting import write_parts_csv

_BUILDING = "Building A"


def _stud(x: float) -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 0, 2900), Point3D(x + 1, 0, 0)),
    )


def _seed_model() -> None:
    """A small framed model: one wall of studs + sheathing, plus loose stock.

    In a real project this state is authored in cadwork; here it is seeded
    through the public API (and, for the storeys and the wall flag, the
    version-isolation seam) so the reports have something to count.
    """
    cadwork.bim.set_storey_height(_BUILDING, "S0", 0.0)
    cadwork.bim.set_storey_height(_BUILDING, "S1", 3000.0)
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)

    # A framed wall: three identical studs and a sheathing panel, linked by group.
    studs = [_stud(x) for x in (0.0, 600.0, 1200.0)]
    sheathing = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 1, 0)),
    )
    wall_parent = _stud(-100.0)
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    wall_parent.attrs.name = "WallA"

    members = [wall_parent, *studs, sheathing]
    for member in members:
        member.attrs.group = "W1"
    for stud in studs:
        stud.attrs.name = "Stud"
        stud.attrs.material_name = "Pine"
    sheathing.attrs.name = "Sheathing"
    sheathing.attrs.material_name = "OSB"

    # A loose first-floor beam outside any cover.
    loose = Beam.create_rectangular(
        RectSection(120.0, 240.0),
        AxisPoints(Point3D(0, 0, 3000), Point3D(4000, 0, 3000), Point3D(0, 0, 3001)),
    )
    loose.attrs.name = "Girder"
    loose.attrs.material_name = "Spruce"

    StoreyAssigner(BuildingName(_BUILDING)).assign([*members, loose])


def demo_cutting_list() -> None:
    """The flat cutting list: identical parts collapse to one counted row."""
    rows = cutting_list(ModelReader().read())

    for row in rows:
        print(
            f"  {row.count}x {row.name or '(unnamed)':<10} {row.material_name or '-':<7}"
            f" {row.length:.0f} x {row.width:.0f} x {row.height:.0f}"
            f"  volume={row.total_volume:.4g}"
        )


def demo_material_totals() -> None:
    """Totals per material — count, volume, weight."""
    for row in material_totals(ModelReader().read()):
        print(
            f"  {row.material_name or '(none)':<7} count={row.count} "
            f"total_volume={row.total_volume:.4g}"
        )


def demo_composed_dimensions() -> None:
    """Axes compose: one call groups per storey *and* per material."""
    rows = cutting_list(ModelReader().read(), dimensions=(by_storey(), by_material()))
    for row in rows:
        storey, material = row.group
        print(
            f"  [{storey} | {material or '-'}] {row.count}x {row.name or '(unnamed)'}"
        )

    # by_cover groups by the owning wall/slab/roof instead (linked via group here).
    for row in cutting_list(ModelReader().read(), dimensions=(by_cover(),)):
        (cover,) = row.group
        print(f"  [{cover or 'loose'}] {row.count}x {row.name or '(unnamed)'}")


def demo_from_sql_snapshot() -> None:
    """The same report from a pulled SQL store — identical rows, no model read."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    stored = load_snapshot(connection, Document().guid)
    live = ModelReader().read()

    assert cutting_list(stored) == cutting_list(live)
    print(f"  SQL snapshot and live model agree: {len(cutting_list(stored))} rows")


def demo_csv() -> None:
    """Serialize a report with the stdlib-csv writers (stream-based)."""
    dimensions = (by_material(),)
    rows = cutting_list(ModelReader().read(), dimensions=dimensions)

    stream = io.StringIO()
    write_parts_csv(rows, stream, dimensions=dimensions)
    print("  " + stream.getvalue().splitlines()[0])  # the header line
    print(f"  ... {len(rows)} data rows")


def run() -> None:
    """Run every reporting demo in order."""
    _seed_model()
    demo_cutting_list()
    demo_material_totals()
    demo_composed_dimensions()
    demo_from_sql_snapshot()
    demo_csv()

    # from pathlib import Path
    #
    # dimensions = (by_material(),)
    # rows = cutting_list(ModelReader().read(), dimensions=dimensions)
    #
    # out_path = Path.home() / "Downloads" / "cutting_list.csv"
    # with out_path.open("w", newline="", encoding="utf-8") as stream:
    #     write_parts_csv(rows, stream, dimensions=dimensions)
    #
    # print(f"wrote {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    run()
