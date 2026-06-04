"""Value-object validation, equality, and ``str`` for building/storey names."""

from __future__ import annotations

import pytest

from pycadwork import BuildingName, StoreyName


@pytest.mark.parametrize("cls", [BuildingName, StoreyName])
def test_rejects_empty_and_whitespace(cls):
    with pytest.raises(ValueError):
        cls("")
    with pytest.raises(ValueError):
        cls("   ")


@pytest.mark.parametrize("cls", [BuildingName, StoreyName])
def test_str_returns_value(cls):
    assert str(cls("Building A")) == "Building A"


@pytest.mark.parametrize("cls", [BuildingName, StoreyName])
def test_equality_and_hash_by_value(cls):
    assert cls("X") == cls("X")
    assert cls("X") != cls("Y")
    assert {cls("X"), cls("X")} == {cls("X")}


def test_value_is_accessible():
    assert BuildingName("B").value == "B"
    assert StoreyName("S").value == "S"
