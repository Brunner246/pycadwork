"""ConnectorAxis: line-anchored standard connector from the cadwork library."""

from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.linear import LinearElement
from pycadwork.element.registry import SPECIAL, register_element
from pycadwork.geometry import Segment


@register_element(lambda s: s.is_connector_axis, priority=SPECIAL)
class ConnectorAxis(LinearElement):
    """A cadwork standard connector — a named connector along a line segment."""

    __slots__ = ()

    @classmethod
    def create_standard(cls, axis: Segment, name: str) -> Self:
        eid = cadwork.elements.create_standard_connector(axis, name)
        return cls(eid)
