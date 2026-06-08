"""StoreyAssigner: classify model elements into storeys from their geometry.

Reads a building's storeys from the BMT seam, builds a pure
:class:`StoreyStack`, and for each element compares its AABB vertical extent
against the storey planes to pick a storey. Elements that straddle a plane are
assigned to the majority storey and **marked** in an indexed user_attribute so a
human can review them. Cover aggregates (Wall / Slab / Roof) are treated as a
unit: the parent's storey is forced onto all its children.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pycadwork.building.names import BuildingName, StoreyName
from pycadwork.building.storey import Storey, StoreyClassification, StoreyStack
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element import Element
from pycadwork.element.cover import Aggregate
from pycadwork.utility import suppressed_display

# Indexed user_attribute slot that carries the straddle marker by default.
_DEFAULT_MARK_ATTRIBUTE_INDEX = 1


@dataclass(frozen=True, slots=True)
class StoreyAssignment:
    """An inspectable record of one element's storey assignment."""

    element: Element
    storey: Storey
    spans: bool


class StoreyAssigner:
    """Assign elements of one building to storeys by vertical geometry."""

    def __init__(
        self,
        building: BuildingName,
        *,
        mark_attribute_index: int = _DEFAULT_MARK_ATTRIBUTE_INDEX,
        mark_value: str = "spans-storeys",
    ) -> None:
        self._building = building
        self._mark_index = mark_attribute_index
        self._mark_value = mark_value

    @suppressed_display
    def assign(self, elements: Iterable[Element]) -> list[StoreyAssignment]:
        """Classify ``elements`` into this building's storeys and write the result.

        Aggregates are classified by their parent's extent and force that storey
        onto every child; loose elements are classified individually. Straddling
        elements (and straddling aggregate parents) are marked in the configured
        user_attribute. Returns one :class:`StoreyAssignment` per processed
        element as a report.
        """
        storey_stack = self._build_stack()
        building = self._building.value

        aggregates: list[Aggregate] = []
        loose: list[Element] = []
        for element in elements:
            if isinstance(element, Aggregate):
                aggregates.append(element)
            else:
                loose.append(element)

        assignments: list[StoreyAssignment] = []
        seen: set[int] = set()

        # Aggregates first so their children are claimed before the loose pass.
        for aggregate in aggregates:
            if aggregate.id in seen:
                continue
            classification = self._classify(storey_stack, aggregate)
            ids = [aggregate.id] + [child.id for child in aggregate.children]
            cadwork.bim.set_building_and_storey(
                ids, building, classification.storey.name.value
            )
            seen.update(ids)
            self._maybe_mark(aggregate.id, classification)
            assignments.append(
                StoreyAssignment(aggregate, classification.storey, classification.spans)
            )

        # Loose elements: classify individually, batch the storey writes.
        by_storey: dict[str, list[ElementId]] = {}
        for element in loose:
            if element.id in seen:
                continue
            classification = self._classify(storey_stack, element)
            seen.add(element.id)
            by_storey.setdefault(classification.storey.name.value, []).append(
                element.id
            )
            self._maybe_mark(element.id, classification)
            assignments.append(
                StoreyAssignment(element, classification.storey, classification.spans)
            )

        for storey_name, eids in by_storey.items():
            cadwork.bim.set_building_and_storey(eids, building, storey_name)

        return assignments

    # ---- internals ----

    def _build_stack(self) -> StoreyStack:
        building = self._building.value
        names = cadwork.bim.get_all_storeys(building)
        if not names:
            raise ValueError(f"building {building!r} has no storeys")
        storeys = [
            Storey(StoreyName(name), cadwork.bim.get_storey_height(building, name))
            for name in names
        ]
        return StoreyStack(storeys)

    @staticmethod
    def _classify(stack: StoreyStack, element: Element) -> StoreyClassification:
        box = element.geometry.aabb
        return stack.classify(box.min_point.z, box.max_point.z)

    def _maybe_mark(self, eid: ElementId, classification: StoreyClassification) -> None:
        if classification.spans:
            cadwork.attributes.set_user_attribute(
                [eid], self._mark_index, self._mark_value
            )
