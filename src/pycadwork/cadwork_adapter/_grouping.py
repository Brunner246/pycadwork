"""GroupingAdapter: grouping mode and group/subgroup filter queries."""
from __future__ import annotations

from pycadwork.cadwork_adapter._helpers import (
    grouping_mode_from_cadwork,
    grouping_mode_to_cadwork,
)
from pycadwork.cadwork_adapter.types import ElementId, GroupingMode


class GroupingAdapter:
    """Active grouping mode + element filtering by group/subgroup value."""

    def get_element_grouping_type(self) -> GroupingMode:
        import attribute_controller
        return grouping_mode_from_cadwork(attribute_controller.get_element_grouping_type())

    def set_element_grouping_type(self, mode: GroupingMode) -> None:
        import attribute_controller
        import cadwork
        attribute_controller.set_element_grouping_type(
            grouping_mode_to_cadwork(cadwork, mode)
        )

    def filter_elements_by_group(self, group: str) -> list[ElementId]:
        import cadwork
        import element_controller
        f = cadwork.element_filter()
        f.set_group(group)
        return element_controller.filter_elements(
            element_controller.get_all_identifiable_element_ids(), f
        )

    def filter_elements_by_subgroup(self, subgroup: str) -> list[ElementId]:
        import cadwork
        import element_controller
        f = cadwork.element_filter()
        f.set_subgroup(subgroup)
        return element_controller.filter_elements(
            element_controller.get_all_identifiable_element_ids(), f
        )
