"""Pure storey classification — no cadwork involved."""

from __future__ import annotations

import pytest

from pycadwork import Storey, StoreyName, StoreyStack


def _stack() -> StoreyStack:
    # Three storeys at 0 / 3000 / 6000, given out of order on purpose.
    return StoreyStack(
        [
            Storey(StoreyName("S1"), 3000.0),
            Storey(StoreyName("S0"), 0.0),
            Storey(StoreyName("S2"), 6000.0),
        ]
    )


def test_constructor_sorts_ascending_by_elevation():
    stack = _stack()
    assert [s.name.value for s in stack.storeys] == ["S0", "S1", "S2"]
    assert len(stack) == 3


def test_empty_stack_raises():
    with pytest.raises(ValueError):
        StoreyStack([])


def test_clean_in_storey_assignment():
    result = _stack().classify(100.0, 2900.0)
    assert result.storey.name.value == "S0"
    assert result.spans is False


def test_topmost_open_interval():
    result = _stack().classify(6500.0, 6900.0)
    assert result.storey.name.value == "S2"
    assert result.spans is False


def test_straddle_assigns_majority_and_marks_spans():
    # [2900, 3300]: 100 in S0, 300 in S1 -> S1 majority, spans.
    result = _stack().classify(2900.0, 3300.0)
    assert result.storey.name.value == "S1"
    assert result.spans is True


def test_straddle_tie_breaks_to_lower_storey():
    # [2500, 3500]: 500 in S0, 500 in S1 -> tie favours the lower storey.
    result = _stack().classify(2500.0, 3500.0)
    assert result.storey.name.value == "S0"
    assert result.spans is True


def test_below_lowest_floor_marks_spans():
    result = _stack().classify(-500.0, -100.0)
    assert result.storey.name.value == "S0"
    assert result.spans is True


def test_degenerate_extent_picks_containing_interval():
    # A node at exactly a storey plane: lands in that storey, never spans.
    result = _stack().classify(3000.0, 3000.0)
    assert result.storey.name.value == "S1"
    assert result.spans is False


def test_degenerate_extent_below_lowest_does_not_span():
    result = _stack().classify(-100.0, -100.0)
    assert result.storey.name.value == "S0"
    assert result.spans is False


def test_touching_a_plane_does_not_count_as_spanning():
    # Sits in S0 and just reaches the S1 floor; the epsilon keeps it single.
    result = _stack().classify(100.0, 3000.0)
    assert result.storey.name.value == "S0"
    assert result.spans is False
