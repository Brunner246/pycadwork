"""Surface: cadwork surface element built from a polygon of points."""

from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.registry import GEOMETRIC, register_element
from pycadwork.geometry import Point3D


@register_element(lambda s: s.is_surface, priority=GEOMETRIC)
class Surface(Element):
    """A cadwork surface element."""

    __slots__ = ()

    @classmethod
    def create(cls, points: list[Point3D]) -> Self:
        eid = cadwork.elements.create_surface_points(points)
        return cls(eid)
