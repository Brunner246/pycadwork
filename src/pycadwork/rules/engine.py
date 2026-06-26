"""The rule abstractions, the element selectors, and the ``check`` entry point.

A rule comes in two shapes, mirroring the two natural evaluation modes — and
deliberately *not* forcing one path (see ``docs/design-principles.md``):

* :class:`ElementRule` is evaluated independently per *selected* element. Its
  :attr:`~ElementRule.check` returns a :data:`RuleResult` — ``None`` to pass, or
  a ``str`` detail to fail. This covers the common case (every beam has a
  material, names are non-empty, dimensions are in range).
* :class:`ModelRule` is evaluated once over the whole snapshot and yields its
  own :class:`ModelFinding` objects. This covers genuinely cross-element checks
  (no two parts share a production number but differ in size) that a per-element
  predicate cannot express.

Both carry the same metadata (``id`` / ``description`` / ``severity``), so the
engine, the report, and the CSV writer treat them uniformly. The selector and
predicate receive a :class:`~pycadwork.reporting.index.SnapshotIndex` built once
per pass — exactly like :meth:`pycadwork.reporting.Dimension.key_of` — plus the
element's :class:`~pycadwork.persistence.records.ElementRecord` (rules dispatch
on ``element_type``, which a bare id could not give them).

Like reporting, this module is a pure function over a
:class:`~pycadwork.persistence.records.ModelSnapshot`: it never imports cadwork
or touches SQL, so the same rules run against a live read
(``ModelReader().read()``) or a pulled SQL store (``load_snapshot(conn, guid)``)
and the whole package is unit-testable from record literals.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from pycadwork.persistence._ids import ElementId
from pycadwork.persistence.records import ElementRecord, ModelSnapshot

# SnapshotIndex lives in reporting (its first consumer); rules reuse it rather
# than duplicate or relocate it. This makes rules depend on reporting — a mildly
# surprising direction; if it ever grates, the clean move is the index into
# pycadwork.persistence and both packages import it from there.
from pycadwork.reporting.index import SnapshotIndex
from pycadwork.rules.records import MODEL_WIDE, RuleReport, Violation
from pycadwork.rules.severity import Severity

#: A predicate result: ``None`` passes; a ``str`` fails and is the per-instance
#: detail appended to the rule's description in the resulting :class:`Violation`.
RuleResult = str | None

#: A selector decides whether an :class:`ElementRule` applies to an element.
Selector = Callable[[SnapshotIndex, ElementRecord], bool]


@dataclass(frozen=True, slots=True)
class ModelFinding:
    """One finding emitted by a :class:`ModelRule`.

    ``element_id`` attributes the finding to a specific element, or is ``None``
    for a model-wide finding that names none (e.g. "0 elements assigned to any
    storey").
    """

    element_id: ElementId | None
    message: str


@dataclass(frozen=True, slots=True)
class ElementRule:
    """A rule evaluated independently per selected element."""

    id: str
    description: str
    severity: Severity
    selects: Selector
    check: Callable[[SnapshotIndex, ElementRecord], RuleResult]


@dataclass(frozen=True, slots=True)
class ModelRule:
    """A rule evaluated once over the whole snapshot, yielding its findings.

    The callable must yield in a deterministic order (sort bucket keys and
    element ids before yielding): a live-read snapshot and a SQL-loaded one are
    not guaranteed to hold elements in the same order, and the engine's final
    sort keys on ``element_id`` — equal ids would otherwise tie unpredictably.
    """

    id: str
    description: str
    severity: Severity
    evaluate: Callable[[SnapshotIndex, ModelSnapshot], Iterable[ModelFinding]]


#: Either rule shape. ``check`` accepts a mixed sequence of these.
Rule = ElementRule | ModelRule


# ---- selectors ----


def any_element() -> Selector:
    """Select every element."""
    return lambda index, element: True


def for_types(*tokens: str) -> Selector:
    """Select elements whose ``element_type`` token is one of ``tokens``.

    Tokens are the lowercase wrapper-class names the snapshot carries
    (``"beam"``, ``"plate"``, ``"wall"``, …) — the same vocabulary
    :data:`pycadwork.reporting.DEFAULT_PART_TYPES` uses.
    """
    allowed = frozenset(tokens)
    return lambda index, element: element.element_type in allowed


def with_attribute() -> Selector:
    """Select only elements that have an attribute satellite in the snapshot."""
    return lambda index, element: index.attribute(element.id) is not None


def with_geometry() -> Selector:
    """Select only elements that have a geometry satellite in the snapshot."""
    return lambda index, element: index.geometry(element.id) is not None


# ---- the engine ----


def _message(description: str, detail: str) -> str:
    """Combine a rule's description with a per-instance detail."""
    return f"{description}: {detail}" if detail else description


def check(
    snapshot: ModelSnapshot,
    rules: Sequence[Rule],
    *,
    min_severity: Severity = Severity.INFO,
) -> RuleReport:
    """Run every rule over ``snapshot`` and collect the violations.

    Mirrors :func:`pycadwork.reporting.cutting_list`: the snapshot is positional,
    tuning is keyword-only, a single :class:`SnapshotIndex` is built up front,
    and the output is deterministically sorted. Element-rules visit each element
    once (selector, then predicate); model-rules then run over the whole
    snapshot. Violations below ``min_severity`` are dropped from the report.

    The result is sorted by ``(severity descending, rule_id, element_id,
    message)`` so the same rules over a live read and a pulled SQL store yield an
    equal report.
    """
    index = SnapshotIndex(snapshot)
    element_rules = [r for r in rules if isinstance(r, ElementRule)]
    model_rules = [r for r in rules if isinstance(r, ModelRule)]

    violations: list[Violation] = []
    checked = 0
    passed = 0

    for element in snapshot.elements:
        applicable = [r for r in element_rules if r.selects(index, element)]
        if applicable:
            checked += 1
        for rule in applicable:
            detail = rule.check(index, element)
            if detail is None:
                passed += 1
                continue
            violations.append(
                Violation(
                    severity=rule.severity,
                    rule_id=rule.id,
                    element_id=int(element.id),
                    element_type=element.element_type,
                    message=_message(rule.description, detail),
                )
            )

    types = {e.id: e.element_type for e in snapshot.elements}
    for rule in model_rules:
        for finding in rule.evaluate(index, snapshot):
            eid = finding.element_id
            violations.append(
                Violation(
                    severity=rule.severity,
                    rule_id=rule.id,
                    element_id=int(eid) if eid is not None else MODEL_WIDE,
                    element_type=types.get(eid, "") if eid is not None else "",
                    message=_message(rule.description, finding.message),
                )
            )

    kept = [v for v in violations if v.severity >= min_severity]
    kept.sort(key=lambda v: (-v.severity, v.rule_id, v.element_id, v.message))

    return RuleReport(
        violations=tuple(kept),
        checked=checked,
        passed=passed,
        rules_run=tuple(sorted(r.id for r in rules)),
    )
