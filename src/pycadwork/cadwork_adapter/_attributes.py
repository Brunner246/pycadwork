"""AttributesAdapter: read/write of element attributes, including cover-kind flags.

Adding a new attribute means three steps:
  1. Add the get/set pair here.
  2. Mirror it on ``FakeAttributesAdapter`` in ``tests/_fakes/cadwork_adapter.py``.
  3. Expose it as a property/setter on :class:`pycadwork.element.components.Attributes`.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import CoverKind, ElementId


class AttributesAdapter:
    """All per-element attribute access — names, grouping, numbers, cover flags."""

    # ---- name / grouping / comment ----

    def get_name(self, eid: ElementId) -> str:
        import attribute_controller

        return attribute_controller.get_name(eid)

    def set_name(self, eids: list[ElementId], name: str) -> None:
        import attribute_controller

        attribute_controller.set_name(list(eids), name)

    def get_group(self, eid: ElementId) -> str:
        import attribute_controller

        return attribute_controller.get_group(eid)

    def set_group(self, eids: list[ElementId], group: str) -> None:
        import attribute_controller

        attribute_controller.set_group(list(eids), group)

    def get_subgroup(self, eid: ElementId) -> str:
        import attribute_controller

        return attribute_controller.get_subgroup(eid)

    def set_subgroup(self, eids: list[ElementId], subgroup: str) -> None:
        import attribute_controller

        attribute_controller.set_subgroup(list(eids), subgroup)

    def get_comment(self, eid: ElementId) -> str:
        import attribute_controller

        return attribute_controller.get_comment(eid)

    # ---- element-module wall situation ----
    # The wall situation (e.g. ``'AW260>AW260#1A'``) is the assembly key cadwork
    # stamps on the members an element-module detail produces. Unlike ordinary
    # cover membership (group/subgroup), detail members are linked by sharing
    # this string. Read-only in cwapi3d — it is calculation output, not authored.

    def get_wall_situation(self, eid: ElementId) -> str:
        import attribute_controller

        return str(attribute_controller.get_wall_situation(eid))

    def set_comment(self, eids: list[ElementId], comment: str) -> None:
        import attribute_controller

        attribute_controller.set_comment(list(eids), comment)

    # ---- material / sku / numbers ----

    def get_material_name(self, eid: ElementId) -> str:
        import attribute_controller

        if hasattr(attribute_controller, "get_element_material_name"):
            return attribute_controller.get_element_material_name(eid)
        return "unknown"

    def set_material_name(self, eids: list[ElementId], name: str) -> None:
        import attribute_controller
        import material_controller

        mid = material_controller.get_material_id(name)
        # cwapi3d's set_element_material takes a *sequence* of ids + one material
        # id; passing a scalar eid (the old per-element loop) raises a TypeError
        # in live cadwork. Apply to the whole list in one call, like the other
        # setters here.
        attribute_controller.set_element_material(list(eids), mid)

    def get_sku(self, eid: ElementId) -> str:
        import attribute_controller

        return attribute_controller.get_sku(eid)

    def set_sku(self, eids: list[ElementId], sku: str) -> None:
        import attribute_controller

        attribute_controller.set_sku(list(eids), sku)

    def get_production_number(self, eid: ElementId) -> int:
        import attribute_controller

        return int(attribute_controller.get_production_number(eid))

    def set_production_number(self, eids: list[ElementId], n: int) -> None:
        import attribute_controller

        attribute_controller.set_production_number(list(eids), n)

    def get_part_number(self, eid: ElementId) -> str:
        import attribute_controller

        return str(attribute_controller.get_part_number(eid))

    def set_part_number(self, eids: list[ElementId], n: str) -> None:
        import attribute_controller

        attribute_controller.set_part_number(list(eids), n)

    # ---- cadwork-issued identifiers ----

    def get_cadwork_guid(self, eid: ElementId) -> str:
        import element_controller

        return str(element_controller.get_element_cadwork_guid(eid))

    # ---- free-form metadata ----

    def get_additional_data(self, eid: ElementId) -> str:
        import attribute_controller

        return str(attribute_controller.get_additional_data(eid))

    def set_additional_data(self, eids: list[ElementId], data: str) -> None:
        import attribute_controller

        attribute_controller.set_additional_data(list(eids), data)

    def get_assembly_number(self, eid: ElementId) -> str:
        import attribute_controller

        return str(attribute_controller.get_assembly_number(eid))

    def set_assembly_number(self, eids: list[ElementId], n: str) -> None:
        import attribute_controller

        attribute_controller.set_assembly_number(list(eids), n)

    # ---- indexed user attributes ----

    def get_user_attribute(self, eid: ElementId, index: int) -> str:
        import attribute_controller

        return str(attribute_controller.get_user_attribute(eid, index))

    def set_user_attribute(self, eids: list[ElementId], index: int, value: str) -> None:
        import attribute_controller

        attribute_controller.set_user_attribute(list(eids), index, value)

    # ---- cover-object flags ----

    def set_cover_kind(self, eids: list[ElementId], kind: CoverKind) -> None:
        import attribute_controller

        setters = {
            CoverKind.FRAMED_WALL: attribute_controller.set_framed_wall,
            CoverKind.SOLID_WALL: attribute_controller.set_solid_wall,
            CoverKind.LOG_WALL: attribute_controller.set_log_wall,
            CoverKind.FRAMED_FLOOR: attribute_controller.set_framed_floor,
            CoverKind.SOLID_FLOOR: attribute_controller.set_solid_floor,
            CoverKind.FRAMED_ROOF: attribute_controller.set_framed_roof,
            CoverKind.SOLID_ROOF: attribute_controller.set_solid_roof,
        }
        setters[kind](list(eids))

    def set_opening(self, eids: list[ElementId]) -> None:
        import attribute_controller

        attribute_controller.set_opening(list(eids))
