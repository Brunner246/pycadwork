"""Value objects for the BMT structure — no raw strings cross the boundary.

A building and a storey are both identified by name in cadwork's
``bim_controller``. Wrapping each in a frozen, validated value object keeps
empty/whitespace names from silently reaching the seam and gives the assigner
a typed argument instead of a bare ``str``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuildingName:
    """A non-empty building identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("BuildingName must be non-empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class StoreyName:
    """A non-empty storey identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("StoreyName must be non-empty")

    def __str__(self) -> str:
        return self.value
