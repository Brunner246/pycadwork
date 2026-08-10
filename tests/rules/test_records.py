"""Violation / RuleReport: ok semantics, grouping, counts — no engine involved."""

from __future__ import annotations

from pycadwork.rules import RuleReport, Severity, Violation


def _v(
    severity: Severity, rule_id: str = "r", eid: int = 1, message: str = "m"
) -> Violation:
    return Violation(
        severity=severity,
        rule_id=rule_id,
        element_id=eid,
        element_type="beam",
        message=message,
    )


def test_empty_report_is_ok() -> None:
    report = RuleReport()
    assert report.ok is True
    assert report.violations == ()
    assert report.count() == 0


def test_ok_is_false_only_with_an_error() -> None:
    assert RuleReport(violations=(_v(Severity.WARNING), _v(Severity.INFO))).ok is True
    assert RuleReport(violations=(_v(Severity.ERROR),)).ok is False


def test_count_filters_by_severity() -> None:
    report = RuleReport(
        violations=(_v(Severity.ERROR), _v(Severity.WARNING), _v(Severity.WARNING))
    )
    assert report.count() == 3
    assert report.count(Severity.WARNING) == 2
    assert report.count(Severity.ERROR) == 1
    assert report.count(Severity.INFO) == 0


def test_by_severity_groups_in_report_order() -> None:
    a, b, c = (
        _v(Severity.ERROR, "a"),
        _v(Severity.WARNING, "b"),
        _v(Severity.ERROR, "c"),
    )
    grouped = RuleReport(violations=(a, b, c)).by_severity()
    assert grouped[Severity.ERROR] == (a, c)
    assert grouped[Severity.WARNING] == (b,)


def test_by_rule_groups_in_report_order() -> None:
    a, b, c = _v(Severity.ERROR, "x"), _v(Severity.WARNING, "y"), _v(Severity.INFO, "x")
    grouped = RuleReport(violations=(a, b, c)).by_rule()
    assert grouped["x"] == (a, c)
    assert grouped["y"] == (b,)


def test_failures_aliases_violations() -> None:
    report = RuleReport(violations=(_v(Severity.ERROR),))
    assert report.failures == report.violations


def test_violation_is_hashable_and_frozen() -> None:
    assert len({_v(Severity.ERROR), _v(Severity.ERROR)}) == 1
