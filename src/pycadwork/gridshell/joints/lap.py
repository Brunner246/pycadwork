"""LapJoint: housed cross-lap (+ optional bolts) where two ribs cross a node.

For grids whose ribs run through a node as continuous lines, the pair of ribs on
the straightest through-line can be interlocked with a **housed cross-lap** — a
half-depth housing notched into each so they seat flush — rather than mitered or
set back. This delegates to cadwork's native ``cut_cross_lap`` (via
:func:`pycadwork.ops.cut_cross_lap`), which computes the interlocking housings
and drills the fasteners in one operation.

Cross-lap suits a genuine crossing (a straight through-pair); it is applied to
the straightest incident pair at each node of valence ``>= min_valence``. On a
finely divided shell those are real through-crossings; the cut geometry itself is
best confirmed live (see this package's verification notes).
"""

from __future__ import annotations

from pycadwork import ops
from pycadwork.gridshell.joints.base import JointContext, JointStrategy
from pycadwork.gridshell.joints.miter import _straightest_pair


class LapJoint(JointStrategy):
    """Housed cross-lap the straightest through-pair at each multi-rib node.

    ``depth`` is the housing depth; when ``None`` it defaults to half the section
    height (a symmetric cross-lap). ``bolt_count`` / ``bolt_diameter`` /
    ``bolt_tolerance`` drill fasteners through each joint; ``clearance_base`` /
    ``clearance_side`` are fit tolerances passed straight to cadwork.
    """

    __slots__ = (
        "_min_valence",
        "_depth",
        "_clearance_base",
        "_clearance_side",
        "_bolt_count",
        "_bolt_diameter",
        "_bolt_tolerance",
    )

    def __init__(
        self,
        *,
        min_valence: int = 3,
        depth: float | None = None,
        clearance_base: float = 0.0,
        clearance_side: float = 0.0,
        bolt_count: int = 0,
        bolt_diameter: float = 0.0,
        bolt_tolerance: float = 0.0,
    ) -> None:
        if min_valence < 2:
            raise ValueError("LapJoint.min_valence must be >= 2")
        if depth is not None and depth <= 0.0:
            raise ValueError("LapJoint.depth must be positive when given")
        if bolt_count < 0:
            raise ValueError("LapJoint.bolt_count must be non-negative")
        self._min_valence = min_valence
        self._depth = depth
        self._clearance_base = clearance_base
        self._clearance_side = clearance_side
        self._bolt_count = bolt_count
        self._bolt_diameter = bolt_diameter
        self._bolt_tolerance = bolt_tolerance

    @property
    def min_valence(self) -> int:
        return self._min_valence

    def resolve(self, context: JointContext) -> None:
        edges = context.topology.edges()
        depth = self._depth if self._depth is not None else context.section.height / 2.0
        for node in context.topology.nodes():
            if node.valence < self._min_valence:
                continue
            pair = _straightest_pair(node, edges, list(node.edge_indices))
            if pair is None:
                continue
            ops.cut_cross_lap(
                [context.beams[pair[0]], context.beams[pair[1]]],
                depth=depth,
                clearance_base=self._clearance_base,
                clearance_side=self._clearance_side,
                drilling_count=self._bolt_count,
                drilling_diameter=self._bolt_diameter,
                drilling_tolerance=self._bolt_tolerance,
            )
