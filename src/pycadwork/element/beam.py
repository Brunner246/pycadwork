"""Beam: rectangular / circular / square / polygon-section linear members."""

from __future__ import annotations

from enum import Enum
from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.linear import LinearElement
from pycadwork.element.registry import PRIMITIVE, register_element
from pycadwork.geometry import AxisFrame, AxisPoints, RectSection


class CrossSection(Enum):
    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"
    SQUARE = "square"
    POLYGON = "polygon"


@register_element(
    lambda s: s.is_rectangular_beam
    or s.is_circular_beam
    or s.is_square_beam
    or s.is_polygon_beam
    or s.is_steel_shape
    or s.is_beam,
    priority=PRIMITIVE,
)
class Beam(LinearElement):
    """A cadwork beam — rectangular, circular, square, or polygon-section."""

    __slots__ = ()

    # ---- introspection ----

    @property
    def cross_section(self) -> CrossSection:
        snap = self.cadwork_type
        if snap.is_circular_beam:
            return CrossSection.CIRCULAR
        if snap.is_square_beam:
            return CrossSection.SQUARE
        if snap.is_polygon_beam:
            return CrossSection.POLYGON
        return CrossSection.RECTANGULAR

    # ---- creation ----

    @classmethod
    def create_rectangular(cls, section: RectSection, axis: AxisPoints) -> Self:
        eid = cadwork.elements.create_rectangular_beam_points(section, axis)
        return cls(eid)

    @classmethod
    def create_rectangular_from_vectors(
        cls, section: RectSection, frame: AxisFrame
    ) -> Self:
        eid = cadwork.elements.create_rectangular_beam_vectors(section, frame)
        return cls(eid)

    @classmethod
    def create_circular(cls, diameter: float, axis: AxisPoints) -> Self:
        eid = cadwork.elements.create_circular_beam_points(diameter, axis)
        return cls(eid)

    @classmethod
    def create_square(cls, width: float, axis: AxisPoints) -> Self:
        eid = cadwork.elements.create_square_beam_points(width, axis)
        return cls(eid)
