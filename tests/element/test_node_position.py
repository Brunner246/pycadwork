"""Node exposes ``position`` via ``node.geometry``; it does not inherit
linear-element geometry.
"""
from __future__ import annotations

from pycadwork import Node, Point3D
from pycadwork.element import LinearElement, OrientedElement


def test_node_position_round_trips():
    p = Point3D(10.0, 20.0, 30.0)
    node = Node.create(p)
    assert node.geometry.position == p


def test_node_is_not_a_linear_or_oriented_element():
    node = Node.create(Point3D(0, 0, 0))
    assert not isinstance(node, LinearElement)
    assert not isinstance(node, OrientedElement)
    # Sanity: linear-only geometry is genuinely absent from the geometry component.
    assert not hasattr(node.geometry, "axis_points")
    assert not hasattr(node.geometry, "axis_frame")
    assert not hasattr(node.geometry, "frame")
    assert not hasattr(node.geometry, "length")
