"""Bulk-attribute helpers — one adapter call per attribute, instead of N."""
from __future__ import annotations

from collections.abc import Iterable

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element import Element

_BATCH_SETTERS: dict[str, str] = {
    "name": "set_name",
    "group": "set_group",
    "subgroup": "set_subgroup",
    "comment": "set_comment",
    "material_name": "set_material_name",
    "sku": "set_sku",
    "production_number": "set_production_number",
    "part_number": "set_part_number",
}


def batch_apply(elements: Iterable[Element], /, **attrs) -> None:
    """Set one or more attributes on many elements with one adapter call each.

    Example::

        batch_apply(beams, group="frame", material_name="Pine")

    Unknown attribute names raise ``TypeError`` so typos surface at the call
    site rather than silently doing nothing.
    """
    ids = [e.id for e in elements]
    if not ids:
        return
    attributes_adapter = cadwork.attributes
    for key, value in attrs.items():
        method_name = _BATCH_SETTERS.get(key)
        if method_name is None:
            raise TypeError(f"batch_apply does not support attribute {key!r}")
        getattr(attributes_adapter, method_name)(ids, value)
