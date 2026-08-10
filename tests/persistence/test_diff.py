"""The pure snapshot diff classifies elements as new / dirty / removed."""

from __future__ import annotations

from pycadwork.persistence._diff import diff
from pycadwork.persistence.records import ElementRecord, ModelSnapshot, ProjectRecord


def _snapshot(*ids: int) -> ModelSnapshot:
    return ModelSnapshot(
        project=ProjectRecord("g"),
        elements=tuple(ElementRecord("g", i, "beam") for i in ids),
    )


def test_classifies_new_dirty_and_removed() -> None:
    current = _snapshot(1, 2)
    target = _snapshot(2, 3)

    result = diff(current, target)

    assert result.new_ids == (3,)
    assert result.dirty_ids == (2,)
    assert tuple(r.id for r in result.removed) == (1,)


def test_carries_target_through_unchanged() -> None:
    target = _snapshot(1)
    result = diff(_snapshot(), target)
    assert result.target is target


def test_identical_snapshots_are_all_dirty() -> None:
    result = diff(_snapshot(1, 2), _snapshot(1, 2))
    assert result.new_ids == ()
    assert result.dirty_ids == (1, 2)
    assert result.removed == ()


def test_ids_are_returned_sorted() -> None:
    result = diff(_snapshot(), _snapshot(3, 1, 2))
    assert result.new_ids == (1, 2, 3)
