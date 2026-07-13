"""Members strategy: emit one beam per lattice edge, then delegate node joinery.

All boolean/cut work goes through :mod:`pycadwork.ops`; element creation goes
through the ``Beam`` wrapper — this module never touches ``cadwork.*`` directly.
Seating a rib on the shell is done by offsetting it at creation, never by a
plane cut: a plane through the rib's own axis is degenerate (see
:class:`~pycadwork.gridshell.specs.TrimPolicy`).

The pipeline is: seat each rib (offset), pull its ends back per the joint
strategy's :meth:`~pycadwork.gridshell.joints.base.JointStrategy.setback`,
create the beam, then hand the whole lattice to
:meth:`~pycadwork.gridshell.joints.base.JointStrategy.resolve` for the real
joinery (miters, connectors, cuts). The *how* of the node joint lives entirely
in the strategy — this module only builds and orients the sticks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycadwork.element.beam import Beam
from pycadwork.geometry import AxisPoints, RectSection
from pycadwork.gridshell.joints.base import JointContext, JointStrategy, SetbackRequest
from pycadwork.gridshell.joints.miter import MiterJoint
from pycadwork.gridshell.specs import GridShellResult, TrimPolicy

if TYPE_CHECKING:
    from pycadwork.gridshell.specs import GridEdge
    from pycadwork.gridshell.topology import GridTopology


def build_members(
    topology: "GridTopology",
    section: RectSection,
    *,
    strategy: JointStrategy | None = None,
    trim: TrimPolicy = TrimPolicy.NONE,
) -> GridShellResult:
    """Build a beam lattice from ``topology`` and return the created members.

    ``strategy`` decides all node joinery (default: miter genuine two-rib
    corners). ``trim`` seats the ribs flush on the shell by offsetting them.
    """
    strategy = strategy if strategy is not None else MiterJoint()
    warnings = list(topology.warnings())
    edges = topology.edges()
    valence = _valence_by_node(edges)

    seat = trim is TrimPolicy.SEAT_ON_SURFACE
    half_height = section.height / 2.0

    beams: list[Beam] = []
    for index, edge in enumerate(edges):
        p1, p2 = edge.p1, edge.p2
        if seat:
            # Drop the rib half its height along the normal so its top face
            # lies flush on the shell — an offset, not a boolean cut (see
            # TrimPolicy).
            offset = edge.up * (-half_height)
            p1, p2 = p1 + offset, p2 + offset
        request = SetbackRequest(
            edge=edge,
            index=index,
            valence_a=valence.get(edge.node_ids[0], 0),
            valence_b=valence.get(edge.node_ids[1], 0),
            section=section,
        )
        p1, p2 = _apply_setback(p1, p2, strategy.setback(request, warnings))
        # p3 puts the local z (height) along the surface normal, so the rib
        # stands on-edge following the shell; up is perpendicular to the axis.
        p3 = p1 + edge.up
        beams.append(Beam.create_rectangular(section, AxisPoints(p1, p2, p3)))

    context = JointContext(
        topology=topology,
        beams=beams,
        section=section,
        warnings=warnings,
    )
    strategy.resolve(context)

    return GridShellResult(
        members=tuple(beams),
        nodes=tuple(topology.nodes()),
        connectors=tuple(context.connectors),
        drillings=tuple(context.drillings),
        warnings=tuple(context.warnings),
    )


def _valence_by_node(edges: list["GridEdge"]) -> dict[int, int]:
    """Incident-edge count per node id (matches ``GridNode.valence``)."""
    valence: dict[int, int] = {}
    for edge in edges:
        a, b = edge.node_ids
        valence[a] = valence.get(a, 0) + 1
        valence[b] = valence.get(b, 0) + 1
    return valence


def _apply_setback(p1, p2, pulls: tuple[float, float]):
    """Pull the rib ends inward along its own axis by ``(start, end)``.

    Shortening the axis at creation gives a producible stick with flat ends and
    a node void for a connector — never a cut. The strategy is responsible for
    returning pulls that leave a non-degenerate stick.
    """
    pull_start, pull_end = pulls
    if not pull_start and not pull_end:
        return p1, p2
    unit = (p2 - p1).normalized()
    if pull_start:
        p1 = p1 + unit * pull_start
    if pull_end:
        p2 = p2 - unit * pull_end
    return p1, p2
