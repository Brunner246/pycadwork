"""Drilling: a cylindrical hole element defined by two endpoints + diameter."""
from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.linear import LinearElement
from pycadwork.element.registry import SPECIAL, register_element
from pycadwork.geometry import Segment


@register_element(lambda s: s.is_drilling, priority=SPECIAL)
class Drilling(LinearElement):
    """A cadwork drilling axis."""

    __slots__ = ()

    @classmethod
    def create(cls, diameter: float, axis: Segment) -> Self:
        eid = cadwork.elements.create_drilling_points(diameter, axis)
        return cls(eid)
