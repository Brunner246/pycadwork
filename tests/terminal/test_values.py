"""Value-object validation for the terminal runner."""

from __future__ import annotations

import pytest

from pycadwork.terminal.values import (
    FrameSelection,
    Licence,
    UpdateTarget,
    UserType,
)


@pytest.mark.parametrize(
    "value",
    [
        "WEB Licence:00.000.0#1;PASSWORD",
        "USB Memory:000010123456789",
    ],
)
def test_licence_accepts_typed_strings(value: str) -> None:
    assert str(Licence(value)) == value


def test_licence_strips_surrounding_whitespace() -> None:
    assert str(Licence("  USB Memory:123  ")) == "USB Memory:123"


@pytest.mark.parametrize("value", ["", "   ", "no-separator-here"])
def test_licence_rejects_malformed(value: str) -> None:
    with pytest.raises(ValueError):
        Licence(value)


@pytest.mark.parametrize("value", ["A", "a", "1-2;5;7", "3", "10-20;30"])
def test_frame_selection_accepts_all_and_specs(value: str) -> None:
    FrameSelection(value)


def test_frame_selection_normalizes_all_to_uppercase() -> None:
    assert str(FrameSelection("a")) == "A"


@pytest.mark.parametrize("value", ["", "PDF", "1,2,3", "1-", "-2", "1;;2", "x"])
def test_frame_selection_rejects_malformed(value: str) -> None:
    with pytest.raises(ValueError):
        FrameSelection(value)


def test_update_target_maps_choices_to_tokens() -> None:
    assert UpdateTarget.from_choice("2d").value == "2D"
    assert UpdateTarget.from_choice("all").value == "ALL"
    assert UpdateTarget.from_choice("all-force").value == "ALL+"


def test_user_type_maps_choices_to_flags() -> None:
    assert UserType.from_choice("holz").value == "/USER_HOLZ"
    assert UserType.from_choice("ing").value == "/USER_ING"
    assert UserType.from_choice("easy").value == "/USER_EASY"


def test_enum_from_choice_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        UpdateTarget.from_choice("nope")
    with pytest.raises(ValueError):
        UserType.from_choice("nope")
