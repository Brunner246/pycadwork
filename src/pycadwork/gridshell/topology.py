"""Grid topology: turn a faceted Brep into deduplicated nodes and edges.

A :class:`~pycadwork.geometry.Brep` is a flat list of planar faces with **no**
shared-edge or shared-vertex topology (see ``geometry/brep.py``). The gridshell
needs that topology: one beam per *unique* edge, and the set of beams meeting at
each *shared* node. :class:`GridTopology` rebuilds it.

Vertices are deduplicated with an epsilon-quantized hash map rather than the
``SpatialIndex3D`` R-tree, because rtree is an optional native dependency that
is absent in cadwork's embedded Python — a hard dependency here would break the
module inside cadwork. The quantized map is deterministic and O(V).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pycadwork.geometry import Point3D, Vector3D
from pycadwork.gridshell.specs import GridEdge, GridNode

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pycadwork.geometry import Brep, Face


@dataclass
class _EdgeAccum:
    """Mutable accumulator for one undirected edge while scanning faces."""

    raw: tuple[int, int]
    face_indices: list[int] = field(default_factory=list)


class GridTopology:
    """Deduplicated node/edge/face topology extracted from triangulated breps."""

    __slots__ = ("_edges", "_nodes", "_faces", "_warnings")

    def __init__(
        self,
        edges: list[GridEdge],
        nodes: list[GridNode],
        faces: list["Face"],
        warnings: list[str],
    ) -> None:
        self._edges = edges
        self._nodes = nodes
        self._faces = faces
        self._warnings = warnings

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_breps(
        cls,
        breps: "Iterable[Brep]",
        *,
        tolerance: float = 1e-6,
        strict: bool = True,
    ) -> "GridTopology":
        """Build topology from one or more triangulated breps.

        Every face must be a triangle (requirement: the input is a triangulated
        surface). With ``strict`` a non-triangular or degenerate face raises
        ``ValueError``; otherwise it is skipped and recorded in :meth:`warnings`.
        """
        if tolerance <= 0.0:
            raise ValueError("GridTopology.from_breps: tolerance must be positive")

        vertices: list[Point3D] = []
        key_to_vid: dict[tuple[int, int, int], int] = {}
        faces: list[Face] = []
        face_normals: list[Vector3D] = []
        edges: dict[tuple[int, int], _EdgeAccum] = {}
        warnings: list[str] = []

        def canonical(point: Point3D) -> int:
            key = (
                round(point.x / tolerance),
                round(point.y / tolerance),
                round(point.z / tolerance),
            )
            vid = key_to_vid.get(key)
            if vid is None:
                vid = len(vertices)
                key_to_vid[key] = vid
                vertices.append(point)
            return vid

        def reject(message: str) -> None:
            if strict:
                raise ValueError(message)
            warnings.append(message)

        for brep in breps:
            for face in brep.faces:
                loop = face.outer_loop
                if loop.vertex_count() != 3:
                    reject(
                        "GridTopology: face is not a triangle "
                        f"({loop.vertex_count()} vertices); input must be triangulated"
                    )
                    continue
                vids = [canonical(v) for v in loop.vertices]
                if len(set(vids)) < 3:
                    reject("GridTopology: degenerate triangle (coincident vertices)")
                    continue

                face_index = len(faces)
                faces.append(face)
                face_normals.append(face.normal)
                for k in range(3):
                    a, b = vids[k], vids[(k + 1) % 3]
                    edge_key = (a, b) if a < b else (b, a)
                    accum = edges.get(edge_key)
                    if accum is None:
                        accum = _EdgeAccum(raw=(a, b))
                        edges[edge_key] = accum
                    accum.face_indices.append(face_index)

        grid_edges: list[GridEdge] = []
        node_edges: dict[int, list[int]] = {}
        for edge_index, accum in enumerate(edges.values()):
            a, b = accum.raw
            up = _averaged_up([face_normals[fi] for fi in accum.face_indices])
            grid_edges.append(
                GridEdge(
                    p1=vertices[a],
                    p2=vertices[b],
                    up=up,
                    face_indices=tuple(accum.face_indices),
                    node_ids=(a, b),
                )
            )
            node_edges.setdefault(a, []).append(edge_index)
            node_edges.setdefault(b, []).append(edge_index)

        grid_nodes = [
            GridNode(position=vertices[vid], edge_indices=tuple(node_edges[vid]))
            for vid in sorted(node_edges)
        ]
        return cls(grid_edges, grid_nodes, faces, warnings)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def edges(self) -> list[GridEdge]:
        return list(self._edges)

    def nodes(self) -> list[GridNode]:
        return list(self._nodes)

    def faces(self) -> list["Face"]:
        """The retained triangular faces, index-aligned with ``GridEdge.face_indices``."""
        return list(self._faces)

    def warnings(self) -> list[str]:
        return list(self._warnings)


def _averaged_up(normals: list[Vector3D]) -> Vector3D:
    """Normalized sum of adjacent face normals; falls back to the first normal.

    Each face normal is perpendicular to the shared edge (the edge lies in the
    face), so the average stays perpendicular to the edge — a valid third point
    for ``AxisPoints`` that never collapses onto the beam axis.
    """
    total = Vector3D.zero()
    for normal in normals:
        total = total + normal
    if total.is_zero():
        return normals[0].normalized()
    return total.normalized()
