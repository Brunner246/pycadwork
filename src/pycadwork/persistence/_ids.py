"""Typed identifiers for the persistence records.

These are :func:`typing.NewType` aliases, not classes: at runtime an
``ElementId`` *is* the ``int`` it wraps and a ``ProjectGuid`` *is* its ``str``,
so they bind to SQLite and round-trip through the gateways with zero overhead
and no unwrapping. Their only job is static — a type checker rejects passing a
``ProjectGuid`` where a ``CadworkGuid`` belongs, or transposing the
``(container_id, member_id)`` pair — the positional mix-ups bare ``str`` /
``int`` fields silently invite.

Only *identity* is wrapped. Descriptive payload fields (``name``, ``comment``,
``material_name``, building / storey names, …) stay primitive: they are never
confused positionally with an id, so wrapping them would be noise.

Every alias here is defined in :mod:`pycadwork.value_types` — the single source
of truth for every typed value in the package — and re-exported from this module
so record code keeps one import site for every identifier. ``ElementId`` is the
canonical seam id; ``ContainerId`` and ``MemberId`` layer on it — a container
and a member are both elements — so either is accepted where an ``ElementId`` is
expected (e.g. as a key into the stored→model id map) while remaining mutually
distinct, so the two cannot be transposed.
"""

from __future__ import annotations

from pycadwork.value_types import (
    CadworkGuid,
    ContainerId,
    ElementId,
    MemberId,
    ProjectGuid,
)

__all__ = [
    "CadworkGuid",
    "ContainerId",
    "ElementId",
    "MemberId",
    "ProjectGuid",
]
