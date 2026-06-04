"""BimAdapter: cadwork's BMT building/storey surface (``bim_controller``).

A building owns an ordered set of storeys; every element may be assigned to a
``(building, storey)`` pair, and each storey carries an absolute Z elevation of
its base plane. The OOP layer reads these to classify elements by height and
writes the resulting assignment back.

Adding a new call here means mirroring it on ``FakeBimAdapter`` in
``tests/_fakes/cadwork_adapter.py`` and wiring the ``bim`` slot in
``tests/conftest.py``.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import ElementId


class BimAdapter:
    """Read/write the BMT building/storey structure and per-element assignment."""

    # ---- per-element assignment ----

    def get_building(self, eid: ElementId) -> str:
        import bim_controller

        return bim_controller.get_building(eid)

    def get_storey(self, eid: ElementId) -> str:
        import bim_controller

        return bim_controller.get_storey(eid)

    def set_building_and_storey(
        self, eids: list[ElementId], building: str, storey: str
    ) -> None:
        import bim_controller

        bim_controller.set_building_and_storey(list(eids), building, storey)

    # ---- registry enumeration ----

    def get_all_buildings(self) -> list[str]:
        import bim_controller

        return list(bim_controller.get_all_buildings())

    def get_all_storeys(self, building: str) -> list[str]:
        import bim_controller

        return list(bim_controller.get_all_storeys(building))

    # ---- storey elevation ----

    def get_storey_height(self, building: str, storey: str) -> float:
        import bim_controller

        return float(bim_controller.get_storey_height(building, storey))

    def set_storey_height(self, building: str, storey: str, height: float) -> None:
        import bim_controller

        bim_controller.set_storey_height(building, storey, height)
