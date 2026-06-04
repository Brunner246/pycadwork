"""Plate: cadwork's "panel" — exposed as Plate to match user vocabulary."""

from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.oriented import OrientedElement
from pycadwork.element.registry import PRIMITIVE, register_element
from pycadwork.geometry import AxisFrame, AxisPoints, PanelSection


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
