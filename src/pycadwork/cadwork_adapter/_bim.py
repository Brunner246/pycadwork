"""BimAdapter: cadwork's BMT building/storey surface (``bim_controller``).

A building owns an ordered set of storeys; every element may be assigned to a
``(building, storey)`` pair, and each storey carries an absolute Z elevation of
its base plane. The OOP layer reads these to classify elements by height and
writes the resulting assignment back.

Adding a new call here means mirroring it on ``FakeBimAdapter`` in
``pycadwork/testing/cadwork_adapter.py`` and wiring the ``bim`` slot in
``tests/conftest.py``.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import ElementId

#: Canonical IFC 2x3 tokens the adapter accepts on set (v1 allow-list).
IFC_2X3_ELEMENT_TYPES: tuple[str, ...] = (
    "IfcBeam",
    "IfcColumn",
    "IfcMember",
    "IfcPlate",
    "IfcWall",
    "IfcSlab",
    "IfcRoof",
    "IfcOpeningElement",
    "IfcBuildingElementProxy",
)

_IFC_2X3_SETTERS: dict[str, str] = {
    "IfcBeam": "set_ifc_beam",
    "IfcColumn": "set_ifc_column",
    "IfcMember": "set_ifc_member",
    "IfcPlate": "set_ifc_plate",
    "IfcWall": "set_ifc_wall",
    "IfcSlab": "set_ifc_slab",
    "IfcRoof": "set_ifc_roof",
    "IfcOpeningElement": "set_ifc_opening_element",
    "IfcBuildingElementProxy": "set_ifc_building_element_proxy",
}


def _canonical_ifc_type(raw: object) -> str:
    """Stringify a cwapi3d ``ifc_2x3_element_type`` to ``"IfcBeam"`` (or ``""``)."""
    if raw is None:
        return ""
    is_none = getattr(raw, "is_none", None)
    if callable(is_none) and is_none():
        return ""
    token = str(raw).strip()
    if not token or token.lower() == "none":
        return ""
    canonical = token if token.startswith("Ifc") else f"Ifc{token}"
    if canonical not in _IFC_2X3_SETTERS:
        return ""
    return canonical


def _unknown_ifc_type(ifc_type: str) -> ValueError:
    allowed = ", ".join(IFC_2X3_ELEMENT_TYPES)
    return ValueError(f"unknown IFC type {ifc_type!r}; allowed: {allowed}")


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

    # ---- IFC 2x3 element type ----

    def get_ifc_type(self, eid: ElementId) -> str:
        import bim_controller

        return _canonical_ifc_type(bim_controller.get_ifc2x3_element_type(eid))

    def set_ifc_type(self, eids: list[ElementId], ifc_type: str) -> None:
        import bim_controller
        import cadwork

        entity = cadwork.ifc_2x3_element_type()
        if ifc_type == "":
            entity.set_none()
        else:
            setter = _IFC_2X3_SETTERS.get(ifc_type)
            if setter is None:
                raise _unknown_ifc_type(ifc_type)
            getattr(entity, setter)()
        bim_controller.set_ifc2x3_element_type(list(eids), entity)
