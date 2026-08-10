"""pycadwork.rules — a linter for the model: validate it against declarative rules.

Pure rule functions over a
:class:`~pycadwork.persistence.records.ModelSnapshot`, the sibling of
:mod:`pycadwork.reporting`. A rule comes in two shapes — an
:class:`ElementRule` evaluated per selected element, and a :class:`ModelRule`
evaluated once over the whole snapshot — and :func:`check` runs a mix of them in
one pass, returning a sorted :class:`RuleReport`. Nothing here imports cadwork or
touches SQL, so the same rules run against both snapshot sources and the module
is unit-testable from record literals::

    from pycadwork.persistence import ModelReader, Synchronizer, load_snapshot, open_sqlite
    from pycadwork.rules import check, has_material, assigned_to_storey, dimensions_within

    rules = [has_material(), assigned_to_storey(), dimensions_within(width=(40, 300))]

    # live model
    report = check(ModelReader().read(), rules)
    assert report.ok           # no ERROR-severity violations

    # pulled SQL store — an equal report
    connection = open_sqlite("model.db")
    Synchronizer().pull(connection)
    report = check(load_snapshot(connection, guid), rules)

Built-in rules are factory free functions (``has_material()``), composing like
reporting's ``by_*`` axes; a custom rule is one :class:`ElementRule` /
:class:`ModelRule` literal away. :class:`SnapshotIndex` is re-exported so a
custom rule has the same one import site reporting offers.
"""

from __future__ import annotations

from pycadwork.reporting.index import SnapshotIndex
from pycadwork.rules.csv_export import write_violations_csv
from pycadwork.rules.engine import (
    ElementRule,
    ModelFinding,
    ModelRule,
    Rule,
    RuleResult,
    Selector,
    any_element,
    check,
    for_types,
    with_attribute,
    with_geometry,
)
from pycadwork.rules.library import (
    assigned_to_storey,
    dimensions_within,
    every_member_has_container_parent,
    has_material,
    has_production_number,
    material_in,
    material_is_known,
    named,
    naming_matches,
    no_duplicate_part_numbers_with_different_dims,
    unique_assembly_numbers,
    volume_between,
    weight_between,
)
from pycadwork.rules.records import MODEL_WIDE, RuleReport, Violation
from pycadwork.rules.severity import Severity

__all__ = [
    "MODEL_WIDE",
    "ElementRule",
    "ModelFinding",
    "ModelRule",
    "Rule",
    "RuleReport",
    "RuleResult",
    "Selector",
    "Severity",
    "SnapshotIndex",
    "Violation",
    "any_element",
    "assigned_to_storey",
    "check",
    "dimensions_within",
    "every_member_has_container_parent",
    "for_types",
    "has_material",
    "has_production_number",
    "material_in",
    "material_is_known",
    "named",
    "naming_matches",
    "no_duplicate_part_numbers_with_different_dims",
    "unique_assembly_numbers",
    "volume_between",
    "weight_between",
    "with_attribute",
    "with_geometry",
    "write_violations_csv",
]
