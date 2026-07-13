"""pycadwork.gridshell — build gridshells from triangulated surfaces.

Turn a triangulated ``Surface`` (or a set of triangle surfaces) into either a
beam lattice (``members``) or a closed panel shell (``panels``)::

    from pycadwork.gridshell import GridShellBuilder
    from pycadwork.geometry import RectSection

    result = GridShellBuilder(surface).members(RectSection(60, 200)).build()
    beams = result.members

:class:`TriangulatedSurfaceBuilder` generates the input surfaces from a
nurbs-style control/sample grid.
"""

from __future__ import annotations

from pycadwork.gridshell.builder import GridShellBuilder
from pycadwork.gridshell.joints import (
    HubConnectorJoint,
    JointStrategy,
    LapJoint,
    MiterJoint,
    RadialMiterJoint,
)
from pycadwork.gridshell.specs import (
    GridEdge,
    GridNode,
    GridShellResult,
    HubJoint,
    MiterPolicy,
    TrimPolicy,
)
from pycadwork.gridshell.surface_builder import TriangulatedSurfaceBuilder
from pycadwork.gridshell.topology import GridTopology

__all__ = [
    "GridEdge",
    "GridNode",
    "GridShellBuilder",
    "GridShellResult",
    "GridTopology",
    "HubConnectorJoint",
    "HubJoint",
    "JointStrategy",
    "LapJoint",
    "MiterJoint",
    "MiterPolicy",
    "RadialMiterJoint",
    "TrimPolicy",
    "TriangulatedSurfaceBuilder",
]
