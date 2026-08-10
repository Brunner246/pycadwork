"""check(): selectors, per-element + model rules, severity filter, ordering."""

from __future__ import annotations

from pycadwork.persistence.records import (
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
)
from pycadwork.rules import (
    ElementRule,
    ModelFinding,
    ModelRule,
    Severity,
    any_element,
    check,
    for_types,
    with_geometry,
)


def _snapshot(**kwargs: object) -> ModelSnapshot:
    return ModelSnapshot(project=ProjectRecord("g"), **kwargs)  # type: ignore[arg-type]


def _always_fail(
    rule_id: str = "fail", severity: Severity = Severity.ERROR
) -> ElementRule:
    return ElementRule(
        id=rule_id,
        description="always fails",
        severity=severity,
        selects=any_element(),
        check=lambda index, element: "nope",
    )


def _always_pass(rule_id: str = "pass") -> ElementRule:
    return ElementRule(
        id=rule_id,
        description="always passes",
        severity=Severity.ERROR,
        selects=any_element(),
        check=lambda index, element: None,
    )


def test_passing_rule_produces_no_violation_and_counts_passed() -> None:
    snap = _snapshot(elements=(ElementRecord("g", 1, "beam"),))
    report = check(snap, [_always_pass()])
    assert report.violations == ()
    assert report.checked == 1
    assert report.passed == 1
    assert report.ok is True
    assert report.rules_run == ("pass",)


def test_failing_rule_produces_one_violation_per_element() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "plate"))
    )
    report = check(snap, [_always_fail()])
    assert [v.element_id for v in report.violations] == [1, 2]
    assert all(v.message == "always fails: nope" for v in report.violations)
    assert report.passed == 0
    assert report.ok is False


def test_for_types_selector_scopes_the_rule() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "plate"))
    )
    rule = ElementRule(
        id="beams-only",
        description="d",
        severity=Severity.WARNING,
        selects=for_types("beam"),
        check=lambda index, element: "x",
    )
    report = check(snap, [rule])
    assert [v.element_id for v in report.violations] == [1]
    assert report.checked == 1  # only the beam was visited by an applicable rule


def test_with_geometry_selector_skips_satellite_less_elements() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        geometries=(GeometryRecord("g", 1, length=100.0),),
    )
    rule = ElementRule(
        id="needs-geom",
        description="d",
        severity=Severity.ERROR,
        selects=with_geometry(),
        check=lambda index, element: "x",
    )
    report = check(snap, [rule])
    assert [v.element_id for v in report.violations] == [1]


def test_model_rule_findings_become_violations() -> None:
    snap = _snapshot(elements=(ElementRecord("g", 7, "beam"),))
    rule = ModelRule(
        id="model",
        description="model says",
        severity=Severity.WARNING,
        evaluate=lambda index, snapshot: [
            ModelFinding(7, "boom"),
            ModelFinding(None, "global"),
        ],
    )
    report = check(snap, [rule])
    by_id = {v.element_id: v for v in report.violations}
    assert by_id[7].element_type == "beam"
    assert by_id[7].message == "model says: boom"
    assert by_id[-1].element_type == ""  # MODEL_WIDE
    assert by_id[-1].message == "model says: global"


def test_min_severity_drops_lower_violations() -> None:
    snap = _snapshot(elements=(ElementRecord("g", 1, "beam"),))
    rules = [
        _always_fail("err", Severity.ERROR),
        _always_fail("warn", Severity.WARNING),
    ]
    report = check(snap, rules, min_severity=Severity.ERROR)
    assert [v.rule_id for v in report.violations] == ["err"]


def test_violations_sorted_severity_desc_then_keys() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 2, "beam"), ElementRecord("g", 1, "beam"))
    )
    rules = [_always_fail("zz", Severity.WARNING), _always_fail("aa", Severity.ERROR)]
    report = check(snap, rules)
    # ERROR before WARNING; within a severity, by rule_id then element_id.
    assert [(v.severity, v.rule_id, v.element_id) for v in report.violations] == [
        (Severity.ERROR, "aa", 1),
        (Severity.ERROR, "aa", 2),
        (Severity.WARNING, "zz", 1),
        (Severity.WARNING, "zz", 2),
    ]


def test_empty_snapshot_is_ok() -> None:
    report = check(_snapshot(), [_always_fail(), _always_pass()])
    assert report.ok is True
    assert report.checked == 0
    assert report.passed == 0
    assert report.violations == ()
