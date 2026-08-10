"""The single seam to cwapi3d.

Outside ``cadwork_adapter`` no module should import ``cadwork`` or any
``*_controller``. Outside callers use the module-level :data:`cadwork`
instance, e.g. ``cadwork.attributes.get_name(eid)``.

Tests swap in a fake by monkeypatching the module attribute::

    monkeypatch.setattr(pycadwork.cadwork_adapter, "cadwork", FakeCadworkAdapter())
"""

from __future__ import annotations

from pycadwork.cadwork_adapter._facade import CadworkAdapter
from pycadwork.cadwork_adapter.types import (
    CoverKind,
    DetailType,
    ElementId,
    ElementTypeSnapshot,
    FacetListLike,
    GroupingMode,
    PointTuple,
    ROOF_KINDS,
    SLAB_KINDS,
    VertexListLike,
    WALL_KINDS,
)

cadwork: CadworkAdapter = CadworkAdapter()

__all__ = [
    "CadworkAdapter",
    "CoverKind",
    "DetailType",
    "ElementId",
    "ElementTypeSnapshot",
    "FacetListLike",
    "GroupingMode",
    "PointTuple",
    "ROOF_KINDS",
    "SLAB_KINDS",
    "VertexListLike",
    "WALL_KINDS",
    "cadwork",
]
