"""Value objects and policy enums for the gridshell module.

These are the small, self-validating types the gridshell builders and
strategies pass around: the deduplicated :class:`GridEdge` / :class:`GridNode`
topology records, the :class:`MiterPolicy` / :class:`TrimPolicy` choices, and
the :class:`GridShellResult` returned by ``GridShellBuilder.build()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from pycadwork.geometry import Point3D, Vector3D

if TYPE_CHECKING:
    from pycadwork.element.beam import Beam
    from pycadwork.element.connector_axis import ConnectorAxis
    from pycadwork.element.drilling import Drilling
    from pycadwork.element.plate import Plate


class MiterPolicy(Enum):
    """How to miter beams that share a node.

    ``cut_with_miter`` joins exactly two beams, so only ``VALENCE_2_ONLY`` is
    unconditionally correct; the higher-valence policies are opt-in.
    """

    NONE = "none"
    #: Miter only genuine two-rib corners/seams; leave higher-valence nodes butted.
    VALENCE_2_ONLY = "valence_2_only"
    #: At each node miter the single straightest through-pair, butt the rest.
    THROUGH_PAIR = "through_pair"
    #: Miter every incident pair. For valence > 2 later cuts clobber earlier
    #: ones on a shared beam end — only meaningful when the caller accepts that.
    ALL_PAIRS = "all_pairs"


class TrimPolicy(Enum):
    """Where a rib sits relative to the shell surface.

    A rib runs along a mesh edge with its height along the surface normal, so
    the edge lies *inside* the shell. Boolean-cutting the rib with the face's
    support plane is degenerate (the plane contains the rib axis), so "trim to
    surface" is realized by offsetting the rib at creation, not by a cut.
    """

    #: Rib centred on the mesh edge (bisected by the shell); ribs meet exactly
    #: at nodes, giving clean miters. Default.
    NONE = "none"
    #: Rib offset below the shell by half its height, so its top face is flush
    #: with the surface. No cut is performed.
    SEAT_ON_SURFACE = "seat_on_surface"


@dataclass(frozen=True, slots=True)
class HubJoint:
    """Setback joint: trim each rib back from multi-rib nodes so it is producible.

    A triangulated shell has high-valence interior nodes (six ribs at one point),
    which cannot be reconciled as mutual miters. Instead every rib is pulled back
    from each such node by ``gap``, leaving a straight stick with a plain flat
    (perpendicular) end cut and a node void that hosts a connector. The setback is
    realized by shortening the axis at creation, never a cut (see
    :class:`TrimPolicy`).

    ``gap`` is the setback distance from the node centre; ``min_valence`` is the
    lowest node valence treated as a hub — valence-2 corners are left to the miter.
    """

    gap: float
    min_valence: int = 3

    def __post_init__(self) -> None:
        if self.gap <= 0.0:
            raise ValueError("HubJoint.gap must be positive")
        if self.min_valence < 3:
            raise ValueError(
                "HubJoint.min_valence must be >= 3 (valence-2 nodes mitre)"
            )


@dataclass(frozen=True, slots=True)
class GridEdge:
    """A unique lattice edge with its section-orientation up-vector.

    ``face_indices`` records how many faces share the edge: 1 = boundary,
    2 = interior (manifold), > 2 = non-manifold. ``up`` is the (averaged)
    surface normal along the edge, perpendicular to the edge direction.
    """

    p1: Point3D
    p2: Point3D
    up: Vector3D
    face_indices: tuple[int, ...]
    node_ids: tuple[int, int]

    @property
    def valence(self) -> int:
        return len(self.face_indices)

    @property
    def is_boundary(self) -> bool:
        return len(self.face_indices) == 1


@dataclass(frozen=True, slots=True)
class GridNode:
    """A lattice node: a canonical vertex and the edges incident to it."""

    position: Point3D
    edge_indices: tuple[int, ...]

    @property
    def valence(self) -> int:
        return len(self.edge_indices)


@dataclass(frozen=True, slots=True)
class GridShellResult:
    """What a gridshell build produced, plus any non-fatal warnings.

    ``connectors`` / ``drillings`` are the joinery a joint strategy placed at the
    nodes (empty unless the strategy creates them); ``laths`` are the continuous
    members of a double-layer lath build. A build reports the joinery it made so
    the caller need not recompute which nodes are hubs.
    """

    members: tuple["Beam", ...] = ()
    panels: tuple["Plate", ...] = ()
    laths: tuple["Beam", ...] = ()
    connectors: tuple["ConnectorAxis", ...] = ()
    drillings: tuple["Drilling", ...] = ()
    nodes: tuple[GridNode, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)
