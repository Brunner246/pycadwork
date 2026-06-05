"""MEP leaf elements: circular and rectangular runs (pipes / ducts).

Both are path-anchored and axis-derived (start/end points, length, frame on
``self.geometry``), but they differ in cross-section surface. A rectangular run
is a :class:`pycadwork.element.linear.LinearElement`: its ``geometry`` exposes
``width`` (the duct width) and ``height`` (the depth). A circular run instead
binds :class:`pycadwork.element.components.CircularGeometry`, whose only
cross-section surface is :attr:`~...CircularGeometry.diameter` /
:attr:`~...CircularGeometry.radius` -- ``width`` / ``height`` are suppressed,
since a pipe has no rectangular section.

Creation takes the centreline path as a sequence of points (minimum two); the
cwapi3d API derives the run's orientation itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Self

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.components import CircularGeometry
from pycadwork.element.linear import LinearElement
from pycadwork.element.registry import PRIMITIVE, register_element
from pycadwork.geometry import Point3D


def _path(points: Sequence[Point3D]) -> list[Point3D]:
    """Validate an MEP centreline path: at least two points, any length above."""
    path = list(points)
    if len(path) < 2:
        raise ValueError("MEP path requires at least two points")
    return path


@register_element(lambda s: s.is_circular_mep, priority=PRIMITIVE)
class CircularMep(Element[CircularGeometry]):
    """A cadwork circular MEP run -- a pipe, defined by a diameter and path."""

    __slots__ = ()

    _geometry_cls = CircularGeometry

    @property
    def diameter(self) -> float:
        """The run's diameter (its single circular cross-section dimension)."""
        return self.geometry.diameter

    @classmethod
    def create(cls, diameter: float, points: Sequence[Point3D]) -> Self:
        eid = cadwork.elements.create_circular_mep(diameter, _path(points))
        return cls(eid)


@register_element(lambda s: s.is_rectangular_mep, priority=PRIMITIVE)
class RectangularMep(LinearElement):
    """A cadwork rectangular MEP run -- a duct, defined by width, depth, path.

    ``width`` maps to ``geometry.width`` and ``depth`` to ``geometry.height``.
    """

    __slots__ = ()

    @classmethod
    def create(cls, width: float, depth: float, points: Sequence[Point3D]) -> Self:
        eid = cadwork.elements.create_rectangular_mep(width, depth, _path(points))
        return cls(eid)
