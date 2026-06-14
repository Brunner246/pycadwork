"""Source equivalence: a live-model snapshot and a pulled-SQL snapshot yield
identical reports — the architectural claim behind building reports on
ModelSnapshot."""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Synchronizer,
    open_sqlite,
)
from pycadwork.persistence import ModelReader, load_snapshot
from pycadwork.persistence._ids import ProjectGuid
from pycadwork.reporting import by_group, by_material, cutting_list, material_totals


def _seed_model() -> None:
    for x in (0.0, 600.0, 1200.0):
        beam = Beam.create_rectangular(
            RectSection(80, 200),
            AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
        )
        beam.attrs.name = "Stud"
        beam.attrs.material_name = "Pine"
        beam.attrs.group = "W1"
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    plate.attrs.name = "Sheathing"
    plate.attrs.material_name = "OSB"


def test_live_and_sql_snapshots_yield_identical_reports() -> None:
    _seed_model()
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    live = ModelReader().read()
    stored = load_snapshot(connection, ProjectGuid(Document().guid))
    dimensions = (by_group(), by_material())

    assert cutting_list(live) == cutting_list(stored)
    assert cutting_list(live, dimensions=dimensions) == cutting_list(
        stored, dimensions=dimensions
    )
    assert material_totals(live) == material_totals(stored)


def test_seeded_model_produces_the_expected_cutting_list() -> None:
    _seed_model()

    rows = cutting_list(ModelReader().read())

    by_name = {r.name: r for r in rows}
    assert by_name["Stud"].count == 3
    assert by_name["Stud"].material_name == "Pine"
    assert by_name["Sheathing"].count == 1
    assert by_name["Sheathing"].material_name == "OSB"
