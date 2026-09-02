"""Gherkin AST — feature / scenario / step nodes after dialect expansion.

Scenario Outline rows are already substituted and Background steps already
prepended; the compiler walks a flat list of scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Step:
    """One Given/When/Then (And/But already rewritten to the inherited kind)."""

    kind: str
    text: str
    line: int
    keyword: str


@dataclass(frozen=True, slots=True)
class Scenario:
    """One runnable scenario (an Outline row is one of these)."""

    name: str
    steps: tuple[Step, ...]
    line: int
    outline_row: int | None = None


@dataclass(frozen=True, slots=True)
class Feature:
    """One parsed feature file, ready to compile."""

    title: str
    scenarios: tuple[Scenario, ...]
    description: str = ""
