"""Closed Then vocabulary: pass/fail, missing geometry, zero-match, counts."""

from __future__ import annotations

from pycadwork.gherkin import run_features
from pycadwork.persistence.records import (
    AttributeRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
)


def _snapshot(**kwargs: object) -> ModelSnapshot:
    return ModelSnapshot(project=ProjectRecord("g"), **kwargs)  # type: ignore[arg-type]


def _stud(
    *,
    material: str = "Pine",
    ifc: str = "IfcBeam",
    group: str = "Frame",
    width: float | None = 80.0,
) -> ModelSnapshot:
    geometries = ()
    if width is not None:
        geometries = (GeometryRecord("g", 1, width=width, height=200.0, length=3000.0),)
    return _snapshot(
        elements=(ElementRecord("g", 1, "beam"),),
        attributes=(
            AttributeRecord(
                "g", 1, name="Stud", material_name=material, group_name=group, ifc_type=ifc
            ),
        ),
        geometries=geometries,
    )


_MATERIAL = """\
Feature: Framing
  Scenario: Studs are pine
    Given the model
    Then every beam named "Stud" has material "Pine"
"""

_IFC = """\
Feature: Framing
  Scenario: Studs are beams
    Then every beam named "Stud" has ifc type "IfcBeam"
"""

_GROUP = """\
Feature: Framing
  Scenario: Studs are framed
    Then every beam named "Stud" has group "Frame"
"""

_WIDTH = """\
Feature: Framing
  Scenario: Studs are 80
    Then every beam named "Stud" has width 80
"""

_WIDTH_RANGE = """\
Feature: Framing
  Scenario: Studs are in range
    Then every beam named "Stud" has width between 70 and 90
"""

_ANY_ELEMENT = """\
Feature: Framing
  Scenario: named
    Then every element named "Stud" has material "Pine"
"""

_COUNT_NAMED = """\
Feature: Framing
  Scenario: one stud
    Then there are 1 beams named "Stud"
"""

_COUNT_TYPE = """\
Feature: Framing
  Scenario: one beam
    Then there are 1 beams
"""

_COUNT_ZERO = """\
Feature: Framing
  Scenario: no plates
    Then there are 0 plates
"""


def test_material_phrase_passes_and_fails() -> None:
    assert run_features(_stud(), _MATERIAL).ok
    assert not run_features(_stud(material="Oak"), _MATERIAL).ok
    assert not run_features(_stud(material=""), _MATERIAL).ok


def test_ifc_phrase_passes_and_fails() -> None:
    assert run_features(_stud(), _IFC).ok
    assert not run_features(_stud(ifc="IfcWall"), _IFC).ok
    assert not run_features(_stud(ifc=""), _IFC).ok


def test_group_phrase_passes_and_fails() -> None:
    assert run_features(_stud(), _GROUP).ok
    assert not run_features(_stud(group="Other"), _GROUP).ok


def test_exact_and_range_dimensions() -> None:
    assert run_features(_stud(width=80.0), _WIDTH).ok
    assert not run_features(_stud(width=81.0), _WIDTH).ok
    assert run_features(_stud(width=80.0), _WIDTH_RANGE).ok
    assert not run_features(_stud(width=60.0), _WIDTH_RANGE).ok


def test_missing_geometry_on_dimension_step_is_error() -> None:
    report = run_features(_stud(width=None), _WIDTH)
    assert not report.ok
    assert report.failures
    assert "no geometry" in report.failures[0].message


def test_zero_match_every_is_error() -> None:
    empty = _snapshot()
    report = run_features(empty, _MATERIAL)
    assert not report.ok
    assert report.failures


def test_there_are_zero_passes_on_empty() -> None:
    assert run_features(_snapshot(), _COUNT_ZERO).ok
    plate = _snapshot(
        elements=(ElementRecord("g", 1, "plate"),),
        attributes=(AttributeRecord("g", 1, name="Sheet"),),
    )
    assert not run_features(plate, _COUNT_ZERO).ok


def test_count_phrases() -> None:
    assert run_features(_stud(), _COUNT_NAMED).ok
    assert run_features(_stud(), _COUNT_TYPE).ok
    assert not run_features(_snapshot(), _COUNT_NAMED).ok


def test_every_element_named_has_no_type_filter() -> None:
    plate = _snapshot(
        elements=(ElementRecord("g", 1, "plate"),),
        attributes=(AttributeRecord("g", 1, name="Stud", material_name="Pine"),),
    )
    assert run_features(plate, _ANY_ELEMENT).ok
