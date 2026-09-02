"""Gherkin run results — frozen DTOs and the authoring error type.

Assertion failures are data on :class:`FeatureReport`. Parse mistakes, unknown
steps, and unmatched ``When`` raise :class:`GherkinError` before ``check``.
"""

from __future__ import annotations

from dataclasses import dataclass


class GherkinError(ValueError):
    """Parse, unknown-step, or unmatched-When error. Raised before ``check``."""


@dataclass(frozen=True, slots=True)
class StepFailure:
    """One compiled step that produced a rule violation."""

    scenario: str
    step: str
    rule_id: str
    element_id: int
    element_type: str
    message: str


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """One scenario after ``check``, with its mapped step failures."""

    name: str
    ok: bool
    failures: tuple[StepFailure, ...]


@dataclass(frozen=True, slots=True)
class FeatureReport:
    """The result of one :func:`~pycadwork.gherkin.run_features` pass.

    ``violations`` is scenario order, then the engine's order within a
    scenario. ``rules_run`` is the engine's sorted rule ids.
    """

    title: str
    scenarios: tuple[ScenarioResult, ...]
    violations: tuple[StepFailure, ...] = ()
    rules_run: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """True when every scenario is ok (no ERROR-severity compiled failure)."""
        return all(scenario.ok for scenario in self.scenarios)

    @property
    def failures(self) -> tuple[StepFailure, ...]:
        """Alias for :attr:`violations`."""
        return self.violations
