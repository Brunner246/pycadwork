"""OrientedElement: a planar element with a 3D frame and planar extent.

Subclass: :class:`Plate`. Shares the axis-frame surface with
:class:`LinearElement` (panels are also constructed from axis points or an
axis frame) but ``self.geometry`` exposes ``thickness`` as the semantically
appropriate alias for the backend's ``height`` channel.
"""
from __future__ import annotations

from pycadwork.element.base import Element
from pycadwork.element.components import OrientedGeometry


class OrientedElement(Element[OrientedGeometry]):
    """Element with a 3D frame and 2D planar extent — Plate."""

    __slots__ = ()

    _geometry_cls = OrientedGeometry
