"""SpherePavilionBuilder: a triangulated timber dome on a clean base ring + slab.

The pipeline reuses the gridshell realization stack wholesale — a geodesic
icosphere is just another triangle soup, and
:class:`~pycadwork.gridshell.topology.GridTopology` /
:func:`~pycadwork.gridshell.members.build_members` /
:class:`~pycadwork.gridshell.joints.RadialMiterJoint` are surface-agnostic. This
builder only adds what is sphere-specific: generating the mesh
(:mod:`~pycadwork.sphere.icosphere`), truncating it at a natural node ring so the
base is a clean coplanar polygon, gapped cladding
(:mod:`~pycadwork.sphere.cladding`), a **sill ring** band along that base, an
optional **foundation slab**, and the strut schedule.

The default node joint is the **radial bisector cut** ("shift cut"):
:class:`RadialMiterJoint` cuts every strut at a 5–6-strut node on the
angular-bisector planes, so the whole rosette butts on shared flat faces with no
void. A ground cut snaps to the nearest geodesic node ring (the base icosahedron
is oriented pole-up so those rings are horizontal); the base-ring edges become a
dedicated sill band rather than struts, and the dome is lifted so the base sits
on ``z = 0``. Config methods return ``self``; the terminal :meth:`build` produces
frame, cladding, ring, and foundation together.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pycadwork.element.beam import Beam
from pycadwork.element.plate import Plate
from pycadwork.geometry import AxisPoints, Point3D, RectSection, Vector3D
from pycadwork.gridshell.joints import RadialMiterJoint
from pycadwork.gridshell.members import build_members
from pycadwork.gridshell.topology import GridTopology
from pycadwork.sphere.cladding import build_cladding
from pycadwork.sphere.icosphere import (
    Triangle,
    faces_to_surfaces,
    icosphere_faces,
    ring_levels,
    snap_boundary_to_plane,
    truncate_at_ring,
)
from pycadwork.sphere.specs import SpherePavilionResult, StrutGroup

if TYPE_CHECKING:
    from pycadwork.gridshell.joints.base import JointStrategy
    from pycadwork.gridshell.specs import GridEdge


class SpherePavilionBuilder:
    """Assemble a triangulated timber dome (frame, cladding, sill ring, slab)."""

    def __init__(self, radius: float) -> None:
        if radius <= 0.0:
            raise ValueError("SpherePavilionBuilder: radius must be positive")
        self._radius = float(radius)
        self._frequency = 3
        self._center: Point3D | None = None
        self._ground_cut: float | None = None
        self._section: RectSection | None = None
        self._sill_section: RectSection | None = None
        self._cladding: tuple[float, float] | None = None
        self._foundation: tuple[float, str, float] | None = None
        self._joint: "JointStrategy | None" = None
        self._strut_tolerance = 1.0
        self._tolerance = 1e-6
        self._strict = True

    # ---- configuration (return self) ----

    def frequency(self, frequency: int) -> "SpherePavilionBuilder":
        """Icosahedron subdivision level (``20 * frequency²`` triangles)."""
        if frequency < 1:
            raise ValueError("SpherePavilionBuilder.frequency must be >= 1")
        self._frequency = frequency
        return self

    def center(self, center: Point3D) -> "SpherePavilionBuilder":
        """Place the sphere centre. With a ground cut only the XY matters — the
        base is always lifted onto ``z = 0`` so the dome stands on the ground."""
        self._center = center
        return self

    def ground_cut(self, distance_below_center: float) -> "SpherePavilionBuilder":
        """Truncate at the natural node ring nearest ``distance`` below the centre.

        ``0`` snaps to the ring nearest the equator; larger values leave more of
        the sphere. The cut always lands on a ring of coplanar nodes, so the base
        is a clean regular polygon, and the dome is lifted so that base sits on
        ``z = 0`` (it stands on the ground).
        """
        if distance_below_center < 0.0:
            raise ValueError("SpherePavilionBuilder.ground_cut must not be negative")
        self._ground_cut = float(distance_below_center)
        return self

    def timber(self, section: RectSection) -> "SpherePavilionBuilder":
        """Strut cross-section for the dome members."""
        self._section = section
        return self

    def sill(self, section: RectSection) -> "SpherePavilionBuilder":
        """Cross-section for the base sill ring (default: the timber section)."""
        self._sill_section = section
        return self

    def cladding(self, thickness: float, gap: float) -> "SpherePavilionBuilder":
        """Clad the faces with panels of ``thickness`` and a uniform ``gap``."""
        self._cladding = (float(thickness), float(gap))
        return self

    def foundation(
        self, thickness: float, *, material: str = "Concrete", margin: float = 0.0
    ) -> "SpherePavilionBuilder":
        """Add a solid slab of ``thickness`` under the base footprint.

        The slab covers the base polygon (optionally grown outward by ``margin``)
        and extrudes downward from the base plane. Needs a ground cut to have a
        base to sit under.
        """
        if thickness <= 0.0:
            raise ValueError(
                "SpherePavilionBuilder.foundation thickness must be positive"
            )
        if margin < 0.0:
            raise ValueError(
                "SpherePavilionBuilder.foundation margin must not be negative"
            )
        self._foundation = (float(thickness), material, float(margin))
        return self

    def joint(self, strategy: "JointStrategy") -> "SpherePavilionBuilder":
        """Override the node joint (default: radial bisector ``RadialMiterJoint``)."""
        self._joint = strategy
        return self

    def strut_tolerance(self, tolerance: float) -> "SpherePavilionBuilder":
        """Length quantum for bucketing struts into length classes (default 1.0)."""
        if tolerance <= 0.0:
            raise ValueError("SpherePavilionBuilder.strut_tolerance must be positive")
        self._strut_tolerance = float(tolerance)
        return self

    def with_tolerance(self, tolerance: float) -> "SpherePavilionBuilder":
        """Vertex-merge tolerance for stitching shared triangle vertices."""
        self._tolerance = tolerance
        return self

    def lenient(self, lenient: bool = True) -> "SpherePavilionBuilder":
        """Skip (and warn about) degenerate faces instead of raising."""
        self._strict = not lenient
        return self

    # ---- terminal ----

    def build(self) -> SpherePavilionResult:
        """Generate the mesh, realize frame/cladding/ring/foundation, and schedule."""
        if self._section is None and self._cladding is None:
            raise ValueError(
                "SpherePavilionBuilder.build: nothing to build; "
                "call timber(...) and/or cladding(...) first"
            )

        center, faces = self._meshed()
        topology = GridTopology.from_breps(
            [surface.geometry.brep for surface in faces_to_surfaces(faces)],
            tolerance=self._tolerance,
            strict=self._strict,
        )
        warnings = list(topology.warnings())
        edges = topology.edges()
        boundary = [edge for edge in edges if edge.is_boundary]

        members, ring = self._frame_and_ring(topology, edges, boundary, warnings)
        panels = self._cladding_panels(topology, center, warnings)
        foundation = self._foundation_slab(boundary, topology, center, warnings)

        return SpherePavilionResult(
            members=tuple(members),
            panels=tuple(panels),
            ring=tuple(ring),
            foundation=foundation,
            strut_groups=tuple(self._strut_schedule(edges)),
            nodes=tuple(topology.nodes()),
            warnings=tuple(warnings),
        )

    # ---- mesh ----

    def _meshed(self) -> tuple[Point3D, list[Triangle]]:
        """The sphere centre and its (optionally ring-truncated, lifted) faces."""
        center = self._center if self._center is not None else Point3D.origin()
        faces = icosphere_faces(self._radius, self._frequency, center)
        if self._ground_cut is None:
            return center, faces

        target = center.z - self._ground_cut
        levels = ring_levels(faces, tolerance=self._tolerance)
        ring_z = min(levels, key=lambda z: abs(z - target))
        faces = truncate_at_ring(faces, ring_z, tolerance=self._tolerance)
        # Flatten the crenellated perimeter onto the ring so the base is a single
        # coplanar polygon (clean sill ring + slab footprint).
        faces = snap_boundary_to_plane(faces, ring_z, tolerance=self._tolerance)
        # A ground cut always lands the base on z=0 (the dome stands on the
        # ground); an explicit centre only places the dome in plan (XY).
        faces = [tuple(p + Vector3D(0.0, 0.0, -ring_z) for p in tri) for tri in faces]
        center = Point3D(center.x, center.y, center.z - ring_z)
        return center, faces

    # ---- frame + sill ring ----

    def _frame_and_ring(
        self,
        topology: GridTopology,
        edges: list["GridEdge"],
        boundary: list["GridEdge"],
        warnings: list[str],
    ) -> tuple[list[Beam], list[Beam]]:
        """Struts (interior edges) plus the sill ring (boundary edges rebuilt)."""
        if self._section is None:
            return [], []
        strategy = self._joint if self._joint is not None else RadialMiterJoint()
        frame = build_members(topology, self._section, strategy=strategy)
        warnings.extend(frame.warnings)

        members: list[Beam] = []
        ring: list[Beam] = []
        sill_section = (
            self._sill_section if self._sill_section is not None else self._section
        )
        for beam, edge in zip(frame.members, edges):
            if edge.is_boundary:
                beam.delete()  # rebuilt below as a dedicated sill beam
            else:
                members.append(beam)
        for edge in boundary:
            ring.append(self._sill_beam(edge, sill_section))
        return members, ring

    def _sill_beam(self, edge: "GridEdge", section: RectSection) -> Beam:
        """One horizontal base-ring beam standing upright along the edge."""
        beam = Beam.create_rectangular(
            section, AxisPoints(edge.p1, edge.p2, edge.p1 + Vector3D.unit_z())
        )
        beam.attrs.name = "Base Ring"
        return beam

    # ---- cladding ----

    def _cladding_panels(
        self, topology: GridTopology, center: Point3D, warnings: list[str]
    ) -> list[Plate]:
        if self._cladding is None:
            return []
        thickness, gap = self._cladding
        panels, cladding_warnings = build_cladding(
            topology, thickness=thickness, gap=gap, center=center
        )
        warnings.extend(cladding_warnings)
        return panels

    # ---- foundation ----

    def _foundation_slab(
        self,
        boundary: list["GridEdge"],
        topology: GridTopology,
        center: Point3D,
        warnings: list[str],
    ) -> Plate | None:
        if self._foundation is None:
            return None
        if not boundary:
            warnings.append("foundation: no base ring (set ground_cut first); skipped")
            return None

        thickness, material, margin = self._foundation
        nodes = topology.nodes()
        node_ids = {nid for edge in boundary for nid in edge.node_ids}
        polygon = _order_by_angle([nodes[nid].position for nid in node_ids], center)
        if margin > 0.0:
            polygon = [_pushed_out(point, center, margin) for point in polygon]

        # Extrude downward: the slab normal (thickness axis) points down, so wind
        # the footprint counter-clockwise about -z for a right-handed solid.
        down = Vector3D(0.0, 0.0, -1.0)
        polygon = _ccw_about(polygon, down)
        x_dir = (polygon[1] - polygon[0]).normalized()
        slab = Plate.create_polygon(
            polygon,
            float(thickness),
            x_local_direction=_as_point(x_dir),
            z_local_direction=_as_point(down),
        )
        if not slab.id:
            warnings.append("foundation: slab not created")
        slab.attrs.name = "Foundation"
        slab.attrs.material_name = material
        return slab

    # ---- strut schedule ----

    def _strut_schedule(self, edges: list["GridEdge"]) -> list[StrutGroup]:
        """Bucket the interior (non-ring) edges into length classes."""
        buckets: dict[int, list[tuple[int, float]]] = {}
        member_index = 0
        for edge in edges:
            if edge.is_boundary:
                continue
            length = float(edge.p1.distance_to(edge.p2))
            key = round(length / self._strut_tolerance)
            buckets.setdefault(key, []).append((member_index, length))
            member_index += 1

        groups: list[StrutGroup] = []
        for entries in buckets.values():
            indices = tuple(index for index, _ in entries)
            nominal = sum(length for _, length in entries) / len(entries)
            groups.append(
                StrutGroup(
                    nominal_length=nominal, count=len(entries), member_indices=indices
                )
            )
        groups.sort(key=lambda group: group.nominal_length)
        return groups


def _order_by_angle(points: list[Point3D], center: Point3D) -> list[Point3D]:
    """Sort points counter-clockwise by their angle about the centre's XY axis."""
    return sorted(points, key=lambda p: math.atan2(p.y - center.y, p.x - center.x))


def _pushed_out(point: Point3D, center: Point3D, margin: float) -> Point3D:
    """Move a point radially outward (in XY) from the centre by ``margin``."""
    radial = Vector3D(point.x - center.x, point.y - center.y, 0.0)
    if radial.is_zero():
        return point
    shift = radial.normalized() * margin
    return Point3D(point.x + shift.x, point.y + shift.y, point.z)


def _ccw_about(points: list[Point3D], normal: Vector3D) -> list[Point3D]:
    """Wind ``points`` counter-clockwise about ``normal`` (right-handed extrusion)."""
    edge_1 = points[1] - points[0]
    edge_2 = points[2] - points[0]
    if edge_1.cross(edge_2).dot(normal) < 0.0:
        return list(reversed(points))
    return points


def _as_point(vector: Vector3D) -> Point3D:
    return Point3D(vector.x, vector.y, vector.z)
