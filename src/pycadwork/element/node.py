"""Minimal wrappers for primitive elements: Node, Line."""
from __future__ import annotations

from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.components import NodeGeometry
from pycadwork.element.linear import LinearElement
from pycadwork.element.registry import GEOMETRIC, register_element
from pycadwork.geometry import Point3D, Segment


@register_element(lambda s: s.is_node, priority=GEOMETRIC)
class Node(Element[NodeGeometry]):
    """A cadwork node — a single positioned point in the model.

    A node has no axis or frame; the only meaningful geometry is its
    ``position`` (read via ``node.geometry.position``). Bulk queries (AABB,
    BRep, COG) on ``node.geometry`` still work and report degenerate results.
    """

    __slots__ = ()

    _geometry_cls = NodeGeometry

    @classmethod
    def create(cls, position: Point3D) -> Self:
        eid = cadwork.elements.create_node(position)
        return cls(eid)


@register_element(lambda s: s.is_line, priority=GEOMETRIC)
class Line(LinearElement):
    """A cadwork line element defined by two endpoints."""

    __slots__ = ()

    @classmethod
    def create(cls, axis: Segment) -> Self:
        eid = cadwork.elements.create_line_points(axis)
        return cls(eid)
