"""The attribute surface for every cadwork element.

Reads and writes are symmetric properties: ``element.attrs.name`` reads and
``element.attrs.name = "Stud"`` writes. Both are live calls against the active
backend — there is no cached field, so the writable property is exactly as
honest about its cost as the readable one. Derived values cadwork won't let us
change (``cadwork_guid``) are read-only properties with no setter. Indexed user
attributes can't be expressed as a bare property, so they stay methods.

Adding a new attribute is a three-step recipe:
  1. Add the get/set pair on ``AttributesAdapter`` in ``cadwork_adapter/_attributes.py``.
  2. Mirror it on ``FakeAttributesAdapter`` in ``tests/_fakes/cadwork_adapter.py``.
  3. Add the property (and ``@<name>.setter``) here.

``color`` is the one exception: in cwapi3d it is a *visualization* concern, not an
attribute, so its property delegates to the ``cadwork.visualization`` seam (and the
get/set pair lives on ``VisualizationAdapter``) rather than ``cadwork.attributes``.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.value_types import CadworkGuid


class Attributes:
    """Read/write view of an element's cadwork attributes."""

    __slots__ = ("_id",)

    def __init__(self, element_id: ElementId) -> None:
        self._id = element_id

    # ---- name / grouping / comment ----

    @property
    def name(self) -> str:
        return cadwork.attributes.get_name(self._id)

    @name.setter
    def name(self, name: str) -> None:
        cadwork.attributes.set_name([self._id], name)

    @property
    def group(self) -> str:
        return cadwork.attributes.get_group(self._id)

    @group.setter
    def group(self, group: str) -> None:
        cadwork.attributes.set_group([self._id], group)

    @property
    def subgroup(self) -> str:
        return cadwork.attributes.get_subgroup(self._id)

    @subgroup.setter
    def subgroup(self, subgroup: str) -> None:
        cadwork.attributes.set_subgroup([self._id], subgroup)

    @property
    def comment(self) -> str:
        return cadwork.attributes.get_comment(self._id)

    @comment.setter
    def comment(self, comment: str) -> None:
        cadwork.attributes.set_comment([self._id], comment)

    @property
    def wall_situation(self) -> str:
        """Element-module wall situation, e.g. ``'AW260>AW260#1A'``.

        The assembly key cadwork stamps on the members a detail calculation
        produces — detail members are linked by sharing this string, not by the
        ``group``/``subgroup`` used for ordinary covers. Read-only in cwapi3d.
        """
        return cadwork.attributes.get_wall_situation(self._id)

    # ---- material / sku / numbers ----

    @property
    def material_name(self) -> str:
        return cadwork.attributes.get_material_name(self._id)

    @material_name.setter
    def material_name(self, name: str) -> None:
        cadwork.attributes.set_material_name([self._id], name)

    # ---- visual state ----
    # Color is a visualization_controller concern, not an attribute, so it
    # delegates to the cadwork.visualization seam (see module docstring).

    @property
    def color(self) -> int:
        return cadwork.visualization.get_color(self._id)

    @color.setter
    def color(self, color_id: int) -> None:
        cadwork.visualization.set_color([self._id], color_id)

    @property
    def sku(self) -> str:
        return cadwork.attributes.get_sku(self._id)

    @sku.setter
    def sku(self, sku: str) -> None:
        cadwork.attributes.set_sku([self._id], sku)

    @property
    def production_number(self) -> int:
        return cadwork.attributes.get_production_number(self._id)

    @production_number.setter
    def production_number(self, n: int) -> None:
        cadwork.attributes.set_production_number([self._id], n)

    @property
    def part_number(self) -> str:
        return cadwork.attributes.get_part_number(self._id)

    @part_number.setter
    def part_number(self, n: str) -> None:
        cadwork.attributes.set_part_number([self._id], n)

    # ---- cadwork-issued identifiers ----

    @property
    def cadwork_guid(self) -> CadworkGuid:
        """The cadwork-issued GUID for this element. Read-only in cwapi3d."""
        return CadworkGuid(cadwork.attributes.get_cadwork_guid(self._id))

    # ---- free-form metadata ----

    @property
    def additional_data(self) -> str:
        return cadwork.attributes.get_additional_data(self._id)

    @additional_data.setter
    def additional_data(self, data: str) -> None:
        cadwork.attributes.set_additional_data([self._id], data)

    @property
    def assembly_number(self) -> str:
        return cadwork.attributes.get_assembly_number(self._id)

    @assembly_number.setter
    def assembly_number(self, n: str) -> None:
        cadwork.attributes.set_assembly_number([self._id], n)

    # ---- indexed user attributes ----

    def user_attribute(self, index: int) -> str:
        """Read user attribute ``index`` (cwapi3d's ``get_user_attribute``)."""
        return cadwork.attributes.get_user_attribute(self._id, index)

    def set_user_attribute(self, index: int, value: str) -> None:
        cadwork.attributes.set_user_attribute([self._id], index, value)
