"""OperationsAdapter: boolean solids, plane/miter cuts, process management.

Methods mirror cwapi3d 1:1 and keep its raw ``hard``/``soft`` vocabulary and
argument order (cutters first); the intention-revealing names live in
:mod:`pycadwork.ops`.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter._helpers import plane_to_cadwork_args
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.geometry.plane3d import Plane3D


class OperationsAdapter:
    """Boolean / cutting / process operations from ``element_controller``."""

    # ---- boolean solids ----

    def solder_elements(self, eids: list[ElementId]) -> list[ElementId]:
        import element_controller

        return [ElementId(e) for e in element_controller.solder_elements(list(eids))]

    def subtract_elements(
        self, hard_eids: list[ElementId], soft_eids: list[ElementId]
    ) -> list[ElementId]:
        import element_controller

        return [
            ElementId(e)
            for e in element_controller.subtract_elements(
                list(hard_eids), list(soft_eids)
            )
        ]

    def subtract_elements_with_undo(
        self,
        hard_eids: list[ElementId],
        soft_eids: list[ElementId],
        with_undo: bool,
    ) -> list[ElementId]:
        import element_controller

        return [
            ElementId(e)
            for e in element_controller.subtract_elements_with_undo(
                list(hard_eids), list(soft_eids), with_undo
            )
        ]

    def split_elements(self, eids: list[ElementId]) -> None:
        import element_controller

        element_controller.split_elements(list(eids))

    # ---- plane / miter / overmeasure cuts ----

    def cut_element_with_plane(self, eid: ElementId, plane: Plane3D) -> bool:
        import cadwork
        import element_controller

        normal, distance = plane_to_cadwork_args(cadwork, plane)
        return element_controller.cut_element_with_plane(eid, normal, distance)

    def slice_element_with_plane_get_new(
        self, eid: ElementId, plane: Plane3D
    ) -> list[ElementId]:
        import cadwork
        import element_controller

        normal, distance = plane_to_cadwork_args(cadwork, plane)
        return [
            ElementId(e)
            for e in element_controller.slice_elements_with_plane_and_get_new_elements(
                eid, normal, distance
            )
        ]

    def cut_elements_with_miter(
        self, first_eid: ElementId, second_eid: ElementId
    ) -> bool:
        import element_controller

        return element_controller.cut_elements_with_miter(first_eid, second_eid)

    def cut_elements_with_overmeasure(
        self, hard_eids: list[ElementId], soft_eids: list[ElementId]
    ) -> None:
        import element_controller

        element_controller.cut_elements_with_overmeasure(
            list(hard_eids), list(soft_eids)
        )

    def cut_cross_lap(
        self,
        eids: list[ElementId],
        depth: float,
        clearance_base: float,
        clearance_side: float,
        drilling_count: int,
        drilling_diameter: float,
        drilling_tolerance: float,
    ) -> None:
        import element_controller

        element_controller.cut_cross_lap(
            list(eids),
            depth,
            clearance_base,
            clearance_side,
            drilling_count,
            drilling_diameter,
            drilling_tolerance,
        )

    def cut_element_with_processing_group(
        self, soft_eid: ElementId, processing_eid: ElementId
    ) -> None:
        import element_controller

        element_controller.cut_element_with_processing_group(soft_eid, processing_eid)

    # ---- process management ----

    def delete_processes_keep_cutting_bodies(
        self, eids: list[ElementId], keep_cutting_elements_only: bool
    ) -> list[ElementId]:
        import element_controller

        return [
            ElementId(e)
            for e in element_controller.delete_processes_keep_cutting_bodies(
                list(eids), keep_cutting_elements_only
            )
        ]

    def delete_all_element_processes(self, eids: list[ElementId]) -> None:
        import element_controller

        element_controller.delete_all_element_processes(list(eids))

    def delete_all_element_end_types(self, eids: list[ElementId]) -> None:
        import element_controller

        element_controller.delete_all_element_end_types(list(eids))
