"""LinearElement: an element defined by an axis (p1 → p2 with p3 as up hint).

Subclasses: :class:`Beam`, :class:`Drilling`, :class:`Line`. They share the
axis-derived geometry surface via :class:`LinearGeometry`, which lives on
``self.geometry``: start/end/third points, the world-space
:class:`Frame3D`, length, cross-section width/height, the composite value
objects :class:`AxisPoints` / :class:`AxisFrame`, and the OBB.
"""
from __future__ import annotations

from pycadwork.element.base import Element
from pycadwork.element.components import LinearGeometry


class LinearElement(Element[LinearGeometry]):
    """Element whose geometry is anchored on a line — Beam, Drilling, Line."""

    __slots__ = ()

    _geometry_cls = LinearGeometry
