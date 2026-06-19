"""In-memory fake of :class:`CadworkAdapter` for tests.

Same shape as the real adapter — duck-typed, no Protocol needed. All five
sub-adapters share one :class:`FakeState` so a mutation on
``fake.attributes.set_name`` is immediately visible to ``fake.geometry`` and
to ``fake.grouping`` filter queries.

Behavioural surface is deliberately permissive: it accepts whatever inputs
the OOP layer sends and remembers them, so tests can round-trip
(create → read back) without a real CAD kernel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from pycadwork.cadwork_adapter.types import (
    CoverKind,
    ElementId,
    ElementTypeSnapshot,
    FacetListLike,
    GroupingMode,
    MaterialId,
    MaterialSnapshot,
    PointTuple,
)
from pycadwork.geometry.plane3d import Plane3D
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.specs import (
    AxisFrame,
    AxisPoints,
    PanelSection,
    RectSection,
    Segment,
)

if TYPE_CHECKING:
    from pycadwork.detail.properties import ModuleProperties

# ---- vertex / facet view types ----


@dataclass
class _FakePoint:
    x: float
    y: float
    z: float


@dataclass
class _FakeVertexList:
    points: list[_FakePoint] = field(default_factory=list)

    def count(self) -> int:
        return len(self.points)

    def at(self, index: int) -> _FakePoint:
        return self.points[index]


@dataclass
class _FakeVertexListList:
    items: list[_FakeVertexList]

    def count(self) -> int:
        return len(self.items)

    def at(self, index: int) -> _FakeVertexList:
        return self.items[index]


@dataclass
class _FakeFacetList:
    facets: list[tuple[_FakeVertexList, list[_FakeVertexList], _FakePoint]] = field(
        default_factory=list
    )

    def count(self) -> int:
        return len(self.facets)

    def get_external_polygon(self, index: int) -> _FakeVertexList:
        return self.facets[index][0]

    def get_internal_polygons(self, index: int) -> _FakeVertexListList:
        return _FakeVertexListList(self.facets[index][1])

    def get_normal_vector(self, index: int) -> _FakePoint:
        return self.facets[index][2]


# ---- vector math helpers (private to the fake) ----


def _distance(a: PointTuple, b: PointTuple) -> float:
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def _normalize(v: PointTuple) -> PointTuple:
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n == 0:
        return v
    return (v[0] / n, v[1] / n, v[2] / n)


def _sub(a: PointTuple, b: PointTuple) -> PointTuple:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: PointTuple, b: PointTuple) -> PointTuple:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _tup(p: Point3D) -> PointTuple:
    return (p.x, p.y, p.z)


def _segment_aabb_hits(
    start: PointTuple, end: PointTuple, box_min: PointTuple, box_max: PointTuple
) -> list[PointTuple]:
    """Entry/exit points where the segment ``start``->``end`` pierces an AABB.

    Slab method: clip the segment parameter ``t`` to the box on each axis.
    Returns ``[]`` on a miss, ``[entry]`` for a grazing single touch, else
    ``[entry, exit]`` with ``t`` clamped to ``[0, 1]``.
    """
    direction = _sub(end, start)
    t_near, t_far = 0.0, 1.0
    for axis in range(3):
        o, d = start[axis], direction[axis]
        lo, hi = box_min[axis], box_max[axis]
        if abs(d) < 1e-12:
            if o < lo or o > hi:
                return []  # parallel to slab and outside it
            continue
        t1, t2 = (lo - o) / d, (hi - o) / d
        if t1 > t2:
            t1, t2 = t2, t1
        t_near = max(t_near, t1)
        t_far = min(t_far, t2)
        if t_near > t_far:
            return []

    def _at(t: float) -> PointTuple:
        return (
            start[0] + direction[0] * t,
            start[1] + direction[1] * t,
            start[2] + direction[2] * t,
        )

    if abs(t_far - t_near) < 1e-12:
        return [_at(t_near)]
    return [_at(t_near), _at(t_far)]


def _frame_from_three_points(
    el: "_FakeElement", p1: Point3D, p2: Point3D, p3: Point3D
) -> None:
    """Mirror cadwork's three-point local-frame derivation."""
    t1, t2, t3 = _tup(p1), _tup(p2), _tup(p3)
    el.p1, el.p2, el.p3 = t1, t2, t3
    el.xl = _normalize(_sub(t2, t1))
    z_hint = _normalize(_sub(t3, t1))
    el.yl = _normalize(_cross(z_hint, el.xl))
    el.zl = _normalize(_cross(el.xl, el.yl))
    el.length = _distance(t1, t2)


# ---- in-memory element + shared state ----


