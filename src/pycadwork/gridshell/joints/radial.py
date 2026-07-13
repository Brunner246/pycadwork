"""RadialMiterJoint: trim a whole rosette of ribs to shared bisector planes.

A pairwise ``cut_with_miter`` can only join two beams, so it cannot resolve the
five- or six-rib hubs of a triangulated shell. This strategy instead gives every
rib a true multi-way miter: at each node it cuts each rib on the angular-bisector
planes between it and its two neighbours (see
:class:`~pycadwork.gridshell.joints.base.NodeFan`), so adjacent ribs butt on a
shared planar face and the whole fan closes with **no void and no connector**.

The ribs are left meeting at the node (no setback) so the cutting planes land;
each cut is an ``ops.cut_with_plane``. Genuine two-rib corners fall back to an
ordinary miter.
"""

from __future__ import annotations

from pycadwork import ops
from pycadwork.gridshell.joints.base import JointContext, JointStrategy, NodeFan
from pycadwork.gridshell.joints.miter import _miter_pair


class RadialMiterJoint(JointStrategy):
    """Radial (multi-rib) miter: cut each rib on its neighbours' bisector planes.

    Nodes of valence ``>= min_valence`` get the radial treatment; genuine
    two-rib corners fall back to a pairwise miter.
    """

    __slots__ = ("_min_valence",)

    def __init__(self, min_valence: int = 3) -> None:
        if min_valence < 3:
            raise ValueError(
                "RadialMiterJoint.min_valence must be >= 3 (valence-2 nodes mitre)"
            )
        self._min_valence = min_valence

    @property
    def min_valence(self) -> int:
        return self._min_valence

    def resolve(self, context: JointContext) -> None:
        edges = context.topology.edges()
        for node in context.topology.nodes():
            incident = list(node.edge_indices)
            if len(incident) < 2:
                continue
            if node.valence < self._min_valence:
                if len(incident) == 2:
                    _miter_pair(
                        context.beams, incident[0], incident[1], context.warnings
                    )
                continue
            self._cut_rosette(NodeFan(node, edges), context)

    def _cut_rosette(self, fan: NodeFan, context: JointContext) -> None:
        for edge_index, planes in fan.bisector_cuts().items():
            beam = context.beams[edge_index]
            for plane in planes:
                if not ops.cut_with_plane(beam, plane):
                    context.warnings.append(
                        f"radial miter: cut missed on edge {edge_index}"
                    )
