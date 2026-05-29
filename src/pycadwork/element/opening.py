"""Opening: a rectangular panel flagged as an opening (subtracts from covers)."""
from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.oriented import OrientedElement
from pycadwork.element.registry import SPECIAL, register_element
from pycadwork.geometry import AxisPoints, PanelSection


@register_element(lambda s: s.is_opening, priority=SPECIAL)
class Opening(OrientedElement):
    """A cadwork opening — a panel marked with the opening flag."""

    __slots__ = ()

    @classmethod
    def create_rectangular(
        cls, section: PanelSection, axis: AxisPoints
    ) -> Self:
        eid = cadwork.elements.create_rectangular_panel_points(section, axis)
        cadwork.attributes.set_opening([eid])
        return cls(eid)
