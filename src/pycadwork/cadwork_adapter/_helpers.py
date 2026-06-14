"""Module-private helpers shared by the cwapi3d sub-adapters.

Centralises the point-tuple conversions and the GroupingMode-to-cadwork-enum
mapping so the sub-adapters stay focused on their own surface.
"""

from __future__ import annotations

from typing import Any

from pycadwork.cadwork_adapter.types import GroupingMode, PointTuple
from pycadwork.geometry.plane3d import Plane3D
from pycadwork.geometry.point3d import Point3D


def to_cadwork_point(cadwork_module: Any, p: Point3D) -> Any:
    """Wrap a :class:`Point3D` in cadwork's native ``point_3d``."""
    return cadwork_module.point_3d(p.x, p.y, p.z)


def plane_to_cadwork_args(cadwork_module: Any, plane: Plane3D) -> tuple[Any, float]:
    """Translate a :class:`Plane3D` into cwapi3d's ``(normal, distance)`` pair.

    cwapi3d describes a cut plane as ``n . x = distance`` (distance from the
    global origin along the normal); :class:`Plane3D` stores ``d = -n . P0``,
    so the distance is ``-plane.d()``.
    """
    n = plane.normal
    return (cadwork_module.point_3d(n.x, n.y, n.z), -plane.d())


def to_tuple(p: Any) -> PointTuple:
    """Project a cadwork ``point_3d`` (or any ``.x/.y/.z`` object) into a tuple."""
    return (float(p.x), float(p.y), float(p.z))


def grouping_mode_to_cadwork(cadwork_module: Any, mode: GroupingMode) -> Any:
    """Translate a :class:`GroupingMode` into cadwork's ``element_grouping_type``."""
    egt = cadwork_module.element_grouping_type
    return egt.subgroup if mode is GroupingMode.SUBGROUP else egt.group


def grouping_mode_from_cadwork(value: int) -> GroupingMode:
    """The reverse mapping. cadwork uses ``2`` for subgroup, anything else for group."""
    return GroupingMode.SUBGROUP if int(value) == 2 else GroupingMode.GROUP
