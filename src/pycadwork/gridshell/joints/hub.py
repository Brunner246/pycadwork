"""HubConnectorJoint: set ribs back from a hub and fill the void with a connector.

A triangulated shell has high-valence interior nodes (five or six ribs at one
point) that cannot be reconciled as mutual miters. This strategy pulls every rib
back from each such node so it becomes a producible straight stick with a flat
end, then — unlike the bare setback it supersedes — actually *places* the
joinery in the void it opened: a :class:`~pycadwork.element.connector_axis.ConnectorAxis`
spanning the node along the shell normal, and (optionally) a dowel
:class:`~pycadwork.element.drilling.Drilling` down each rib's axis into that
connector. Genuine two-rib corners are still mitered.

The setback is realized by shortening the rib axis at creation (never a boolean
cut — a plane through the rib's own axis is degenerate); see
:class:`~pycadwork.gridshell.joints.base.JointStrategy`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycadwork.element.connector_axis import ConnectorAxis
from pycadwork.element.drilling import Drilling
from pycadwork.geometry import Point3D, Segment
from pycadwork.gridshell.joints.base import (
    JointContext,
    JointStrategy,
    SetbackRequest,
    node_normal,
)
from pycadwork.gridshell.joints.miter import apply_miter
from pycadwork.gridshell.specs import MiterPolicy

if TYPE_CHECKING:
    from pycadwork.element.beam import Beam
    from pycadwork.gridshell.specs import GridEdge, GridNode

#: A shortened rib must keep at least this length after the setback, else the
#: node gaps would swallow it whole; such edges are warned about and left full.
_MIN_STUB = 1e-6


class HubConnectorJoint(JointStrategy):
    """Set ribs back from multi-rib hubs and connect them across the void.

    ``gap`` is the setback distance from the node centre. When ``gap`` is
    ``None`` it is derived from the section (``0.75 × section height``) so a
    caller need not hand-tune it — the geometry-blind scalar was the main source
    of manual work. ``min_valence`` is the lowest node valence treated as a hub
    (valence-2 corners are left to the miter). When ``connector_name`` is given,
    a standard connector of that name is placed across each hub void; when
    ``dowel_diameter`` is given, a dowel is drilled down each rib into it.
    ``miter_policy`` mitres the remaining non-hub nodes (default: two-rib corners).
    """

    __slots__ = (
        "_gap",
        "_min_valence",
        "_connector_name",
        "_dowel_diameter",
        "_miter_policy",
    )

    def __init__(
        self,
        gap: float | None = None,
        *,
        min_valence: int = 3,
        connector_name: str | None = None,
        dowel_diameter: float | None = None,
        miter_policy: MiterPolicy = MiterPolicy.VALENCE_2_ONLY,
    ) -> None:
        if gap is not None and gap <= 0.0:
            raise ValueError("HubConnectorJoint.gap must be positive when given")
        if min_valence < 3:
            raise ValueError(
                "HubConnectorJoint.min_valence must be >= 3 (valence-2 nodes mitre)"
            )
        if dowel_diameter is not None and dowel_diameter <= 0.0:
            raise ValueError("HubConnectorJoint.dowel_diameter must be positive")
        self._gap = gap
        self._min_valence = min_valence
        self._connector_name = connector_name
        self._dowel_diameter = dowel_diameter
        self._miter_policy = miter_policy

    @property
    def min_valence(self) -> int:
        return self._min_valence

    def _resolved_gap(self, section) -> float:
        """The setback distance, section-derived when no explicit gap was set."""
        return self._gap if self._gap is not None else 0.75 * section.height

    # ---- pre-creation ----

    def setback(
        self, request: SetbackRequest, warnings: list[str]
    ) -> tuple[float, float]:
        gap = self._resolved_gap(request.section)
        pull_start = gap if request.valence_a >= self._min_valence else 0.0
        pull_end = gap if request.valence_b >= self._min_valence else 0.0
        if not pull_start and not pull_end:
            return (0.0, 0.0)
        length = request.edge.p1.distance_to(request.edge.p2)
        if length - (pull_start + pull_end) < _MIN_STUB:
            warnings.append(
                f"hub joint: edge {request.index} too short for setback "
                f"(len {float(length):.0f}); rib left full length"
            )
            return (0.0, 0.0)
        return (pull_start, pull_end)

    # ---- post-creation ----

    def resolve(self, context: JointContext) -> None:
        # Non-hub nodes still miter (hub nodes are skipped: their ribs were
        # pulled back and no longer meet, so a miter there would miss).
        apply_miter(
            context.topology.nodes(),
            context.topology.edges(),
            context.beams,
            self._miter_policy,
            skip_hub_valence=self._min_valence,
            warnings=context.warnings,
        )
        if self._connector_name is None and self._dowel_diameter is None:
            return
        edges = context.topology.edges()
        for node in context.topology.nodes():
            if node.valence < self._min_valence:
                continue
            self._connect_hub(node, edges, context)

    def _connect_hub(
        self, node: "GridNode", edges: list["GridEdge"], context: JointContext
    ) -> None:
        normal = node_normal(node, edges)
        half = context.section.height / 2.0
        if self._connector_name is not None:
            axis = Segment(
                node.position + normal * (-half),
                node.position + normal * half,
            )
            context.connectors.append(
                ConnectorAxis.create_standard(axis, self._connector_name)
            )
        if self._dowel_diameter is not None:
            for edge_index in node.edge_indices:
                beam = context.beams[edge_index]
                end = _beam_end_near(beam, node.position)
                if end is None:
                    continue
                context.drillings.append(
                    Drilling.create(self._dowel_diameter, Segment(end, node.position))
                )


def _beam_end_near(beam: "Beam", target: Point3D) -> Point3D | None:
    """The beam endpoint closer to ``target`` (the rib's node-side end)."""
    start = beam.geometry.start_point
    end = beam.geometry.end_point
    if start.distance_to(target) <= end.distance_to(target):
        return start
    return end
