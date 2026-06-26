"""Source equivalence: the same rules over a live-model snapshot and a pulled-SQL
snapshot yield an equal report — the architectural claim behind building rules on
ModelSnapshot, mirroring tests/reporting/test_sources.py."""

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
    assigned_to_storey,
    check,
    dimensions_within,
    has_material,
    named,
    no_duplicate_part_numbers_with_different_dims,
    open_sqlite,
)
from pycadwork.persistence import ModelReader, load_snapshot


def _seed_model() -> None:
    for x in (0.0, 600.0, 1200.0):
        beam = Beam.create_rectangular(
            RectSection(80, 200),
            AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
        )
        beam.attrs.name = "Stud"
        beam.attrs.part_number = "P1"
    beam.attrs.material_name = "Pine"  # leave the others bare on purpose

    panel = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 1, 0)),
    )
    panel.attrs.name = "Sheathing"
    panel.attrs.part_number = "P1"  # clashes with the studs at a different size


def _rules() -> list:
    return [
        named(),
        has_material(),
        assigned_to_storey(),
        dimensions_within(width=(40.0, 400.0)),
        no_duplicate_part_numbers_with_different_dims(),
    ]


def test_live_and_sql_snapshots_give_equal_reports() -> None:
    _seed_model()
    rules = _rules()

    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)
    stored = load_snapshot(connection, Document().guid)
    live = ModelReader().read()

    assert check(stored, rules) == check(live, rules)


def test_report_is_deterministic_across_repeated_reads() -> None:
    _seed_model()
    rules = _rules()
    assert check(ModelReader().read(), rules) == check(ModelReader().read(), rules)