@dataclass
class _FakeElement:
    eid: ElementId
    snapshot: ElementTypeSnapshot
    name: str = ""
    group: str = ""
    subgroup: str = ""
    wall_situation: str = ""
    comment: str = ""
    material: str = ""
    sku: str = ""
    production_number: int = 0
    part_number: str = ""
    cadwork_guid: str = ""
    additional_data: str = ""
    assembly_number: str = ""
    color: int = 0
    building: str = ""
    storey: str = ""
    container_parent: ElementId = 0
    user_attributes: dict[int, str] = field(default_factory=dict)
    p1: PointTuple = (0.0, 0.0, 0.0)
    p2: PointTuple = (0.0, 0.0, 0.0)
    p3: PointTuple = (0.0, 0.0, 0.0)
    xl: PointTuple = (1.0, 0.0, 0.0)
    yl: PointTuple = (0.0, 1.0, 0.0)
    zl: PointTuple = (0.0, 0.0, 1.0)
    width: float = 0.0
    height: float = 0.0
    length: float = 0.0
    volume: float = 0.0
    weight: float = 0.0
    surface_points: list[PointTuple] = field(default_factory=list)


@dataclass
class FakeState:
    """Shared in-memory store. All sub-adapters mutate this one object."""

    elements: dict[ElementId, _FakeElement] = field(default_factory=dict)
    grouping_mode: GroupingMode = GroupingMode.GROUP
    # building -> storey -> absolute Z elevation of the storey base plane
    storeys: dict[str, dict[str, float]] = field(default_factory=dict)
    _next_id: ElementId = 1
    _next_guid: int = 1
    # behavioural observables — kept (small, exercised by display tests)
    display_refresh_disable_calls: int = 0
    display_refresh_enable_calls: int = 0
    recreate_calls: list[list[ElementId]] = field(default_factory=list)
    # ---- project metadata (global, element-agnostic) ----
    project_guid: str = "fake-project-guid"
    project_name: str = ""
    project_number: str = ""
    project_part: str = ""
    project_architect: str = ""
    project_customer: str = ""
    project_designer: str = ""
    project_deadline: str = ""
    project_description: str = ""
    project_address: str = ""
    project_postal_code: str = ""
    project_city: str = ""
    project_country: str = ""
    project_latitude: float = 0.0
    project_longitude: float = 0.0
    project_elevation: float = 0.0
    project_user_attributes: dict[int, str] = field(default_factory=dict)
    project_user_attribute_names: dict[int, str] = field(default_factory=dict)
    project_data: dict[str, str] = field(default_factory=dict)
    # Active 3d document file name; defaults to a valid 3dc doc so detail tests pass.
    file_name_3dc: str = "model.3dc"
    _next_project_guid: int = 1
    # ---- material catalog (name <-> id, plus the per-material snapshot) ----
    material_by_id: dict[MaterialId, MaterialSnapshot] = field(default_factory=dict)
    material_id_by_name: dict[str, MaterialId] = field(default_factory=dict)
    _next_material_id: int = 1
    # ---- operations observables (recording style) ----
    solder_calls: list[list[ElementId]] = field(default_factory=list)
    subtract_calls: list[tuple[list[ElementId], list[ElementId], bool]] = field(
        default_factory=list
    )
    split_calls: list[list[ElementId]] = field(default_factory=list)
    plane_cut_calls: list[tuple[ElementId, PointTuple, float]] = field(
        default_factory=list
    )
    miter_calls: list[tuple[ElementId, ElementId]] = field(default_factory=list)
    overmeasure_calls: list[tuple[list[ElementId], list[ElementId]]] = field(
        default_factory=list
    )
    processing_group_calls: list[tuple[ElementId, ElementId]] = field(
        default_factory=list
    )
    keep_cutting_bodies_calls: list[tuple[list[ElementId], bool]] = field(
        default_factory=list
    )
    delete_processes_calls: list[list[ElementId]] = field(default_factory=list)
    delete_end_types_calls: list[list[ElementId]] = field(default_factory=list)
    # ---- operations behaviour, seeded by tests ----
    # how many cutting bodies delete_processes_keep_cutting_bodies fabricates per eid
    pending_cutting_bodies: dict[ElementId, int] = field(default_factory=dict)
    # split-off piece ids the next subtract_elements call returns (pop-all)
    pending_subtract_pieces: list[ElementId] = field(default_factory=list)
    # ---- element-module observables ----
    # Records the *mirror* ModuleProperties applied (never a cadwork object).
    module_applied: list[tuple[list[ElementId], "ModuleProperties"]] = field(
        default_factory=list
    )
    # Per-element mirror of the last properties applied, so a reader can read
    # them straight back (the read inverse of apply_properties).
    module_properties: dict[ElementId, "ModuleProperties"] = field(default_factory=dict)
    module_calculation_calls: list[list[ElementId]] = field(default_factory=list)
    module_silent_calculation_calls: list[list[ElementId]] = field(default_factory=list)
    module_detail_path: str | None = None
    # Situation calls: (cover, add, remove) per manual situation write.
    module_parts_situation: list[tuple[ElementId, list[ElementId], list[ElementId]]] = (
        field(default_factory=list)
    )
    module_rough_volume_situation: list[
        tuple[ElementId, list[ElementId], list[ElementId]]
    ] = field(default_factory=list)
    module_auto_parts_situation: list[list[ElementId]] = field(default_factory=list)
    module_auto_rough_volume_situation: list[list[ElementId]] = field(
        default_factory=list
    )

    def alloc(self, snapshot: ElementTypeSnapshot) -> _FakeElement:
        eid = self._next_id
        self._next_id += 1
        guid = f"fake-guid-{self._next_guid:08d}"
        self._next_guid += 1
        el = _FakeElement(eid=eid, snapshot=snapshot, cadwork_guid=guid)
        self.elements[eid] = el
        return el


