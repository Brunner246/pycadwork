"""Validate the model against declarative rules — a linter over a snapshot.

:mod:`pycadwork.rules` is the sibling of :mod:`pycadwork.reporting`: pure rule
functions over a :class:`~pycadwork.persistence.records.ModelSnapshot`, so the
same rules run against the **live model** (``ModelReader().read()``) or a
**pulled SQL store** (``load_snapshot(connection, guid)``).

A rule set is a list of factory calls; :func:`~pycadwork.rules.check` runs them
in one pass and returns a sorted :class:`~pycadwork.rules.RuleReport`. Built-in
rules come in two shapes — per-element (``has_material``) and model-level
(``no_duplicate_part_numbers_with_different_dims``) — and a custom rule is one
:class:`~pycadwork.rules.ElementRule` literal away.

    uv run python -m examples.rules

Reading the live model needs a backend, so ``run()`` executes inside cadwork or
under the test suite's fake adapter.
"""

from __future__ import annotations

import io

from pycadwork import (
    AxisPoints,
    Beam,
    BuildingName,
    Document,
    ElementRule,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Severity,
    StoreyAssigner,
    assigned_to_storey,
    check,
    dimensions_within,
    has_material,
    named,
    no_duplicate_part_numbers_with_different_dims,
    write_violations_csv,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.persistence import ModelReader, Synchronizer, load_snapshot, open_sqlite
from pycadwork.rules import for_types

_BUILDING = "Building A"


def _seed_model() -> None:
    """A small framed model with a couple of deliberate defects to flag.

    In a real project this state is authored in cadwork; here it is seeded
    through the public API (and the version-isolation seam for the storeys) so
    the rules have something to validate. Two studs are left without a material
    on purpose, and a sheathing panel reuses a stud's part number at a different
    size — the kinds of slips a linter should catch before fabrication.
    """
    cadwork.bim.set_storey_height(_BUILDING, "S0", 0.0)

    studs = [
        Beam.create_rectangular(
            RectSection(80.0, 200.0),
            AxisPoints(Point3D(x, 0, 0), Point3D(x, 0, 2900), Point3D(x + 1, 0, 0)),
        )
        for x in (0.0, 600.0, 1200.0)
    ]
    for stud in studs:
        stud.attrs.name = "Stud"
        stud.attrs.part_number = "P1"
    studs[0].attrs.material_name = "Pine"  # the other two are left bare on purpose

    sheathing = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 1, 0)),
    )
    sheathing.attrs.name = "Sheathing"
    sheathing.attrs.material_name = "OSB"
    sheathing.attrs.part_number = "P1"  # clashes with the studs at a different size

    StoreyAssigner(BuildingName(_BUILDING)).assign([*studs, sheathing])


def _rule_set() -> list:
    """The rules used across the demos — element-level and model-level."""
    return [
        named(),
        has_material(),
        assigned_to_storey(),
        dimensions_within(width=(40.0, 400.0)),
        no_duplicate_part_numbers_with_different_dims(),
    ]


def demo_basic_rules() -> None:
    """Run the rule set over the live model and print the report summary."""
    report = check(ModelReader().read(), _rule_set())
    print(f"  ok={report.ok} checked={report.checked} passed={report.passed}")
    for v in report.violations:
        print(f"  {v.severity.name:<7} {v.rule_id:<26} #{v.element_id} {v.message}")


def demo_model_level_rule() -> None:
    """A model-level rule sees the whole model — here, a part-number clash."""
    report = check(
        ModelReader().read(),
        [no_duplicate_part_numbers_with_different_dims()],
    )
    print(f"  duplicate-part-number findings: {report.count()}")


def demo_custom_rule() -> None:
    """A custom rule is one ElementRule literal — no factory needed."""

    def heavy(index, element) -> str | None:
        geometry = index.geometry(element.id)
        if geometry is None or geometry.volume <= 0.05:
            return None
        return f"volume {geometry.volume:.3g} m³ exceeds the handling limit"

    rule = ElementRule(
        id="handling-limit",
        description="part must be liftable by hand",
        severity=Severity.INFO,
        selects=for_types("beam", "plate"),
        check=heavy,
    )
    report = check(ModelReader().read(), [rule])
    print(f"  custom-rule violations: {report.count()}")


def demo_from_sql_snapshot() -> None:
    """The same rules over a pulled SQL store — an equal report, no model read."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    stored = load_snapshot(connection, Document().guid)
    live = ModelReader().read()
    rules = _rule_set()

    assert check(stored, rules) == check(live, rules)
    print("  SQL snapshot and live model agree on the report")


def demo_csv() -> None:
    """Serialize a report's violations with the stream-based stdlib-csv writer."""
    report = check(ModelReader().read(), _rule_set())
    stream = io.StringIO()
    write_violations_csv(report, stream)
    print("  " + stream.getvalue().splitlines()[0])  # the header line
    print(f"  ... {report.count()} violation rows")


def run() -> None:
    """Run every rules demo in order."""
    _seed_model()
    demo_basic_rules()
    demo_model_level_rule()
    demo_custom_rule()
    demo_from_sql_snapshot()
    demo_csv()


if __name__ == "__main__":
    run()
