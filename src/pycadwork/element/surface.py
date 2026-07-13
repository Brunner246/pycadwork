"""Surface: cadwork surface element built from a polygon of points."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.registry import GEOMETRIC, register_element
from pycadwork.geometry import Point3D

if TYPE_CHECKING:
    from pycadwork.element.plate import Plate


@register_element(lambda s: s.is_surface, priority=GEOMETRIC)
class Surface(Element):
    """A cadwork surface element."""

    __slots__ = ()

    @classmethod
    def create(cls, points: list[Point3D]) -> Self:
        eid = cadwork.elements.create_surface_points(points)
        return cls(eid)

    def extrude_to_panel(self, thickness: float) -> "Plate":
        """Extrude this surface along its own normal by ``thickness`` into a Plate."""
        from pycadwork.element.plate import Plate

        normal = self.geometry.brep.face_at(0).normal.normalized()
        displacement = Point3D(
            normal.x * thickness, normal.y * thickness, normal.z * thickness
        )
        eid = cadwork.elements.extrude_surface_to_panel_vector(self.id, displacement)
        return Plate(eid)
