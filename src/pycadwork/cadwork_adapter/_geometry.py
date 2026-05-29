"""GeometryAdapter: axis points, frame axes, dimensions, vertices, facets."""
from __future__ import annotations

from pycadwork.cadwork_adapter._helpers import to_tuple
from pycadwork.cadwork_adapter.types import (
    ElementId,
    FacetListLike,
    PointTuple,
)


class GeometryAdapter:
    """All geometric queries on an element — never mutates."""

    # ---- raw axis points ----

    def get_p1(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_p1(eid))

    def get_p2(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_p2(eid))

    def get_p3(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_p3(eid))

    # ---- local frame axes ----

    def get_xl(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_xl(eid))

    def get_yl(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_yl(eid))

    def get_zl(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_zl(eid))

    # ---- scalars ----

    def get_length(self, eid: ElementId) -> float:
        import geometry_controller
        return float(geometry_controller.get_length(eid))

    def get_width(self, eid: ElementId) -> float:
        import geometry_controller
        return float(geometry_controller.get_width(eid))

    def get_height(self, eid: ElementId) -> float:
        import geometry_controller
        return float(geometry_controller.get_height(eid))

    def get_volume(self, eid: ElementId) -> float:
        import geometry_controller
        return float(geometry_controller.get_volume(eid))

    def get_weight(self, eid: ElementId) -> float:
        import geometry_controller
        return float(geometry_controller.get_weight(eid))

    def get_center_of_gravity(self, eid: ElementId) -> PointTuple:
        import geometry_controller
        return to_tuple(geometry_controller.get_center_of_gravity(eid))

    # ---- bulk geometry ----

    def get_element_vertices(self, eid: ElementId) -> list[PointTuple]:
        # cwapi3d's get_element_vertices returns a plain ``List[point_3d]``
        # (NOT a vertex_list with count()/at() -- only facet polygons are
        # vertex_list). Project each point into a stable tuple at the seam so
        # the geometry layer never sees a raw cadwork object here.
        import geometry_controller
        return [to_tuple(p) for p in geometry_controller.get_element_vertices(eid)]

    def get_element_facets(self, eid: ElementId) -> FacetListLike:
        import geometry_controller
        return geometry_controller.get_element_facets(eid)
