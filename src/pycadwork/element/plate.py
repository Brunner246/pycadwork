"""Plate: cadwork's "panel" — exposed as Plate to match user vocabulary."""

from __future__ import annotations

from typing import Self

from collections.abc import Sequence

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.oriented import OrientedElement
from pycadwork.element.registry import PRIMITIVE, register_element
from pycadwork.geometry import AxisFrame, AxisPoints, PanelSection, Point3D


@register_element(lambda s: s.is_panel, priority=PRIMITIVE)
class Plate(OrientedElement):
    """A cadwork panel — flat sheet/board element."""

    __slots__ = ()

    @classmethod
    def create_rectangular(cls, section: PanelSection, axis: AxisPoints) -> Self:
        eid = cadwork.elements.create_rectangular_panel_points(section, axis)
        return cls(eid)

    @classmethod
    def create_rectangular_from_vectors(
        cls, section: PanelSection, frame: AxisFrame
    ) -> Self:
        eid = cadwork.elements.create_rectangular_panel_vectors(section, frame)
        return cls(eid)

    @classmethod
    def create_polygon(
        cls,
        vertices: Sequence[Point3D],
        thickness: float,
        x_local_direction: Point3D,
        z_local_direction: Point3D,
    ) -> Self:
        """Create a panel from a planar polygon, extruded by ``thickness``.

        ``z_local_direction`` is the panel normal — the thickness (extrusion)
        axis; ``x_local_direction`` is a meaningful in-plane orientation vector.
        The vertices must wind counter-clockwise about the normal so the panel
        faces outward and its local frame stays right-handed (otherwise cadwork
        builds an inverted/degenerate solid).
        """
        eid = cadwork.elements.create_polygon_panel(
            list(vertices), float(thickness), x_local_direction, z_local_direction
        )
        return cls(eid)
