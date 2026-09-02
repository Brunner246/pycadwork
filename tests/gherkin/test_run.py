"""run_features report, snapshot injection, register_step, and authoring errors."""

from __future__ import annotations

import pytest

from pycadwork.gherkin import GherkinError, register_step, reset_steps, run_features
from pycadwork.persistence import UnitOfWork, load_snapshot, open_sqlite
from pycadwork.persistence.records import (
    AttributeRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
)
from pycadwork.rules import ElementRule, Severity, any_element


def _snapshot(**kwargs: object) -> ModelSnapshot:
    return ModelSnapshot(project=ProjectRecord("g"), **kwargs)  # type: ignore[arg-type]


def _stud() -> ModelSnapshot:
    return _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        attributes=(
            AttributeRecord("g", 1, name="Stud", material_name="Pine", ifc_type="IfcBeam"),
            AttributeRecord("g", 2, name="Stud", material_name="Oak", ifc_type="IfcBeam"),
        ),
        geometries=(
            GeometryRecord("g", 1, width=80.0),
            GeometryRecord("g", 2, width=80.0),
        ),
    )


_FAILING = """\
Feature: Framing QA
  Scenario: Studs are pine
    Given the model
    Then every beam named "Stud" has material "Pine"
"""


def test_failures_map_onto_scenario_and_step() -> None:
    report = run_features(_stud(), _FAILING)
    assert report.ok is False
    assert report.title == "Framing QA"
    assert report.failures is report.violations
    assert len(report.scenarios) == 1
    assert report.scenarios[0].ok is False
    failure = report.failures[0]
    assert failure.scenario == "Studs are pine"
    assert "has material" in failure.step
    assert failure.element_id == 2
    assert failure.element_type == "beam"
    assert failure.message
    assert "Framing QA:Studs are pine:" in failure.rule_id


def test_empty_feature_is_ok() -> None:
    report = run_features(_snapshot(), "Feature: Empty\n")
    assert report.ok is True
    assert report.scenarios == ()
    assert report.violations == ()
    assert report.rules_run == ()


def test_same_feature_over_literal_and_sql_load_snapshot() -> None:
    snap = _stud()
    connection = open_sqlite(":memory:")
    unit = UnitOfWork(connection)
    for record in snap.all_records():
        unit.register_new(record)
    unit.commit()
    loaded = load_snapshot(connection, snap.project.project_guid)
    literal = run_features(snap, _FAILING)
    sql = run_features(loaded, _FAILING)
    assert literal.violations == sql.violations


def test_source_path_and_text_are_equivalent(tmp_path) -> None:
    path = tmp_path / "framing.feature"
    path.write_text(_FAILING, encoding="utf-8")
    snap = _stud()
    from_text = run_features(snap, _FAILING)
    from_path = run_features(snap, path)
    from_str_path = run_features(snap, str(path))
    assert from_text.violations == from_path.violations == from_str_path.violations


def test_scenario_outline_and_background_run() -> None:
    source = """\
Feature: sizes
  Background:
    Given the snapshot
  Scenario Outline: section
    Then every beam named "<name>" has width <width>
    Examples:
      | name | width |
      | Stud | 80    |
"""
    report = run_features(_stud(), source)
    assert report.ok
    assert report.scenarios[0].name == "section"


def test_unknown_then_raises_with_raw_step_text() -> None:
    source = """\
Feature: x
  Scenario: y
    Then this phrase is not registered
"""
    with pytest.raises(GherkinError, match="this phrase is not registered"):
        run_features(_snapshot(), source)


def test_unmatched_when_raises_with_raw_step_text() -> None:
    source = """\
Feature: x
  Scenario: y
    When I delete the studs
"""
    with pytest.raises(GherkinError, match="When I delete the studs"):
        run_features(_snapshot(), source)


def test_register_step_adds_a_phrase_and_reset_restores_builtins() -> None:
    def always_pass(**kwargs: str) -> ElementRule:
        return ElementRule(
            id="custom",
            description="custom",
            severity=Severity.ERROR,
            selects=any_element(),
            check=lambda index, element: None,
        )

    source = """\
Feature: x
  Scenario: y
    Then everything is fine
"""
    with pytest.raises(GherkinError, match="everything is fine"):
        run_features(_snapshot(), source)

    register_step(r"everything is fine", always_pass)
    assert run_features(_stud(), source).ok

    reset_steps()
    with pytest.raises(GherkinError, match="everything is fine"):
        run_features(_snapshot(), source)


def test_passing_feature_is_ok() -> None:
    source = """\
Feature: Framing
  Scenario: one oak
    Then there are 1 beams named "Stud"
    And every beam named "Stud" has width 80
"""
    # two studs named Stud — count 1 should fail; use a matching snapshot
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"),),
        attributes=(AttributeRecord("g", 1, name="Stud", material_name="Pine"),),
        geometries=(GeometryRecord("g", 1, width=80.0),),
    )
    report = run_features(snap, source)
    assert report.ok
    assert report.rules_run
