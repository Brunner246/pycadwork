"""Facade composing the responsibility-scoped sub-adapters.

The OOP layer talks to the singleton ``cadwork`` instance exported from the
package, e.g. ``cadwork.attributes.get_name(eid)``. Each sub-adapter owns one
slice of the cwapi3d surface; adding a new call means adding it to the right
sub-adapter (and its fake counterpart in ``tests/_fakes``).
"""
from __future__ import annotations

from pycadwork.cadwork_adapter._attributes import AttributesAdapter
from pycadwork.cadwork_adapter._display import DisplayAdapter
from pycadwork.cadwork_adapter._elements import ElementsAdapter
from pycadwork.cadwork_adapter._geometry import GeometryAdapter
from pycadwork.cadwork_adapter._grouping import GroupingAdapter


class CadworkAdapter:
    """Facade over cwapi3d. Sub-adapters are grouped by responsibility."""

    __slots__ = ("elements", "attributes", "geometry", "grouping", "display")

    def __init__(self) -> None:
        self.elements: ElementsAdapter = ElementsAdapter()
        self.attributes: AttributesAdapter = AttributesAdapter()
        self.geometry: GeometryAdapter = GeometryAdapter()
        self.grouping: GroupingAdapter = GroupingAdapter()
        self.display: DisplayAdapter = DisplayAdapter()
