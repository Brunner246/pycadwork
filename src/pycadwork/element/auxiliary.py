"""AuxiliaryElement: a helper element produced by surface extrusion."""

from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.registry import SPECIAL, register_element
from pycadwork.element.surface import Surface
from pycadwork.geometry import Point3D, Vector3D


@register_element(lambda s: s.is_auxiliary, priority=SPECIAL)
class AuxiliaryElement(Element):
    """A cadwork auxiliary element."""

    __slots__ = ()

    @classmethod
    def from_surface_extrusion(cls, surface: Surface, vector: Vector3D) -> Self:
        eid = cadwork.elements.extrude_surface_to_auxiliary_vector(
            surface.id, Point3D(vector.x, vector.y, vector.z)
        )
        return cls(eid)
