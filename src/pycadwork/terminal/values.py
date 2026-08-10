"""Value objects for the terminal runner — raw CLI strings validated once.

cadwork's command line carries a few structured values (a licence string, a
plotter/laser frame selection) and two small closed vocabularies (the live-update
target, the installed user type). Wrapping each in a frozen, self-validating value
object — the same idiom as :class:`pycadwork.persistence.UserAttributeIndices` and
:class:`pycadwork.building.BuildingName` — keeps malformed input from reaching the
``/SLASH`` command line and gives the translation layer typed arguments instead of
bare ``str``. Bad input raises :class:`ValueError` at construction; the CLI turns
that into an ``argparse`` error (exit code 2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

#: A plotter/laser frame spec: a ``;``-separated list of frames or ``n-m`` ranges.
_FRAME_SPEC = re.compile(r"^\d+(-\d+)?(;\d+(-\d+)?)*$")

#: argparse ``choices`` for ``update`` — kept beside :class:`UpdateTarget`.
UPDATE_CHOICES: tuple[str, ...] = ("2d", "all", "all-force")

#: argparse ``choices`` for ``install --user`` — kept beside :class:`UserType`.
USER_CHOICES: tuple[str, ...] = ("holz", "ing", "easy")


@dataclass(frozen=True, slots=True)
class Licence:
    """A cadwork licence string, e.g. ``WEB Licence:00.000.0#1;PASSWORD``.

    The value is ``<Type>:<payload>`` — a ``WEB Licence:``/``USB Memory:`` prefix
    followed by the licence payload. Only the shape is checked (non-empty, one
    ``:`` separator); the payload itself is opaque to us.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise ValueError("licence must be non-empty")
        if ":" not in stripped:
            raise ValueError(
                'licence must look like "<Type>:<payload>", e.g. '
                '"WEB Licence:00.000.0#1;PASSWORD" or '
                f'"USB Memory:000010123456789"; got {self.value!r}'
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class FrameSelection:
    """A plotter/laser frame selection: ``A`` (all) or a spec like ``1-2;5;7``."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if stripped.upper() == "A":
            object.__setattr__(self, "value", "A")
            return
        if not _FRAME_SPEC.match(stripped):
            raise ValueError(
                'frame selection must be "A" (all) or a spec like "1-2;5;7"; '
                f"got {self.value!r}"
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


class UpdateTarget(Enum):
    """Which modules ``/LIVEUPDATE`` refreshes; value is the cadwork token."""

    TWO_D = "2D"
    ALL = "ALL"
    ALL_FORCE = "ALL+"

    @classmethod
    def from_choice(cls, choice: str) -> UpdateTarget:
        mapping = {"2d": cls.TWO_D, "all": cls.ALL, "all-force": cls.ALL_FORCE}
        try:
            return mapping[choice]
        except KeyError:
            raise ValueError(f"unknown update target {choice!r}") from None


class UserType(Enum):
    """The installed user profile; value is the full cadwork flag token."""

    HOLZ = "/USER_HOLZ"
    ING = "/USER_ING"
    EASY = "/USER_EASY"

    @classmethod
    def from_choice(cls, choice: str) -> UserType:
        mapping = {"holz": cls.HOLZ, "ing": cls.ING, "easy": cls.EASY}
        try:
            return mapping[choice]
        except KeyError:
            raise ValueError(f"unknown user type {choice!r}") from None
