"""The attribute surface for every cadwork element.

Adding a new attribute is a three-step recipe:
  1. Add the get/set pair on ``AttributesAdapter`` in ``cadwork_adapter/_attributes.py``.
  2. Mirror it on ``FakeAttributesAdapter`` in ``tests/_fakes/cadwork_adapter.py``.
  3. Add the property / setter here.
"""
from __future__ import annotations

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId


class Attributes:
    """Read/write view of an element's cadwork attributes."""

    __slots__ = ("_id",)

    def __init__(self, element_id: ElementId) -> None:
        self._id = element_id

    # ---- name / grouping / comment ----

    @property
    def name(self) -> str:
        return cadwork.attributes.get_name(self._id)

    def set_name(self, name: str) -> None:
        cadwork.attributes.set_name([self._id], name)

    @property
    def group(self) -> str:
        return cadwork.attributes.get_group(self._id)

    def set_group(self, group: str) -> None:
        cadwork.attributes.set_group([self._id], group)

    @property
    def subgroup(self) -> str:
        return cadwork.attributes.get_subgroup(self._id)

    def set_subgroup(self, subgroup: str) -> None:
        cadwork.attributes.set_subgroup([self._id], subgroup)

    @property
    def comment(self) -> str:
        return cadwork.attributes.get_comment(self._id)

    def set_comment(self, comment: str) -> None:
        cadwork.attributes.set_comment([self._id], comment)

    # ---- material / sku / numbers ----

    @property
    def material_name(self) -> str:
        return cadwork.attributes.get_material_name(self._id)

    def set_material(self, name: str) -> None:
        cadwork.attributes.set_material_name([self._id], name)

    @property
    def sku(self) -> str:
        return cadwork.attributes.get_sku(self._id)

    def set_sku(self, sku: str) -> None:
        cadwork.attributes.set_sku([self._id], sku)

    @property
    def production_number(self) -> int:
        return cadwork.attributes.get_production_number(self._id)

    def set_production_number(self, n: int) -> None:
        cadwork.attributes.set_production_number([self._id], n)

    @property
    def part_number(self) -> str:
        return cadwork.attributes.get_part_number(self._id)

    def set_part_number(self, n: str) -> None:
        cadwork.attributes.set_part_number([self._id], n)

    # ---- cadwork-issued identifiers ----

    @property
    def cadwork_guid(self) -> str:
        """The cadwork-issued GUID for this element. Read-only in cwapi3d."""
        return cadwork.attributes.get_cadwork_guid(self._id)

    # ---- free-form metadata ----

    @property
    def additional_data(self) -> str:
        return cadwork.attributes.get_additional_data(self._id)

    def set_additional_data(self, data: str) -> None:
        cadwork.attributes.set_additional_data([self._id], data)

    @property
    def assembly_number(self) -> str:
        return cadwork.attributes.get_assembly_number(self._id)

    def set_assembly_number(self, n: str) -> None:
        cadwork.attributes.set_assembly_number([self._id], n)

    # ---- indexed user attributes ----

    def user_attribute(self, index: int) -> str:
        """Read user attribute ``index`` (cwapi3d's ``get_user_attribute``)."""
        return cadwork.attributes.get_user_attribute(self._id, index)

    def set_user_attribute(self, index: int, value: str) -> None:
        cadwork.attributes.set_user_attribute([self._id], index, value)
