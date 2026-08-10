"""Act on a collision report in the model — an opt-in side effect.

:func:`check_collisions` is pure: it reads geometry and returns a report.
:func:`highlight_clashes` is the separate, explicit step that makes the
findings visible, recolouring (and optionally commenting) the offending
elements through the existing visualization / attributes seam so a user can
locate them in cadwork.
"""

from __future__ import annotations

from collections.abc import Collection

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.collision.records import CollisionKind, CollisionReport

#: Default cadwork colour index applied to clashing elements (a vivid red).
DEFAULT_CLASH_COLOR = 6


def highlight_clashes(
    report: CollisionReport,
    *,
    color_id: int = DEFAULT_CLASH_COLOR,
    comment: str | None = None,
    kinds: Collection[CollisionKind] = (CollisionKind.OVERLAP,),
) -> list[ElementId]:
    """Recolour every element taking part in a clash of ``kinds``.

    Returns the affected element ids (sorted, de-duplicated). When ``comment``
    is given it is also written to each element's comment attribute. Pure
    delegation to the visualization / attributes seam — the report itself is
    never mutated.
    """
    wanted = frozenset(kinds)
    ids = sorted(
        {
            ElementId(eid)
            for clash in report.clashes
            if clash.kind in wanted
            for eid in (clash.first_id, clash.second_id)
        }
    )
    if not ids:
        return []

    cadwork.visualization.set_color(ids, color_id)
    if comment is not None:
        cadwork.attributes.set_comment(ids, comment)
    return ids
