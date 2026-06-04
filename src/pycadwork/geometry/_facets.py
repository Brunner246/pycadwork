"""Conversion helpers from cadwork facet/vertex data into the pycadwork.geometry model.

This module is a boundary between live cadwork data structures and the
value-typed geometry library. It does not import ``cadwork`` directly --
instead it codes against the ``VertexListLike`` / ``FacetListLike`` protocols
declared in :mod:`pycadwork.cadwork_adapter.types`. That way the geometry
package stays runnable without cwapi3d installed (the protocols are
duck-typed) and the seam stays clean.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycadwork.geometry.aabb import AxisAlignedBoundingBox
from pycadwork.geometry.brep import Brep
from pycadwork.geometry.face import Face
from pycadwork.geometry.loop import Loop
from pycadwork.geometry.plane3d import Plane3D
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pycadwork.cadwork_adapter.types import (
        FacetListLike,
        PointTuple,
        VertexListLike,
    )


def point3d_from_tuple(t: "PointTuple") -> Point3D:
    """Lift a stable point tuple into a :class:`Point3D`."""
    return Point3D(t[0], t[1], t[2])


def _points_from_vertex_list(verts: "VertexListLike") -> list[Point3D]:
    return [Point3D(p.x, p.y, p.z) for p in (verts.at(i) for i in range(verts.count()))]


def _loop_from_vertex_list(verts: "VertexListLike") -> Loop:
    return Loop(_points_from_vertex_list(verts))


def aabb_from_points(points: "Iterable[PointTuple]") -> AxisAlignedBoundingBox:
    """Build an :class:`AxisAlignedBoundingBox` from a sequence of point tuples.

    The typical caller passes the 8 vertices of an element's oriented
    bounding box, as returned by ``cadwork.geometry.get_element_vertices``
    (a plain list of stable point tuples -- not a cadwork ``vertex_list``).
    The returned AABB encloses those vertices on the world axes and is
    suitable for insertion into a
    :class:`~pycadwork.geometry.spatial_index.SpatialIndex3D`.

    Raises:
        ValueError: if ``points`` is empty.
    """
    return AxisAlignedBoundingBox(point3d_from_tuple(t) for t in points)


def brep_from_facet_list(facets: "FacetListLike") -> Brep:
    """Build a :class:`Brep` from a cadwork-shaped facet list.

    Each facet becomes a :class:`Face` with:
      - an outer :class:`Loop` from ``facets.get_external_polygon(i)``
      - zero or more inner :class:`Loop` from ``facets.get_internal_polygons(i)``
      - a support :class:`Plane3D` built from the facet normal and the first
        outer-loop vertex (a real point on the plane, avoiding numerical
        issues from reconstructing via ``get_distance_to_origin``).

    The caller retains ownership of ``facets``.
    """
    brep = Brep()
    for i in range(facets.count()):
        outer = _loop_from_vertex_list(facets.get_external_polygon(i))

        holes = facets.get_internal_polygons(i)
        inner = [_loop_from_vertex_list(holes.at(h)) for h in range(holes.count())]

        n = facets.get_normal_vector(i)
        normal = Vector3D(n.x, n.y, n.z)

        point_on_plane = (
            outer.vertex_at(0) if not outer.is_empty() else Point3D.origin()
        )
        plane = Plane3D.from_point_and_normal(point_on_plane, normal)

        brep.add_face(Face(outer, plane, inner))
    return brep
