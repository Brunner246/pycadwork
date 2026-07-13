"""MiterJoint: join ribs at a node with pairwise cadwork miters.

``cut_with_miter`` joins exactly two beams, so only :attr:`MiterPolicy.VALENCE_2_ONLY`
is unconditionally correct; the higher-valence policies are opt-in and lossy (see
:class:`~pycadwork.gridshell.specs.MiterPolicy`). This module holds both the
strategy and the shared miter helpers reused by :class:`HubConnectorJoint`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycadwork import ops
from pycadwork.gridshell.joints.base import JointContext, JointStrategy
from pycadwork.gridshell.specs import MiterPolicy

if TYPE_CHECKING:
    from pycadwork.element.beam import Beam
    from pycadwork.gridshell.specs import GridEdge, GridNode


class MiterJoint(JointStrategy):
    """Miter ribs meeting at a node, pairwise, per a :class:`MiterPolicy`.

    No setback — ribs are left meeting at the node, then mitered. This is the
    default joint (``VALENCE_2_ONLY``): genuine two-rib corners/seams get a
    clean miter and higher-valence nodes are left butted.
    """

    __slots__ = ("_policy",)

    def __init__(self, policy: MiterPolicy = MiterPolicy.VALENCE_2_ONLY) -> None:
        self._policy = policy

    @property
    def policy(self) -> MiterPolicy:
        return self._policy

    def resolve(self, context: JointContext) -> None:
        apply_miter(
            context.topology.nodes(),
            context.topology.edges(),
            context.beams,
            self._policy,
            skip_hub_valence=None,
            warnings=context.warnings,
        )


def apply_miter(
    nodes: list["GridNode"],
    edges: list["GridEdge"],
    beams: list["Beam"],
    policy: MiterPolicy,
    *,
    skip_hub_valence: int | None,
    warnings: list[str],
) -> None:
    """Miter incident rib pairs at each node per ``policy``.

    When ``skip_hub_valence`` is set, nodes of that valence or higher are left
    to another joint mechanism (a hub node's ribs were pulled back and no longer
    meet, so a miter there would miss).
    """
    if policy is MiterPolicy.NONE:
        return
    for node in nodes:
        incident = list(node.edge_indices)
        if len(incident) < 2:
            continue
        if skip_hub_valence is not None and node.valence >= skip_hub_valence:
            continue
        if policy is MiterPolicy.VALENCE_2_ONLY:
            if len(incident) == 2:
                _miter_pair(beams, incident[0], incident[1], warnings)
        elif policy is MiterPolicy.THROUGH_PAIR:
            pair = _straightest_pair(node, edges, incident)
            if pair is not None:
                _miter_pair(beams, pair[0], pair[1], warnings)
        elif policy is MiterPolicy.ALL_PAIRS:
            for i in range(len(incident)):
                for j in range(i + 1, len(incident)):
                    _miter_pair(beams, incident[i], incident[j], warnings)


def _miter_pair(
    beams: list["Beam"], edge_a: int, edge_b: int, warnings: list[str]
) -> None:
    if not ops.cut_with_miter(beams[edge_a], beams[edge_b]):
        warnings.append(f"miter: cut missed between edges {edge_a} and {edge_b}")


def _straightest_pair(
    node: "GridNode", edges: list["GridEdge"], incident: list[int]
) -> tuple[int, int] | None:
    """The incident edge pair whose directions are closest to anti-parallel.

    That is the ridge/through line crossing the node — the one pair a single
    miter joins cleanly.
    """
    directions: list[tuple[int, object]] = []
    for edge_index in incident:
        edge = edges[edge_index]
        away_1 = edge.p2 - node.position
        away_2 = edge.p1 - node.position
        away = away_1 if away_1.magnitude() >= away_2.magnitude() else away_2
        if away.is_zero():
            continue
        directions.append((edge_index, away.normalized()))

    best: tuple[int, int] | None = None
    best_dot = float("inf")
    for i in range(len(directions)):
        for j in range(i + 1, len(directions)):
            dot = directions[i][1].dot(directions[j][1])
            if dot < best_dot:
                best_dot = dot
                best = (directions[i][0], directions[j][0])
    return best
