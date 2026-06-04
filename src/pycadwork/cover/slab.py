"""Slab: an aggregate flagged as framed/solid floor."""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import SLAB_KINDS
from pycadwork.cover.aggregate import Aggregate
from pycadwork.element.registry import AGGREGATE, register_element


@register_element(lambda s: s.is_framed_floor or s.is_solid_floor, priority=AGGREGATE)
class Slab(Aggregate):
    """A cadwork floor — framed or solid."""

    _ALLOWED_KINDS = SLAB_KINDS
