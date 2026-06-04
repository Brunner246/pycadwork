"""pycadwork: OOP layer over cwapi3d (cadwork 3D Python API).

The top-level namespace re-exports the public surface so callers can write
``from pycadwork import Beam, Wall, CoverBuilder, Point3D`` without knowing
the submodule layout. All cwapi3d interaction is funnelled through one
internal seam (``pycadwork.cadwork_adapter``); the rest of the package is
agnostic to any specific cwapi3d version.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode
from pycadwork.connectivity import (
    ConnectionGraph,
    build_connection_graph,
    find_connected,
)
from pycadwork.cover import (
    Aggregate,
    CoverBuilder,
    Group,
    Roof,
    Slab,
    Wall,
    discover_covers,
)
from pycadwork.document import Document, ProjectInfo
from pycadwork.element import (
    REGISTRY,
    AuxiliaryElement,
    Beam,
    ConnectorAxis,
    CrossSection,
    Drilling,
    Element,
    ElementRegistry,
    Line,
    LinearElement,
    Node,
    Opening,
    OrientedElement,
    Plate,
    Surface,
    from_id,
    register_element,
)
from pycadwork.geometry import (
    AxisAlignedBoundingBox,
    AxisFrame,
    AxisPoints,
    Brep,
    Face,
    Frame3D,
    Loop,
    OrientedBoundingBox,
    PanelSection,
    Plane3D,
    Point3D,
    RTreeIndex3D,
    RectSection,
    Segment,
    SpatialIndex3D,
    SpatialQuery3D,
    Vector3D,
)
from pycadwork.utility import (
    DisplayRefreshScope,
    auto_eq,
    auto_hash,
    auto_recreate,
    auto_repr,
    batch_apply,
    deprecated,
    suppressed_display,
)

__all__ = [
    "REGISTRY",
    "Aggregate",
    "AuxiliaryElement",
    "AxisAlignedBoundingBox",
    "AxisFrame",
    "AxisPoints",
    "Beam",
    "Brep",
    "ConnectionGraph",
    "ConnectorAxis",
    "CoverBuilder",
    "CoverKind",
    "CrossSection",
    "DisplayRefreshScope",
    "Document",
    "Drilling",
    "Element",
    "ElementRegistry",
    "Face",
    "Frame3D",
    "Group",
    "GroupingMode",
    "Line",
    "LinearElement",
    "Loop",
    "Node",
    "Opening",
    "OrientedBoundingBox",
    "OrientedElement",
    "PanelSection",
    "Plane3D",
    "Plate",
    "Point3D",
    "ProjectInfo",
    "RTreeIndex3D",
    "RectSection",
    "Roof",
    "Segment",
    "Slab",
    "SpatialIndex3D",
    "SpatialQuery3D",
    "Surface",
    "Vector3D",
    "Wall",
    "auto_eq",
    "auto_hash",
    "auto_recreate",
    "auto_repr",
    "batch_apply",
    "build_connection_graph",
    "deprecated",
    "discover_covers",
    "find_connected",
    "from_id",
    "register_element",
    "suppressed_display",
]
