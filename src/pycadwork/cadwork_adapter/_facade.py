"""Facade composing the responsibility-scoped sub-adapters.

The OOP layer talks to the singleton ``cadwork`` instance exported from the
package, e.g. ``cadwork.attributes.get_name(eid)``. Each sub-adapter owns one
slice of the cwapi3d surface; adding a new call means adding it to the right
sub-adapter (and its fake counterpart in ``tests/_fakes``).
"""

from __future__ import annotations

from pycadwork.cadwork_adapter._attributes import AttributesAdapter
from pycadwork.cadwork_adapter._bim import BimAdapter
from pycadwork.cadwork_adapter._collision import CollisionAdapter
from pycadwork.cadwork_adapter._display import DisplayAdapter
from pycadwork.cadwork_adapter._elements import ElementsAdapter
from pycadwork.cadwork_adapter._file import FileAdapter
from pycadwork.cadwork_adapter._geometry import GeometryAdapter
from pycadwork.cadwork_adapter._grouping import GroupingAdapter
from pycadwork.cadwork_adapter._material import MaterialAdapter
from pycadwork.cadwork_adapter._module import ModuleAdapter
from pycadwork.cadwork_adapter._operations import OperationsAdapter
from pycadwork.cadwork_adapter._project import ProjectAdapter
from pycadwork.cadwork_adapter._visualization import VisualizationAdapter


class CadworkAdapter:
    """Facade over cwapi3d. Sub-adapters are grouped by responsibility."""

    __slots__ = (
        "elements",
        "attributes",
        "geometry",
        "grouping",
        "display",
        "project",
        "bim",
        "material",
        "operations",
        "module",
        "visualization",
        "collision",
        "file",
    )

    def __init__(self) -> None:
        self.elements: ElementsAdapter = ElementsAdapter()
        self.attributes: AttributesAdapter = AttributesAdapter()
        self.geometry: GeometryAdapter = GeometryAdapter()
        self.grouping: GroupingAdapter = GroupingAdapter()
        self.display: DisplayAdapter = DisplayAdapter()
        self.project: ProjectAdapter = ProjectAdapter()
        self.bim: BimAdapter = BimAdapter()
        self.material: MaterialAdapter = MaterialAdapter()
        self.operations: OperationsAdapter = OperationsAdapter()
        self.module: ModuleAdapter = ModuleAdapter()
        self.visualization: VisualizationAdapter = VisualizationAdapter()
        self.collision: CollisionAdapter = CollisionAdapter()
        self.file: FileAdapter = FileAdapter()
