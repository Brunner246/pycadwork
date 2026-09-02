"""pycadwork.gherkin — compile a stdlib Gherkin subset into ``rules.check``.

The snapshot is injected by the caller, so the same ``.feature`` file runs
against a live ``ModelReader().read()``, a SQL ``load_snapshot``, or a test
literal. This module never imports cadwork.
"""

from __future__ import annotations

from pathlib import Path

from pycadwork.gherkin.ast import Scenario
from pycadwork.gherkin.compile import StepBinding, compile_feature
from pycadwork.gherkin.parser import parse
from pycadwork.gherkin.report import (
    FeatureReport,
    GherkinError,
    ScenarioResult,
    StepFailure,
)
from pycadwork.gherkin.steps import register_step, reset_steps
from pycadwork.persistence.records import ModelSnapshot
from pycadwork.rules import RuleReport, Severity, check
from pycadwork.rules.records import Violation

__all__ = [
    "FeatureReport",
    "GherkinError",
    "ScenarioResult",
    "StepFailure",
    "register_step",
    "reset_steps",
    "run_features",
]


def run_features(
    snapshot: ModelSnapshot,
    source: str | Path,
    *,
    min_severity: Severity = Severity.INFO,
) -> FeatureReport:
    """Parse ``source``, compile Then steps, and run one ``check`` pass."""
    feature = parse(_load_source(source))
    compiled = compile_feature(feature)
    if not compiled.rules:
        empty = tuple(
            ScenarioResult(name=scenario.name, ok=True, failures=())
            for scenario in feature.scenarios
        )
        return FeatureReport(title=feature.title, scenarios=empty)
    report = check(snapshot, compiled.rules, min_severity=min_severity)
    return _map_report(feature.title, feature.scenarios, compiled.bindings, report)


def _load_source(source: str | Path) -> str:
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    if "\n" in source or source.lstrip().startswith("Feature:"):
        return source
    return Path(source).read_text(encoding="utf-8")


def _map_report(
    title: str,
    scenarios: tuple[Scenario, ...],
    bindings: tuple[StepBinding, ...],
    report: RuleReport,
) -> FeatureReport:
    by_id = {binding.rule_id: binding for binding in bindings}
    grouped: list[list[StepFailure]] = [[] for _ in scenarios]
    has_error = [False] * len(scenarios)
    for violation in report.violations:
        binding = by_id[violation.rule_id]
        grouped[binding.scenario_index].append(_to_failure(binding, violation))
        if violation.severity is Severity.ERROR:
            has_error[binding.scenario_index] = True
    results = tuple(
        ScenarioResult(
            name=scenario.name,
            ok=not has_error[index],
            failures=tuple(grouped[index]),
        )
        for index, scenario in enumerate(scenarios)
    )
    violations = tuple(failure for group in grouped for failure in group)
    return FeatureReport(
        title=title,
        scenarios=results,
        violations=violations,
        rules_run=report.rules_run,
    )


def _to_failure(binding: StepBinding, violation: Violation) -> StepFailure:
    return StepFailure(
        scenario=binding.scenario_name,
        step=binding.step,
        rule_id=violation.rule_id,
        element_id=violation.element_id,
        element_type=violation.element_type,
        message=violation.message,
    )
