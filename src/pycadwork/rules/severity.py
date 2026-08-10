"""Severity — the one shared enum of the rules package.

A leaf module (imports only :mod:`enum`) so both the records and the engine can
depend on it without an import cycle. :class:`Severity` is an :class:`~enum.IntEnum`
so violations sort by it deterministically and a numeric ``min_severity`` cut
(``>=``) reads naturally.
"""

from __future__ import annotations

from enum import IntEnum


class Severity(IntEnum):
    """How serious a rule violation is. Ordered ``INFO < WARNING < ERROR``."""

    INFO = 10
    WARNING = 20
    ERROR = 30
