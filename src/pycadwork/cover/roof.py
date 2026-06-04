"""Roof: an aggregate flagged as framed/solid roof."""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import ROOF_KINDS
from pycadwork.cover.aggregate import Aggregate
from pycadwork.element.registry import AGGREGATE, register_element


@register_element(lambda s: s.is_framed_roof or s.is_solid_roof, priority=AGGREGATE)
class Roof(Aggregate):
    """A cadwork roof — framed or solid."""

    _ALLOWED_KINDS = ROOF_KINDS