# ---- sub-adapters ----


class FakeElementsAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    # ---- creation ----

    def create_rectangular_beam_points(
        self, section: RectSection, axis: AxisPoints
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_beam=True, is_rectangular_beam=True)
        el = self._state.alloc(snap)
        _frame_from_three_points(el, axis.p1, axis.p2, axis.p3)
        el.width, el.height = section.width, section.height
        el.volume = section.width * section.height * el.length
        return el.eid

    def create_rectangular_beam_vectors(
        self, section: RectSection, frame: AxisFrame
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_beam=True, is_rectangular_beam=True)
        el = self._state.alloc(snap)
        origin = _tup(frame.origin)
        el.p1 = origin
        x = _normalize((frame.x_dir.x, frame.x_dir.y, frame.x_dir.z))
        el.p2 = (
            origin[0] + x[0] * frame.length,
            origin[1] + x[1] * frame.length,
            origin[2] + x[2] * frame.length,
        )
        z = _normalize((frame.z_dir.x, frame.z_dir.y, frame.z_dir.z))
        el.p3 = (origin[0] + z[0], origin[1] + z[1], origin[2] + z[2])
        el.xl = x
        el.zl = z
        el.yl = _normalize(_cross(z, x))
        el.width, el.height, el.length = section.width, section.height, frame.length
        el.volume = section.width * section.height * frame.length
        return el.eid

    def create_circular_beam_points(
        self, diameter: float, axis: AxisPoints
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_beam=True, is_circular_beam=True)
        el = self._state.alloc(snap)
        _frame_from_three_points(el, axis.p1, axis.p2, axis.p3)
        el.width = el.height = diameter
        return el.eid

    def create_square_beam_points(self, width: float, axis: AxisPoints) -> ElementId:
        snap = ElementTypeSnapshot(is_beam=True, is_rectangular_beam=True)
        el = self._state.alloc(snap)
        _frame_from_three_points(el, axis.p1, axis.p2, axis.p3)
        el.width = el.height = width
        el.volume = width * width * el.length
        return el.eid

    def create_rectangular_panel_points(
        self, section: PanelSection, axis: AxisPoints
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_panel=True)
        el = self._state.alloc(snap)
        _frame_from_three_points(el, axis.p1, axis.p2, axis.p3)
        el.width, el.height = section.width, section.thickness
        el.volume = section.width * section.thickness * el.length
        return el.eid

    def create_rectangular_panel_vectors(
        self, section: PanelSection, frame: AxisFrame
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_panel=True)
        el = self._state.alloc(snap)
        origin = _tup(frame.origin)
        el.p1 = origin
        x = _normalize((frame.x_dir.x, frame.x_dir.y, frame.x_dir.z))
        el.p2 = (
            origin[0] + x[0] * frame.length,
            origin[1] + x[1] * frame.length,
            origin[2] + x[2] * frame.length,
        )
        z = _normalize((frame.z_dir.x, frame.z_dir.y, frame.z_dir.z))
        el.p3 = (origin[0] + z[0], origin[1] + z[1], origin[2] + z[2])
        el.xl, el.zl = x, z
        el.yl = _normalize(_cross(z, x))
        el.width, el.height, el.length = section.width, section.thickness, frame.length
        el.volume = section.width * section.thickness * frame.length
        return el.eid

    def create_drilling_points(self, diameter: float, axis: Segment) -> ElementId:
        snap = ElementTypeSnapshot(is_drilling=True)
        el = self._state.alloc(snap)
        t1, t2 = _tup(axis.p1), _tup(axis.p2)
        el.p1, el.p2 = t1, t2
        el.p3 = (t1[0], t1[1], t1[2] + 1.0)
        el.length = _distance(t1, t2)
        el.width = el.height = diameter
        return el.eid

    def create_circular_mep(self, diameter: float, points: list[Point3D]) -> ElementId:
        snap = ElementTypeSnapshot(is_circular_mep=True)
        el = self._state.alloc(snap)
        t1, t2 = _tup(points[0]), _tup(points[-1])
        el.p1, el.p2 = t1, t2
        el.p3 = (t1[0], t1[1], t1[2] + 1.0)
        el.length = _distance(t1, t2)
        el.width = el.height = diameter
        return el.eid

    def create_rectangular_mep(
        self, width: float, depth: float, points: list[Point3D]
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_rectangular_mep=True)
        el = self._state.alloc(snap)
        t1, t2 = _tup(points[0]), _tup(points[-1])
        el.p1, el.p2 = t1, t2
        el.p3 = (t1[0], t1[1], t1[2] + 1.0)
        el.length = _distance(t1, t2)
        el.width, el.height = width, depth
        return el.eid

    def create_auto_container_from_standard(
        self, eids: list[ElementId], output_name: str, standard_element_name: str
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_container=True)
        el = self._state.alloc(snap)
        el.name = output_name
        for cid in eids:
            self._state.elements[cid].container_parent = el.eid
        return el.eid

    def create_auto_container_from_standard_with_reference(
        self,
        eids: list[ElementId],
        output_name: str,
        standard_element_name: str,
        reference_eid: ElementId,
    ) -> ElementId:
        # The reference only affects placement in real cadwork; for the
        # in-memory containment model it behaves like the plain variant.
        return self.create_auto_container_from_standard(
            eids, output_name, standard_element_name
        )

    def create_node(self, position: Point3D) -> ElementId:
        snap = ElementTypeSnapshot(is_node=True)
        el = self._state.alloc(snap)
        t = _tup(position)
        el.p1 = el.p2 = el.p3 = t
        return el.eid

    def create_line_points(self, axis: Segment) -> ElementId:
        snap = ElementTypeSnapshot(is_line=True)
        el = self._state.alloc(snap)
        t1, t2 = _tup(axis.p1), _tup(axis.p2)
        el.p1, el.p2 = t1, t2
        el.p3 = (t1[0], t1[1], t1[2] + 1.0)
        el.length = _distance(t1, t2)
        return el.eid

    def create_surface_points(self, points: list[Point3D]) -> ElementId:
        snap = ElementTypeSnapshot(is_surface=True)
        el = self._state.alloc(snap)
        el.surface_points = [_tup(p) for p in points]
        if points:
            el.p1 = _tup(points[0])
        return el.eid

    def create_standard_connector(self, axis: Segment, name: str) -> ElementId:
        snap = ElementTypeSnapshot(is_connector_axis=True, is_line=True, is_beam=True)
        el = self._state.alloc(snap)
        t1, t2 = _tup(axis.p1), _tup(axis.p2)
        el.p1, el.p2 = t1, t2
        el.p3 = (t1[0], t1[1], t1[2] + 1.0)
        el.length = _distance(t1, t2)
        el.name = name
        return el.eid

    def extrude_surface_to_auxiliary_vector(
        self, surface_eid: ElementId, vector: Point3D
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_auxiliary=True)
        el = self._state.alloc(snap)
        src = self._state.elements[surface_eid]
        el.p1 = src.p1
        el.length = math.sqrt(vector.x**2 + vector.y**2 + vector.z**2)
        return el.eid

    def delete_elements(self, eids: list[ElementId]) -> None:
        for eid in eids:
            self._state.elements.pop(eid, None)

    def element_exists(self, eid: ElementId) -> bool:
        return eid in self._state.elements

    # ---- type introspection ----

    def get_element_type(self, eid: ElementId) -> ElementTypeSnapshot:
        return self._state.elements[eid].snapshot

    # ---- container content ----

    def get_container_content_elements(self, eid: ElementId) -> list[ElementId]:
        return [
            cid
            for cid, el in self._state.elements.items()
            if el.container_parent == eid
        ]

    def get_parent_container_id(self, eid: ElementId) -> ElementId:
        return self._state.elements[eid].container_parent

    def set_container_contents(
        self, container_eid: ElementId, eids: list[ElementId]
    ) -> None:
        for el in self._state.elements.values():
            if el.container_parent == container_eid:
                el.container_parent = 0
        for cid in eids:
            self._state.elements[cid].container_parent = container_eid

    # ---- identifiable enumeration ----

    def get_all_identifiable_element_ids(self) -> list[ElementId]:
        return list(self._state.elements.keys())

    def get_active_identifiable_element_ids(self) -> list[ElementId]:
        # No selection state in the fake — same as "all".
        return list(self._state.elements.keys())

    # ---- ray casting ----

    def cast_ray(
        self, eids: list[ElementId], start: Point3D, end: Point3D, radius: float
    ) -> list[tuple[ElementId, list[PointTuple]]]:
        # Mirror the live call deterministically: intersect the segment against
        # each element's world-axis box (the same box get_element_vertices
        # reports), grown by ``radius`` on every axis.
        s, e = _tup(start), _tup(end)
        out: list[tuple[ElementId, list[PointTuple]]] = []
        for eid in eids:
            el = self._state.elements.get(eid)
            if el is None:
                continue
            x, y, z = el.p1
            box_min = (x - radius, y - radius, z - radius)
            box_max = (
                x + el.length + radius,
                y + el.width + radius,
                z + el.height + radius,
            )
            hits = _segment_aabb_hits(s, e, box_min, box_max)
            if hits:
                out.append((ElementId(eid), hits))
        return out


class FakeAttributesAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    # ---- name / grouping / comment ----

    def get_name(self, eid: ElementId) -> str:
        return self._state.elements[eid].name

    def set_name(self, eids: list[ElementId], name: str) -> None:
        for eid in eids:
            self._state.elements[eid].name = name

    def get_group(self, eid: ElementId) -> str:
        return self._state.elements[eid].group

    def set_group(self, eids: list[ElementId], group: str) -> None:
        for eid in eids:
            self._state.elements[eid].group = group

    def get_subgroup(self, eid: ElementId) -> str:
        return self._state.elements[eid].subgroup

    def set_subgroup(self, eids: list[ElementId], subgroup: str) -> None:
        for eid in eids:
            self._state.elements[eid].subgroup = subgroup

    def get_comment(self, eid: ElementId) -> str:
        return self._state.elements[eid].comment

    def set_comment(self, eids: list[ElementId], comment: str) -> None:
        for eid in eids:
            self._state.elements[eid].comment = comment

    # ---- element-module wall situation ----

    def get_wall_situation(self, eid: ElementId) -> str:
        return self._state.elements[eid].wall_situation

    def set_wall_situation(self, eids: list[ElementId], situation: str) -> None:
        """Test-only seed (cwapi3d has no setter; the calc writes the real one)."""
        for eid in eids:
            self._state.elements[eid].wall_situation = situation

    # ---- material / sku / numbers ----

    def get_material_name(self, eid: ElementId) -> str:
        return self._state.elements[eid].material

    def set_material_name(self, eids: list[ElementId], name: str) -> None:
        for eid in eids:
            self._state.elements[eid].material = name

    def get_sku(self, eid: ElementId) -> str:
        return self._state.elements[eid].sku

    def set_sku(self, eids: list[ElementId], sku: str) -> None:
        for eid in eids:
            self._state.elements[eid].sku = sku

    def get_production_number(self, eid: ElementId) -> int:
        return self._state.elements[eid].production_number

    def set_production_number(self, eids: list[ElementId], n: int) -> None:
        for eid in eids:
            self._state.elements[eid].production_number = n

    def get_part_number(self, eid: ElementId) -> str:
        return self._state.elements[eid].part_number

    def set_part_number(self, eids: list[ElementId], n: str) -> None:
        for eid in eids:
            self._state.elements[eid].part_number = n

    # ---- cadwork-issued identifiers ----

    def get_cadwork_guid(self, eid: ElementId) -> str:
        return self._state.elements[eid].cadwork_guid

    # ---- free-form metadata ----

    def get_additional_data(self, eid: ElementId) -> str:
        return self._state.elements[eid].additional_data

    def set_additional_data(self, eids: list[ElementId], data: str) -> None:
        for eid in eids:
            self._state.elements[eid].additional_data = data

    def get_assembly_number(self, eid: ElementId) -> str:
        return self._state.elements[eid].assembly_number

    def set_assembly_number(self, eids: list[ElementId], n: str) -> None:
        for eid in eids:
            self._state.elements[eid].assembly_number = n

    # ---- indexed user attributes ----

    def get_user_attribute(self, eid: ElementId, index: int) -> str:
        return self._state.elements[eid].user_attributes.get(index, "")

    def set_user_attribute(self, eids: list[ElementId], index: int, value: str) -> None:
        for eid in eids:
            self._state.elements[eid].user_attributes[index] = value

    # ---- cover-object flags ----

    def set_cover_kind(self, eids: list[ElementId], kind: CoverKind) -> None:
        for eid in eids:
            self._state.elements[eid].snapshot = replace(
                self._state.elements[eid].snapshot,
                is_wall=kind
                in {CoverKind.FRAMED_WALL, CoverKind.SOLID_WALL, CoverKind.LOG_WALL},
                is_floor=kind in {CoverKind.FRAMED_FLOOR, CoverKind.SOLID_FLOOR},
                is_roof=kind in {CoverKind.FRAMED_ROOF, CoverKind.SOLID_ROOF},
                is_framed_wall=kind is CoverKind.FRAMED_WALL,
                is_solid_wall=kind is CoverKind.SOLID_WALL,
                is_log_wall=kind is CoverKind.LOG_WALL,
                is_framed_floor=kind is CoverKind.FRAMED_FLOOR,
                is_solid_floor=kind is CoverKind.SOLID_FLOOR,
                is_framed_roof=kind is CoverKind.FRAMED_ROOF,
                is_solid_roof=kind is CoverKind.SOLID_ROOF,
            )

    def set_opening(self, eids: list[ElementId]) -> None:
        for eid in eids:
            self._state.elements[eid].snapshot = replace(
                self._state.elements[eid].snapshot,
                is_opening=True,
            )


class FakeGeometryAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    def get_p1(self, eid: ElementId) -> PointTuple:
        return self._state.elements[eid].p1

    def get_p2(self, eid: ElementId) -> PointTuple:
        return self._state.elements[eid].p2

    def get_p3(self, eid: ElementId) -> PointTuple:
        return self._state.elements[eid].p3

    def get_xl(self, eid: ElementId) -> PointTuple:
        return self._state.elements[eid].xl

    def get_yl(self, eid: ElementId) -> PointTuple:
        return self._state.elements[eid].yl

    def get_zl(self, eid: ElementId) -> PointTuple:
        return self._state.elements[eid].zl

    def get_length(self, eid: ElementId) -> float:
        return self._state.elements[eid].length

    def get_width(self, eid: ElementId) -> float:
        return self._state.elements[eid].width

    def get_height(self, eid: ElementId) -> float:
        return self._state.elements[eid].height

    def set_width(self, eids: list[ElementId], width: float) -> None:
        for eid in eids:
            self._state.elements[eid].width = width

    def set_height(self, eids: list[ElementId], height: float) -> None:
        for eid in eids:
            self._state.elements[eid].height = height

    def set_length(self, eids: list[ElementId], length: float) -> None:
        for eid in eids:
            self._state.elements[eid].length = length

    def get_volume(self, eid: ElementId) -> float:
        return self._state.elements[eid].volume

    def get_weight(self, eid: ElementId) -> float:
        return self._state.elements[eid].weight

    def get_center_of_gravity(self, eid: ElementId) -> PointTuple:
        el = self._state.elements[eid]
        return (
            0.5 * (el.p1[0] + el.p2[0]),
            0.5 * (el.p1[1] + el.p2[1]),
            0.5 * (el.p1[2] + el.p2[2]),
        )

    def get_element_vertices(self, eid: ElementId) -> list[PointTuple]:
        # Mirrors cwapi3d: a plain list of point tuples, not a vertex_list.
        el = self._state.elements[eid]
        x, y, z = el.p1
        L, W, H = el.length, el.width, el.height
        return [
            (x, y, z),
            (x + L, y, z),
            (x + L, y + W, z),
            (x, y + W, z),
            (x, y, z + H),
            (x + L, y, z + H),
            (x + L, y + W, z + H),
            (x, y + W, z + H),
        ]

    def get_element_facets(self, eid: ElementId) -> FacetListLike:
        return _FakeFacetList()


class FakeGroupingAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    def get_element_grouping_type(self) -> GroupingMode:
        return self._state.grouping_mode

    def set_element_grouping_type(self, mode: GroupingMode) -> None:
        self._state.grouping_mode = mode

    def filter_elements_by_group(self, group: str) -> list[ElementId]:
        if not group:
            return []
        return [eid for eid, el in self._state.elements.items() if el.group == group]

    def filter_elements_by_subgroup(self, subgroup: str) -> list[ElementId]:
        if not subgroup:
            return []
        return [
            eid for eid, el in self._state.elements.items() if el.subgroup == subgroup
        ]


class FakeDisplayAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    def disable_auto_display_refresh(self) -> None:
        self._state.display_refresh_disable_calls += 1

    def enable_auto_display_refresh(self) -> None:
        self._state.display_refresh_enable_calls += 1

    def recreate_elements(self, eids: list[ElementId]) -> None:
        self._state.recreate_calls.append(list(eids))


class FakeVisualizationAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    def get_color(self, eid: ElementId) -> int:
        return self._state.elements[eid].color

    def set_color(self, eids: list[ElementId], color_id: int) -> None:
        for eid in eids:
            self._state.elements[eid].color = color_id


class FakeProjectAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    # ---- identity ----

    def get_project_guid(self) -> str:
        return self._state.project_guid

    def create_new_guid(self) -> str:
        guid = f"fake-new-guid-{self._state._next_project_guid:08d}"
        self._state._next_project_guid += 1
        return guid

    def get_3d_file_name(self) -> str:
        return self._state.file_name_3dc

    # ---- metadata (str) ----

    def get_project_name(self) -> str:
        return self._state.project_name

    def set_project_name(self, value: str) -> None:
        self._state.project_name = value

    def get_project_number(self) -> str:
        return self._state.project_number

    def set_project_number(self, value: str) -> None:
        self._state.project_number = value

    def get_project_part(self) -> str:
        return self._state.project_part

    def set_project_part(self, value: str) -> None:
        self._state.project_part = value

    def get_project_architect(self) -> str:
        return self._state.project_architect

    def set_project_architect(self, value: str) -> None:
        self._state.project_architect = value

    def get_project_customer(self) -> str:
        return self._state.project_customer

    def set_project_customer(self, value: str) -> None:
        self._state.project_customer = value

    def get_project_designer(self) -> str:
        return self._state.project_designer

    def set_project_designer(self, value: str) -> None:
        self._state.project_designer = value

    def get_project_deadline(self) -> str:
        return self._state.project_deadline

    def set_project_deadline(self, value: str) -> None:
        self._state.project_deadline = value

    def get_project_description(self) -> str:
        return self._state.project_description

    def set_project_description(self, value: str) -> None:
        self._state.project_description = value

    # ---- address ----

    def get_project_address(self) -> str:
        return self._state.project_address

    def set_project_address(self, value: str) -> None:
        self._state.project_address = value

    def get_project_postal_code(self) -> str:
        return self._state.project_postal_code

    def set_project_postal_code(self, value: str) -> None:
        self._state.project_postal_code = value

    def get_project_city(self) -> str:
        return self._state.project_city

    def set_project_city(self, value: str) -> None:
        self._state.project_city = value

    def get_project_country(self) -> str:
        return self._state.project_country

    def set_project_country(self, value: str) -> None:
        self._state.project_country = value

    # ---- geo-location (float) ----

    def get_project_latitude(self) -> float:
        return self._state.project_latitude

    def set_project_latitude(self, value: float) -> None:
        self._state.project_latitude = value

    def get_project_longitude(self) -> float:
        return self._state.project_longitude

    def set_project_longitude(self, value: float) -> None:
        self._state.project_longitude = value

    def get_project_elevation(self) -> float:
        return self._state.project_elevation

    def set_project_elevation(self, value: float) -> None:
        self._state.project_elevation = value

    # ---- indexed user attributes ----

    def get_project_user_attribute(self, number: int) -> str:
        return self._state.project_user_attributes.get(number, "")

    def set_project_user_attribute(self, number: int, value: str) -> None:
        self._state.project_user_attributes[number] = value

    def get_project_user_attribute_name(self, number: int) -> str:
        return self._state.project_user_attribute_names.get(number, "")

    def set_project_user_attribute_name(self, number: int, value: str) -> None:
        self._state.project_user_attribute_names[number] = value

    # ---- project-data key/value store ----

    def get_project_data(self, key: str) -> str:
        return self._state.project_data.get(key, "")

    def set_project_data(self, key: str, data: str) -> None:
        self._state.project_data[key] = data

    def delete_project_data(self, key: str) -> None:
        self._state.project_data.pop(key, None)

    def get_project_data_keys(self) -> list[str]:
        return list(self._state.project_data.keys())


class FakeMaterialAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    def _ensure(self, name: str) -> MaterialId:
        """Resolve ``name`` to an id, registering a default material if unseen.

        Mirrors the live catalog: assigning a material by name (via
        ``set_material_name``) makes that name resolvable here, so a pull can
        read it back. Tests wanting real structural data seed it with
        :meth:`register` first.
        """
        ids = self._state.material_id_by_name
        if name not in ids:
            mid = MaterialId(self._state._next_material_id)
            self._state._next_material_id += 1
            ids[name] = mid
            self._state.material_by_id[mid] = MaterialSnapshot(name=name)
        return ids[name]

    def register(self, snapshot: MaterialSnapshot) -> MaterialId:
        """Test helper: add (or replace) a material with full properties."""
        mid = self._ensure(snapshot.name)
        self._state.material_by_id[mid] = snapshot
        return mid

    def get_material_id(self, name: str) -> MaterialId:
        return self._ensure(name)

    def get_all_material_ids(self) -> list[MaterialId]:
        return list(self._state.material_by_id.keys())

    def get_material(self, material_id: MaterialId) -> MaterialSnapshot:
        return self._state.material_by_id[material_id]


class FakeOperationsAdapter:
    """Recording fake: remembers every call, fabricates results from seeded state."""

    def __init__(self, state: FakeState) -> None:
        self._state = state

    # ---- boolean solids ----

    def solder_elements(self, eids: list[ElementId]) -> list[ElementId]:
        self._state.solder_calls.append(list(eids))
        first, *rest = eids
        for eid in rest:
            self._state.elements.pop(eid, None)
        return [first]

    def _subtract(
        self,
        hard_eids: list[ElementId],
        soft_eids: list[ElementId],
        with_undo: bool,
    ) -> list[ElementId]:
        self._state.subtract_calls.append((list(hard_eids), list(soft_eids), with_undo))
        pieces = list(self._state.pending_subtract_pieces)
        self._state.pending_subtract_pieces.clear()
        return pieces

    def subtract_elements(
        self, hard_eids: list[ElementId], soft_eids: list[ElementId]
    ) -> list[ElementId]:
        return self._subtract(hard_eids, soft_eids, False)

    def subtract_elements_with_undo(
        self,
        hard_eids: list[ElementId],
        soft_eids: list[ElementId],
        with_undo: bool,
    ) -> list[ElementId]:
        return self._subtract(hard_eids, soft_eids, with_undo)

    def split_elements(self, eids: list[ElementId]) -> None:
        self._state.split_calls.append(list(eids))

    # ---- plane / miter / overmeasure cuts ----

    def _record_plane(self, eid: ElementId, plane: Plane3D) -> None:
        normal = (plane.normal.x, plane.normal.y, plane.normal.z)
        self._state.plane_cut_calls.append((eid, normal, -plane.d()))

    def cut_element_with_plane(self, eid: ElementId, plane: Plane3D) -> bool:
        self._record_plane(eid, plane)
        return eid in self._state.elements

    def slice_element_with_plane_get_new(
        self, eid: ElementId, plane: Plane3D
    ) -> list[ElementId]:
        self._record_plane(eid, plane)
        el = self._state.alloc(self._state.elements[eid].snapshot)
        return [el.eid]

    def cut_elements_with_miter(
        self, first_eid: ElementId, second_eid: ElementId
    ) -> bool:
        self._state.miter_calls.append((first_eid, second_eid))
        return True

    def cut_elements_with_overmeasure(
        self, hard_eids: list[ElementId], soft_eids: list[ElementId]
    ) -> None:
        self._state.overmeasure_calls.append((list(hard_eids), list(soft_eids)))

    def cut_element_with_processing_group(
        self, soft_eid: ElementId, processing_eid: ElementId
    ) -> None:
        self._state.processing_group_calls.append((soft_eid, processing_eid))

    # ---- process management ----

    def delete_processes_keep_cutting_bodies(
        self, eids: list[ElementId], keep_cutting_elements_only: bool
    ) -> list[ElementId]:
        self._state.keep_cutting_bodies_calls.append(
            (list(eids), keep_cutting_elements_only)
        )
        out: list[ElementId] = []
        for eid in eids:
            count = self._state.pending_cutting_bodies.pop(eid, 0)
            for _ in range(count):
                el = self._state.alloc(ElementTypeSnapshot(is_auxiliary=True))
                out.append(el.eid)
        return out

    def delete_all_element_processes(self, eids: list[ElementId]) -> None:
        self._state.delete_processes_calls.append(list(eids))

    def delete_all_element_end_types(self, eids: list[ElementId]) -> None:
        self._state.delete_end_types_calls.append(list(eids))


