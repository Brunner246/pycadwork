"""Compile expanded scenarios into ``Rule`` objects with stable ``rule_id``s."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from pycadwork.gherkin.ast import Feature, Scenario, Step
from pycadwork.gherkin.report import GherkinError
from pycadwork.gherkin.steps import match_step
from pycadwork.persistence.records import ModelSnapshot
from pycadwork.reporting.index import SnapshotIndex
from pycadwork.rules import (
    ElementRule,
    ModelFinding,
    ModelRule,
    Rule,
    Selector,
    Severity,
)

_GIVEN_NOOPS = frozenset({"the model", "the snapshot"})


@dataclass(frozen=True, slots=True)
class StepBinding:
    """Maps a compiled ``rule_id`` back onto its scenario and step text."""

    rule_id: str
    scenario_index: int
    scenario_name: str
    step: str


@dataclass(frozen=True, slots=True)
class CompiledFeature:
    """Rules for one ``check`` pass plus the mapping used to build the report."""

    rules: tuple[Rule, ...]
    bindings: tuple[StepBinding, ...]


def compile_feature(feature: Feature) -> CompiledFeature:
    """Turn ``feature`` into rules. Unknown steps raise :class:`GherkinError`."""
    rules: list[Rule] = []
    bindings: list[StepBinding] = []
    for scenario_index, scenario in enumerate(feature.scenarios):
        for step_index, step in enumerate(scenario.steps):
            compiled = _compile_step(feature.title, scenario, step, step_index)
            if compiled is None:
                continue
            rule_id, step_rules = compiled
            rules.extend(step_rules)
            bindings.append(
                StepBinding(
                    rule_id=rule_id,
                    scenario_index=scenario_index,
                    scenario_name=scenario.name,
                    step=_raw_step(step),
                )
            )
    return CompiledFeature(rules=tuple(rules), bindings=tuple(bindings))


def _compile_step(
    feature_title: str, scenario: Scenario, step: Step, step_index: int
) -> tuple[str, list[Rule]] | None:
    if step.kind == "Given" and step.text in _GIVEN_NOOPS:
        return None
    produced = match_step(step.text)
    if produced is None:
        raw = _raw_step(step)
        if step.kind == "When":
            raise GherkinError(f"line {step.line}: unmatched When {raw!r}")
        raise GherkinError(f"line {step.line}: unknown step {raw!r}")
    if isinstance(produced, Sequence) and not isinstance(produced, (str, bytes)):
        step_rules = list(produced)
    else:
        step_rules = [produced]
    rule_id = _rule_id(feature_title, scenario, step_index)
    stamped = [_with_id(rule, rule_id) for rule in step_rules]
    element_rules = [rule for rule in stamped if isinstance(rule, ElementRule)]
    if element_rules:
        stamped.append(_require_match(element_rules[0].selects, rule_id))
    return rule_id, stamped


def _rule_id(feature_title: str, scenario: Scenario, step_index: int) -> str:
    base = f"{feature_title}:{scenario.name}:{step_index}"
    if scenario.outline_row is None:
        return base
    return f"{base}:{scenario.outline_row}"


def _with_id(rule: Rule, rule_id: str) -> Rule:
    return replace(rule, id=rule_id)


def _require_match(selects: Selector, rule_id: str) -> ModelRule:
    def evaluate(index: SnapshotIndex, snapshot: ModelSnapshot) -> tuple[ModelFinding, ...]:
        for element in snapshot.elements:
            if selects(index, element):
                return ()
        return (ModelFinding(None, "no matching elements"),)

    return ModelRule(
        id=rule_id,
        description="step must match at least one element",
        severity=Severity.ERROR,
        evaluate=evaluate,
    )


def _raw_step(step: Step) -> str:
    return f"{step.keyword} {step.text}".strip()
