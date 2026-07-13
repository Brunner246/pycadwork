"""pycadwork.gridshell.joints — pluggable node-joint strategies.

The members strategy delegates all node joinery to a :class:`JointStrategy`, so
a caller chooses how ribs meeting at a lattice node resolve into producible
geometry:

* :class:`MiterJoint` — pairwise cadwork miters (default: two-rib corners).
* :class:`HubConnectorJoint` — set ribs back from a hub and fill the void with a
  standard connector (+ optional dowel drillings).
* :class:`RadialMiterJoint` — cut every rib on the angular-bisector planes
  between neighbours, so a whole rosette butts on shared faces with no void.
* :class:`LapJoint` — housed cross-lap cuts (+ optional bolts) at crossings.
"""

from __future__ import annotations

from pycadwork.gridshell.joints.base import (
    JointContext,
    JointStrategy,
    NodeFan,
    SetbackRequest,
)
from pycadwork.gridshell.joints.hub import HubConnectorJoint
from pycadwork.gridshell.joints.lap import LapJoint
from pycadwork.gridshell.joints.miter import MiterJoint
from pycadwork.gridshell.joints.radial import RadialMiterJoint

__all__ = [
    "HubConnectorJoint",
    "JointContext",
    "JointStrategy",
    "LapJoint",
    "MiterJoint",
    "NodeFan",
    "RadialMiterJoint",
    "SetbackRequest",
]
