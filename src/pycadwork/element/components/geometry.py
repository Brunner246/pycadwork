"""Geometry components attached to every :class:`Element`.

Four classes, walked by inheritance:

* :class:`Geometry` — bulk queries shared by every element (volume, weight,
  COG, AABB, BRep). Bound on bare ``Element`` and :class:`Surface`.
* :class:`LinearGeometry` — adds axis points, frame, length/width/height,
  axis-derived composite value objects, and the oriented bounding box.
  Bound on :class:`LinearElement` (Beam, Drilling, Line).
* :class:`OrientedGeometry` — adds the :attr:`thickness` semantic alias for
  the backend's height channel. Bound on :class:`OrientedElement` (Plate).
* :class:`NodeGeometry` — adds the single :attr:`position` accessor; bulk
  queries still work but report degenerate values.
"""
from __future__ import annotations

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.geometry import (
    AxisAlignedBoundingBox,
    AxisFrame,
    AxisPoints,
    Brep,
    Frame3D,
    OrientedBoundingBox,
    Point3D,
    Vector3D,
)
from pycadwork.geometry._facets import (
    aabb_from_points,
    brep_from_facet_list,
    point3d_from_tuple,
)


class Geometry:
    """Whole-element queries: volume, weight, COG, AABB, BRep."""

    __slots__ = ("_id",)

    def __init__(self, element_id: ElementId) -> None:
        self._id = element_id

    @property
    def volume(self) -> float:
        return cadwork.geometry.get_volume(self._id)

    @property
    def weight(self) -> float:
        return cadwork.geometry.get_weight(self._id)

    @property
    def center_of_gravity(self) -> Point3D:
        return point3d_from_tuple(cadwork.geometry.get_center_of_gravity(self._id))

    @property
    def aabb(self) -> AxisAlignedBoundingBox:
        return aabb_from_points(cadwork.geometry.get_element_vertices(self._id))

    @property
    def brep(self) -> Brep:
        return brep_from_facet_list(cadwork.geometry.get_element_facets(self._id))


class LinearGeometry(Geometry):
    """Axis-anchored geometry: points, frame, length, composites, OBB."""

    __slots__ = ()

    # ---- raw points ----

    @property
    def start_point(self) -> Point3D:
        return point3d_from_tuple(cadwork.geometry.get_p1(self._id))

    @property
    def end_point(self) -> Point3D:
        return point3d_from_tuple(cadwork.geometry.get_p2(self._id))

    @property
    def third_point(self) -> Point3D:
        return point3d_from_tuple(cadwork.geometry.get_p3(self._id))

    # ---- frame ----

    @property
    def frame(self) -> Frame3D:
        g = cadwork.geometry
        origin = point3d_from_tuple(g.get_p1(self._id))
        xl = g.get_xl(self._id)
        yl = g.get_yl(self._id)
        zl = g.get_zl(self._id)
        return Frame3D(
            origin,
            Vector3D(xl[0], xl[1], xl[2]),
            Vector3D(yl[0], yl[1], yl[2]),
            Vector3D(zl[0], zl[1], zl[2]),
        )

    # ---- scalars ----

    @property
    def length(self) -> float:
        return cadwork.geometry.get_length(self._id)

    @property
    def width(self) -> float:
        return cadwork.geometry.get_width(self._id)

    @property
    def height(self) -> float:
        return cadwork.geometry.get_height(self._id)

    # ---- composite value objects ----

    @property
    def axis_points(self) -> AxisPoints:
        """The three points that define this element's axis frame."""
        return AxisPoints(self.start_point, self.end_point, self.third_point)

    @property
    def axis_frame(self) -> AxisFrame:
        """The vector form of the axis: origin + x/z + length."""
        f = self.frame
        return AxisFrame(f.origin, f.axis_x, f.axis_z, self.length)

    # ---- oriented bounding box ----

    @property
    def obb(self) -> OrientedBoundingBox:
        """Tight OBB aligned to this element's local frame."""
        verts = cadwork.geometry.get_element_vertices(self._id)
        points = [point3d_from_tuple(t) for t in verts]
        return OrientedBoundingBox(points, self.frame)


class OrientedGeometry(LinearGeometry):
    """Adds the ``thickness`` alias for panel-like elements."""

    __slots__ = ()

    @property
    def thickness(self) -> float:
        """Panel thickness — semantic alias for the backend's ``height`` channel."""
        return cadwork.geometry.get_height(self._id)


class NodeGeometry(Geometry):
    """Geometry for a positioned point: a single :attr:`position` accessor."""

    __slots__ = ()

    @property
    def position(self) -> Point3D:
        return point3d_from_tuple(cadwork.geometry.get_p1(self._id))
