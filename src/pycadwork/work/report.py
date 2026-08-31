"""Frozen result of a :class:`~pycadwork.work.unit.WorkUnit`.

These types describe what a unit did — committed vs rolled back, per-step
outcome, before/after attribute diffs against the enter/track snapshot.
They are not quantity-takeoff rows; those live in
:mod:`pycadwork.reporting.records`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkStatus(Enum):
    """Outcome of a work-unit or of one of its steps."""

    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True, slots=True)
class AttributeDiff:
    """One attribute whose value after a step differs from the snapshot."""

    element_id: int
    attribute: str
    before: object
    after: object


@dataclass(frozen=True, slots=True)
class WorkStep:
    """One ``apply`` / ``run`` invocation inside a unit."""

    name: str
    status: WorkStatus
    diffs: tuple[AttributeDiff, ...]


@dataclass(frozen=True, slots=True)
class WorkReport:
    """Finished journal of a :class:`~pycadwork.work.unit.WorkUnit`.

    Frozen in ``__exit__``. ``diffs`` flattens every step's diffs in step
    order; each step's diffs are versus the enter/track snapshot, not the
    previous step.
    """

    status: WorkStatus
    element_ids: tuple[int, ...]
    steps: tuple[WorkStep, ...]

    @property
    def diffs(self) -> tuple[AttributeDiff, ...]:
        """Flatten every step's diffs in step order."""
        return tuple(diff for step in self.steps for diff in step.diffs)
