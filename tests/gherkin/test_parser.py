"""Dialect parser: supported keywords, expansion, and line-numbered rejections."""

from __future__ import annotations

import pytest

from pycadwork.gherkin import GherkinError
from pycadwork.gherkin.parser import parse


def test_feature_scenario_and_description() -> None:
    feature = parse(
        """\
Feature: Framing QA
  Studs must be pine.

  Scenario: Studs are pine
    Given the model
    Then every beam named "Stud" has material "Pine"
"""
    )
    assert feature.title == "Framing QA"
    assert "Studs must be pine" in feature.description
    assert len(feature.scenarios) == 1
    scenario = feature.scenarios[0]
    assert scenario.name == "Studs are pine"
    assert [step.kind for step in scenario.steps] == ["Given", "Then"]
    assert scenario.steps[0].text == "the model"
    assert scenario.steps[1].text == 'every beam named "Stud" has material "Pine"'


def test_and_but_inherit_kind() -> None:
    feature = parse(
        """\
Feature: x
  Scenario: y
    Given the model
    Then every beam named "Stud" has material "Pine"
    And every beam named "Stud" has ifc type "IfcBeam"
    But every beam named "Stud" has group "Frame"
"""
    )
    kinds = [step.kind for step in feature.scenarios[0].steps]
    assert kinds == ["Given", "Then", "Then", "Then"]
    assert feature.scenarios[0].steps[2].keyword == "And"
    assert feature.scenarios[0].steps[3].keyword == "But"


def test_background_is_prepended() -> None:
    feature = parse(
        """\
Feature: x
  Background:
    Given the snapshot
  Scenario: a
    Then there are 1 beams named "Stud"
  Scenario: b
    Then there are 0 plates
"""
    )
    assert [s.steps[0].text for s in feature.scenarios] == ["the snapshot", "the snapshot"]
    assert feature.scenarios[0].steps[1].text == 'there are 1 beams named "Stud"'
    assert feature.scenarios[1].steps[1].text == "there are 0 plates"


def test_scenario_outline_expands_rows() -> None:
    feature = parse(
        """\
Feature: sizes
  Scenario Outline: <name> is pine
    Then every beam named "<name>" has material "<mat>"
    Examples:
      | name | mat  |
      | Stud | Pine |
      | Plate | Oak |
"""
    )
    assert [s.name for s in feature.scenarios] == ["Stud is pine", "Plate is pine"]
    assert feature.scenarios[0].outline_row == 0
    assert feature.scenarios[1].outline_row == 1
    assert feature.scenarios[0].steps[0].text == 'every beam named "Stud" has material "Pine"'
    assert feature.scenarios[1].steps[0].text == 'every beam named "Plate" has material "Oak"'


def test_comments_are_stripped_but_not_inside_quotes() -> None:
    feature = parse(
        """\
Feature: x
  # a comment
  Scenario: y
    Then every beam named "Stud #1" has material "Pine" # trailing
"""
    )
    assert feature.scenarios[0].steps[0].text == 'every beam named "Stud #1" has material "Pine"'


def test_tags_rejected_with_line_number() -> None:
    with pytest.raises(GherkinError, match=r"line 2: tags"):
        parse("Feature: x\n  @wip\n  Scenario: y\n    Given the model\n")


def test_doc_string_rejected_with_line_number() -> None:
    with pytest.raises(GherkinError, match=r"line 3: doc strings"):
        parse('Feature: x\n  Scenario: y\n    """\n    no\n    """\n')


def test_language_header_rejected_with_line_number() -> None:
    with pytest.raises(GherkinError, match=r"line 1: language:"):
        parse("# language: de\nFeature: x\n  Scenario: y\n    Given the model\n")


def test_rule_block_rejected_with_line_number() -> None:
    with pytest.raises(GherkinError, match=r"line 2: Rule:"):
        parse("Feature: x\n  Rule: nested\n    Scenario: y\n      Given the model\n")


def test_and_without_previous_step_is_an_error() -> None:
    source = 'Feature: x\n  Scenario: y\n    And every beam named "Stud" has material "Pine"\n'
    with pytest.raises(GherkinError, match=r"line 3: And without"):
        parse(source)


def test_empty_source_expects_feature() -> None:
    with pytest.raises(GherkinError, match=r"line 1: expected Feature:"):
        parse("")
