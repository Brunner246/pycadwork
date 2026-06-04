"""Wall: an aggregate flagged as framed/solid/log wall."""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import WALL_KINDS
from pycadwork.cover.aggregate import Aggregate
from pycadwork.element.registry import AGGREGATE, register_element


@register_element(
    lambda s: s.is_framed_wall or s.is_solid_wall or s.is_log_wall,
    priority=AGGREGATE,
)
class Wall(Aggregate):
    """A cadwork wall — framed, solid, or log."""

    _ALLOWED_KINDS = WALL_KINDS
