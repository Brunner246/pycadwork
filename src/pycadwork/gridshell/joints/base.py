"""The pluggable joint abstraction the members strategy delegates to.

A gridshell's node joinery is the hard part: how do the ribs meeting at a
lattice node resolve into producible geometry? Rather than bake one answer into
:func:`~pycadwork.gridshell.members.build_members`, that pipeline delegates to a
:class:`JointStrategy` — so a caller picks a miter fan, a hub connector, a
radial bisector cut, or a lap joint per build (see the concrete strategies in
this package).

A strategy participates in two phases, mirroring how the members pipeline works:

* :meth:`JointStrategy.setback` (pre-creation) — how far to pull each rib end in
  from its node *before* the beam is created. This is an axis edit, never a
  boolean cut: a plane through a rib's own axis is degenerate for ACIS (see
  :class:`~pycadwork.gridshell.specs.TrimPolicy`), so shortening the axis at
  creation is the only clean way to open a node void.
* :meth:`JointStrategy.resolve` (post-creation) — the real joinery on the
  already-created beams: miters, plane cuts, connectors, drillings. The strategy
  records what it produced (and any non-fatal misses) on the :class:`JointContext`.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pycadwork.geometry import Plane3D, Point3D, Vector3D

if TYPE_CHECKING:
    from pycadwork.element.beam import Beam
    from pycadwork.element.connector_axis import ConnectorAxis
    from pycadwork.element.drilling import Drilling
    from pycadwork.geometry import RectSection
    from pycadwork.gridshell.specs import GridEdge, GridNode
    from pycadwork.gridshell.topology import GridTopology


@dataclass(frozen=True, slots=True)
class SetbackRequest:
    """The per-edge context a strategy needs to decide its axial pull-in.

    ``valence_a`` / ``valence_b`` are the rib counts at the edge's two nodes
    (``edge.node_ids[0]`` / ``[1]``), so a strategy can pull back only the ends
    that land on a multi-rib hub.
    """

    edge: "GridEdge"
    index: int
    valence_a: int
    valence_b: int
    section: "RectSection"


@dataclass(slots=True)
class JointContext:
    """The mutable model view a strategy resolves against, plus its output sinks.

    ``beams`` is index-aligned with ``topology.edges()`` — ``beams[i]`` is the
    rib on edge ``i``. A strategy appends the joinery it creates to
    :attr:`connectors` / :attr:`drillings` and any non-fatal misses to
    :attr:`warnings`; the members pipeline folds these into the
    :class:`~pycadwork.gridshell.specs.GridShellResult`.
    """

    topology: "GridTopology"
    beams: list["Beam"]
    section: "RectSection"
    tolerance: float = 1e-6
    warnings: list[str] = field(default_factory=list)
    connectors: list["ConnectorAxis"] = field(default_factory=list)
    drillings: list["Drilling"] = field(default_factory=list)


class JointStrategy(ABC):
    """How ribs meeting at gridshell nodes are turned into producible joints.

    Subclasses override :meth:`resolve` (required) and, when they open a node
    void, :meth:`setback` (optional; the default is no pull-in).
    """

    __slots__ = ()

    def setback(
        self, request: SetbackRequest, warnings: list[str]
    ) -> tuple[float, float]:
        """Axial pull-in ``(start, end)`` for this rib, in model units.

        Returns ``(0.0, 0.0)`` by default — most joints leave the ribs meeting
        at the node. A strategy that opens a void returns a positive pull for
        each end whose node is a hub, and is responsible for its own
        too-short guard (append a warning and return ``(0.0, 0.0)`` rather than
        produce a degenerate stick).
        """
        return (0.0, 0.0)

    @abstractmethod
    def resolve(self, context: JointContext) -> None:
        """Apply the joinery to the created beams in ``context``."""


# ---- shared node geometry ----


def node_normal(node: "GridNode", edges: list["GridEdge"]) -> Vector3D:
    """Averaged shell normal at a node: the sum of its incident edges' up-vectors.

    Each ``edge.up`` is perpendicular to that edge and points off the shell, so
    their sum is a stable outward normal at the node (it never collapses onto a
    rib axis).
    """
    total = Vector3D.zero()
    for edge_index in node.edge_indices:
        total = total + edges[edge_index].up
    if total.is_zero():
        return edges[node.edge_indices[0]].up.normalized()
    return total.normalized()


def _outward(edge: "GridEdge", origin: Point3D) -> Vector3D | None:
    """Unit direction from ``origin`` toward the edge's far endpoint."""
    away_1 = edge.p2 - origin
    away_2 = edge.p1 - origin
    away = away_1 if away_1.magnitude() >= away_2.magnitude() else away_2
    if away.is_zero():
        return None
    return away.normalized()


def _tangent_reference(normal: Vector3D) -> Vector3D:
    """Any unit vector in the plane perpendicular to ``normal`` (a basis seed)."""
    seed = Vector3D.unit_x() if abs(normal.x) < 0.9 else Vector3D.unit_y()
    return normal.cross(seed).normalized()


class NodeFan:
    """The ribs meeting at a node, ordered by angle around its shell normal.

    Projects each incident rib's outward direction onto the node's tangent plane
    and sorts them, so the ribs form a fan. :meth:`bisector_cuts` returns, per
    rib, the angular-bisector planes that trim it to its own sector — the basis
    of a radial (multi-rib) miter.
    """

    __slots__ = ("position", "normal", "_ribs")

    def __init__(self, node: "GridNode", edges: list["GridEdge"]) -> None:
        self.position: Point3D = node.position
        self.normal: Vector3D = node_normal(node, edges)
        u = _tangent_reference(self.normal)
        v = self.normal.cross(u)
        ribs: list[tuple[float, int, Vector3D]] = []
        for edge_index in node.edge_indices:
            outward = _outward(edges[edge_index], node.position)
            if outward is None:
                continue
            tangent = outward - self.normal * outward.dot(self.normal)
            if tangent.is_zero():
                continue  # rib runs along the normal — no angular position
            tangent = tangent.normalized()
            angle = math.atan2(tangent.dot(v), tangent.dot(u))
            ribs.append((angle, edge_index, tangent))
        ribs.sort(key=lambda item: item[0])
        self._ribs = ribs

    def bisector_cuts(self) -> dict[int, list[Plane3D]]:
        """Per rib ``edge_index``, the oriented planes trimming it to its sector.

        Each plane contains the node position and the shell normal and lies on
        the angular bisector between two neighbouring ribs; it is oriented to
        remove the material of *this* rib that overlaps its neighbour. A rib
        gets one plane per angular neighbour (two at an interior fan rib).
        """
        cuts: dict[int, list[Plane3D]] = {ei: [] for _, ei, _ in self._ribs}
        count = len(self._ribs)
        if count < 2:
            return cuts
        for i in range(count):
            _, a_index, a_dir = self._ribs[i]
            _, b_index, b_dir = self._ribs[(i + 1) % count]
            bisector = a_dir + b_dir
            if bisector.is_zero():
                continue  # (near-)collinear ribs: no wedge to trim between them
            normal = self.normal.cross(bisector.normalized())
            if normal.is_zero():
                continue
            normal = normal.normalized()
            # Orient so the plane normal points toward rib b's side (the side of
            # rib a to remove); rib b is trimmed by the opposite orientation.
            if b_dir.dot(normal) < 0.0:
                normal = -normal
            cuts[a_index].append(Plane3D.from_point_and_normal(self.position, normal))
            cuts[b_index].append(Plane3D.from_point_and_normal(self.position, -normal))
        return cuts