class FakeModuleAdapter:
    """Records element-module calls; stores the mirror ModuleProperties as-is."""

    def __init__(self, state: FakeState) -> None:
        self._state = state

    def apply_properties(
        self, eids: list[ElementId], properties: "ModuleProperties"
    ) -> None:
        self._state.module_applied.append((list(eids), properties))
        for eid in eids:
            self._state.module_properties[eid] = properties

    def get_properties(self, eid: ElementId) -> "ModuleProperties":
        from pycadwork.detail.properties import ModuleProperties

        return self._state.module_properties.get(eid, ModuleProperties())

    def start_calculation(self, cover_eids: list[ElementId]) -> None:
        self._state.module_calculation_calls.append(list(cover_eids))

    def start_calculation_silently(self, cover_eids: list[ElementId]) -> None:
        self._state.module_silent_calculation_calls.append(list(cover_eids))

    def set_detail_path(self, path: str) -> None:
        self._state.module_detail_path = path

    # ---- module situations ----

    def set_parts_situation(
        self,
        cover: ElementId,
        add_children: list[ElementId],
        remove_children: list[ElementId] = (),
    ) -> None:
        self._state.module_parts_situation.append(
            (cover, list(add_children), list(remove_children))
        )

    def set_rough_volume_situation(
        self,
        cover: ElementId,
        add_partners: list[ElementId],
        remove_partners: list[ElementId] = (),
    ) -> None:
        self._state.module_rough_volume_situation.append(
            (cover, list(add_partners), list(remove_partners))
        )

    def auto_set_parts_situation(self, eids: list[ElementId]) -> None:
        self._state.module_auto_parts_situation.append(list(eids))

    def auto_set_rough_volume_situation(self, eids: list[ElementId]) -> None:
        self._state.module_auto_rough_volume_situation.append(list(eids))

    def activate_parts_without_situation(self) -> list[ElementId]:
        return []

    def activate_rv_without_situation(self) -> list[ElementId]:
        return []


class FakeBimAdapter:
    def __init__(self, state: FakeState) -> None:
        self._state = state

    # ---- per-element assignment ----

    def get_building(self, eid: ElementId) -> str:
        return self._state.elements[eid].building

    def get_storey(self, eid: ElementId) -> str:
        return self._state.elements[eid].storey

    def set_building_and_storey(
        self, eids: list[ElementId], building: str, storey: str
    ) -> None:
        for eid in eids:
            el = self._state.elements[eid]
            el.building = building
            el.storey = storey

    # ---- registry enumeration ----

    def get_all_buildings(self) -> list[str]:
        return list(self._state.storeys.keys())

    def get_all_storeys(self, building: str) -> list[str]:
        # Deterministic: sorted ascending by elevation.
        registry = self._state.storeys.get(building, {})
        return sorted(registry, key=lambda name: registry[name])

    # ---- storey elevation ----

    def get_storey_height(self, building: str, storey: str) -> float:
        return self._state.storeys[building][storey]

    def set_storey_height(self, building: str, storey: str, height: float) -> None:
        self._state.storeys.setdefault(building, {})[storey] = height


# ---- facade ----


class FakeCadworkAdapter:
    """Same shape as :class:`CadworkAdapter` — duck-typed, no Protocol needed."""

    __slots__ = (
        "state",
        "elements",
        "attributes",
        "geometry",
        "grouping",
        "display",
        "project",
        "bim",
        "material",
        "operations",
        "module",
        "visualization",
    )

    def __init__(self) -> None:
        self.state: FakeState = FakeState()
        self.elements = FakeElementsAdapter(self.state)
        self.attributes = FakeAttributesAdapter(self.state)
        self.geometry = FakeGeometryAdapter(self.state)
        self.grouping = FakeGroupingAdapter(self.state)
        self.display = FakeDisplayAdapter(self.state)
        self.project = FakeProjectAdapter(self.state)
        self.bim = FakeBimAdapter(self.state)
        self.material = FakeMaterialAdapter(self.state)
        self.operations = FakeOperationsAdapter(self.state)
        self.module = FakeModuleAdapter(self.state)
        self.visualization = FakeVisualizationAdapter(self.state)
