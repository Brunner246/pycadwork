"""Live-model work units — snapshot, apply, restore, undo, report.

:class:`WorkUnit` is a context manager over tracked live elements. It is
**not** :class:`pycadwork.persistence.UnitOfWork` (that one commits SQL).
"""

from __future__ import annotations

from pycadwork.work.report import AttributeDiff, WorkReport, WorkStatus, WorkStep
from pycadwork.work.unit import WorkUnit

__all__ = [
    "AttributeDiff",
    "WorkReport",
    "WorkStatus",
    "WorkStep",
    "WorkUnit",
]
