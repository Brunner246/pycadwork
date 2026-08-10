"""Per-concern wrappers that ``Element`` aggregates.

Each component holds an :class:`ElementId` and routes attribute / geometry
calls to the active backend. ``Element`` exposes them as ``elem.attrs`` and
``elem.geometry`` instead of inheriting their methods directly, so the
class surface stays small and the concerns stay obvious at the call site.
"""

from __future__ import annotations

from pycadwork.element.components.attributes import Attributes
from pycadwork.element.components.geometry import (
    CircularGeometry,
    Geometry,
    LinearGeometry,
    NodeGeometry,
    OrientedGeometry,
)

__all__ = [
    "Attributes",
    "CircularGeometry",
    "Geometry",
    "LinearGeometry",
    "NodeGeometry",
    "OrientedGeometry",
]
