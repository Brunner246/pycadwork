"""ElementsAdapter: element creation, deletion, type introspection, identification."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pycadwork.cadwork_adapter._helpers import to_cadwork_point
from pycadwork.cadwork_adapter.types import ElementId, ElementTypeSnapshot
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.specs import (
    AxisFrame,
    AxisPoints,
    PanelSection,
    RectSection,
    Segment,
)


def _pt(cadwork_module: Any, p: Point3D) -> Any:
    return to_cadwork_point(cadwork_module, p)


class ElementsAdapter:
    """Creation / deletion / type introspection / identifiable id enumeration."""

    # ---- creation ----

    def create_rectangular_beam_points(
        self, section: RectSection, axis: AxisPoints
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_rectangular_beam_points(
                section.width,
                section.height,
                _pt(cadwork, axis.p1),
                _pt(cadwork, axis.p2),
                _pt(cadwork, axis.p3),
            )
        )

    def create_rectangular_beam_vectors(
        self, section: RectSection, frame: AxisFrame
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_rectangular_beam_vectors(
                section.width,
                section.height,
                frame.length,
                _pt(cadwork, frame.origin),
                cadwork.point_3d(frame.x_dir.x, frame.x_dir.y, frame.x_dir.z),
                cadwork.point_3d(frame.z_dir.x, frame.z_dir.y, frame.z_dir.z),
            )
        )

    def create_circular_beam_points(
        self, diameter: float, axis: AxisPoints
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_circular_beam_points(
                diameter,
                _pt(cadwork, axis.p1),
                _pt(cadwork, axis.p2),
                _pt(cadwork, axis.p3),
            )
        )

    def create_square_beam_points(self, width: float, axis: AxisPoints) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_square_beam_points(
                width,
                _pt(cadwork, axis.p1),
                _pt(cadwork, axis.p2),
                _pt(cadwork, axis.p3),
            )
        )

    def create_rectangular_panel_points(
        self, section: PanelSection, axis: AxisPoints
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_rectangular_panel_points(
                section.width,
                section.thickness,
                _pt(cadwork, axis.p1),
                _pt(cadwork, axis.p2),
                _pt(cadwork, axis.p3),
            )
        )

    def create_rectangular_panel_vectors(
        self, section: PanelSection, frame: AxisFrame
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_rectangular_panel_vectors(
                section.width,
                section.thickness,
                frame.length,
                _pt(cadwork, frame.origin),
                cadwork.point_3d(frame.x_dir.x, frame.x_dir.y, frame.x_dir.z),
                cadwork.point_3d(frame.z_dir.x, frame.z_dir.y, frame.z_dir.z),
            )
        )

    def create_drilling_points(self, diameter: float, axis: Segment) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_drilling_points(
                diameter, _pt(cadwork, axis.p1), _pt(cadwork, axis.p2)
            )
        )

    def create_circular_mep(
        self, diameter: float, points: Sequence[Point3D]
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_circular_mep(
                diameter, [_pt(cadwork, p) for p in points]
            )
        )

    def create_rectangular_mep(
        self, width: float, depth: float, points: Sequence[Point3D]
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_rectangular_mep(
                width, depth, [_pt(cadwork, p) for p in points]
            )
        )

    def create_auto_container_from_standard(
        self, eids: list[ElementId], output_name: str, standard_element_name: str
    ) -> ElementId:
        import element_controller

        return ElementId(
            element_controller.create_auto_container_from_standard(
                list(eids), output_name, standard_element_name
            )
        )

    def create_auto_container_from_standard_with_reference(
        self,
        eids: list[ElementId],
        output_name: str,
        standard_element_name: str,
        reference_eid: ElementId,
    ) -> ElementId:
        import element_controller

        return ElementId(
            element_controller.create_auto_container_from_standard_with_reference(
                list(eids), output_name, standard_element_name, reference_eid
            )
        )

    def create_node(self, position: Point3D) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(element_controller.create_node(_pt(cadwork, position)))

    def create_line_points(self, axis: Segment) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_line_points(
                _pt(cadwork, axis.p1), _pt(cadwork, axis.p2)
            )
        )

    def create_surface_points(self, points: list[Point3D]) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.create_surface([_pt(cadwork, p) for p in points])
        )

    def create_standard_connector(self, axis: Segment, name: str) -> ElementId:
        import cadwork
        import connector_axis_controller

        return ElementId(
            connector_axis_controller.create_standard_connector(
                _pt(cadwork, axis.p1),
                _pt(cadwork, axis.p2),
                name,
            )
        )

    def extrude_surface_to_auxiliary_vector(
        self, surface_eid: ElementId, vector: Point3D
    ) -> ElementId:
        import cadwork
        import element_controller

        return ElementId(
            element_controller.extrude_surface_to_auxiliary_vector(
                surface_eid, _pt(cadwork, vector)
            )
        )

    def delete_elements(self, eids: list[ElementId]) -> None:
        import element_controller

        element_controller.delete_elements(list(eids))

    def element_exists(self, eid: ElementId) -> bool:
        import element_controller

        return element_controller.check_element_id(eid)

    # ---- type introspection ----

    def get_element_type(self, eid: ElementId) -> ElementTypeSnapshot:
        # Importing ``cadwork`` registers the ``element_type`` pybind11 binding;
        # without it, converting ``get_element_type``'s return value raises
        # "Unregistered type : element_type".
        import attribute_controller
        import cadwork  # noqa: F401 — imported for its type registrations

        t = attribute_controller.get_element_type(eid)
        is_rect = t.is_rectangular_beam()
        is_circ = t.is_circular_beam()
        is_wall = t.is_wall()
        is_floor = t.is_floor()
        is_roof = t.is_roof()
        return ElementTypeSnapshot(
            is_beam=is_rect or is_circ or t.is_steel_shape(),
            is_rectangular_beam=is_rect,
            is_circular_beam=is_circ,
            is_steel_shape=t.is_steel_shape(),
            is_panel=t.is_panel(),
            is_circular_mep=attribute_controller.is_circular_mep(eid),
            is_rectangular_mep=attribute_controller.is_rectangular_mep(eid),
            is_container=t.is_container(),
            is_drilling=t.is_drilling_axis(),
            is_node=t.is_normal_node() or t.is_connector_node(),
            is_surface=t.is_surface(),
            is_line=t.is_line(),
            is_wall=is_wall,
            is_floor=is_floor,
            is_roof=is_roof,
            is_framed_wall=is_wall and attribute_controller.is_framed_wall(eid),
            is_solid_wall=is_wall and attribute_controller.is_solid_wall(eid),
            is_log_wall=is_wall and attribute_controller.is_log_wall(eid),
            is_framed_floor=is_floor and attribute_controller.is_framed_floor(eid),
            is_solid_floor=is_floor and attribute_controller.is_solid_floor(eid),
            is_framed_roof=is_roof and attribute_controller.is_framed_roof(eid),
            is_solid_roof=is_roof and attribute_controller.is_solid_roof(eid),
            is_opening=attribute_controller.is_opening(eid),
            is_connector_axis=attribute_controller.is_connector_axis(eid),
            is_auxiliary=attribute_controller.is_auxiliary(eid),
        )

    # ---- container content ----

    def get_container_content_elements(self, eid: ElementId) -> list[ElementId]:
        import element_controller

        return [
            ElementId(e) for e in element_controller.get_container_content_elements(eid)
        ]

    def get_parent_container_id(self, eid: ElementId) -> ElementId:
        """The id of ``eid``'s parent container, or ``0`` when it has none."""
        import element_controller

        return ElementId(element_controller.get_parent_container_id(eid))

    def set_container_contents(
        self, container_eid: ElementId, eids: list[ElementId]
    ) -> None:
        import element_controller

        element_controller.set_container_contents(container_eid, list(eids))

    # ---- identifiable enumeration ----

    def get_all_identifiable_element_ids(self) -> list[ElementId]:
        import element_controller

        return [
            ElementId(e) for e in element_controller.get_all_identifiable_element_ids()
        ]

    def get_active_identifiable_element_ids(self) -> list[ElementId]:
        import element_controller

        return [
            ElementId(e)
            for e in element_controller.get_active_identifiable_element_ids()
        ]
