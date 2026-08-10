"""Rule output — the frozen result DTOs of the rule engine.

A :class:`Violation` is one failed (element, rule) pair (or one model-level
finding); a :class:`RuleReport` is the whole result of a :func:`check` pass.
Like the reporting rows (:class:`~pycadwork.reporting.records.PartRow`) they are
frozen, slotted, and carry only plain scalars plus tuples — safe to sort, hash
into sets, and serialize, and equality-comparable so the same rules over a live
read and a pulled SQL store produce equal reports.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from pycadwork.rules.severity import Severity

#: The element id stamped on a model-wide finding that names no element.
MODEL_WIDE: int = -1


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    """One rule failure.

    ``element_id`` is the unwrapped int (like
    :attr:`~pycadwork.reporting.records.PartRow.element_ids`); it is
    :data:`MODEL_WIDE` (``-1``) for a model-level finding that names no element,
    and ``element_type`` is then ``""``. ``message`` is the rule's description
    plus the per-instance detail the predicate returned.

    Field order is the sort order: severity first (descending is applied by the
    engine), then rule, element, message — so a report's violations are
    deterministic regardless of the snapshot's internal element order.
    """

    severity: Severity
    rule_id: str
    element_id: int
    element_type: str
    message: str


@dataclass(frozen=True, slots=True)
class RuleReport:
    """The result of one :func:`~pycadwork.rules.check` pass.

    ``violations`` is sorted and deterministic. ``checked`` counts the elements
    visited by at least one element-rule; ``passed`` counts the (element, rule)
    pairs that returned no violation; ``rules_run`` is the sorted ids of every
    rule that executed.
    """

    violations: tuple[Violation, ...] = ()
    checked: int = 0
    passed: int = 0
    rules_run: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """True when no ``ERROR``-severity violation was raised.

        ``WARNING`` and ``INFO`` violations do not break ``ok`` — it is the
        clean CI gate (``assert check(...).ok``) while advisories still surface
        in :attr:`violations`.
        """
        return not any(v.severity is Severity.ERROR for v in self.violations)

    @property
    def failures(self) -> tuple[Violation, ...]:
        """Alias for :attr:`violations` — every recorded failure."""
        return self.violations

    def by_severity(self) -> dict[Severity, tuple[Violation, ...]]:
        """Group the violations by severity, each list in report order."""
        grouped: dict[Severity, list[Violation]] = defaultdict(list)
        for violation in self.violations:
            grouped[violation.severity].append(violation)
        return {severity: tuple(items) for severity, items in grouped.items()}

    def by_rule(self) -> dict[str, tuple[Violation, ...]]:
        """Group the violations by rule id, each list in report order."""
        grouped: dict[str, list[Violation]] = defaultdict(list)
        for violation in self.violations:
            grouped[violation.rule_id].append(violation)
        return {rule_id: tuple(items) for rule_id, items in grouped.items()}

    def count(self, severity: Severity | None = None) -> int:
        """Total violations, or only those of ``severity`` when given."""
        if severity is None:
            return len(self.violations)
        return sum(1 for v in self.violations if v.severity is severity)
