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

from pycadwork.cadwork_adapter.types import (
    CoverKind,
    ElementId,
    ElementTypeSnapshot,
    FacetListLike,
    GroupingMode,
    PointTuple,
)
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.specs import (
    AxisFrame,
    AxisPoints,
    PanelSection,
    RectSection,
    Segment,
)


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
    comment: str = ""
    material: str = ""
    sku: str = ""
    production_number: int = 0
    part_number: str = ""
    cadwork_guid: str = ""
    additional_data: str = ""
    assembly_number: str = ""
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
    _next_id: ElementId = 1
    _next_guid: int = 1
    # behavioural observables — kept (small, exercised by display tests)
    display_refresh_disable_calls: int = 0
    display_refresh_enable_calls: int = 0
    recreate_calls: list[list[ElementId]] = field(default_factory=list)

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

    def create_square_beam_points(
        self, width: float, axis: AxisPoints
    ) -> ElementId:
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

    def create_drilling_points(
        self, diameter: float, axis: Segment
    ) -> ElementId:
        snap = ElementTypeSnapshot(is_drilling=True)
        el = self._state.alloc(snap)
        t1, t2 = _tup(axis.p1), _tup(axis.p2)
        el.p1, el.p2 = t1, t2
        el.p3 = (t1[0], t1[1], t1[2] + 1.0)
        el.length = _distance(t1, t2)
        el.width = el.height = diameter
        return el.eid

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

    def create_standard_connector(
        self, axis: Segment, name: str
    ) -> ElementId:
        snap = ElementTypeSnapshot(
            is_connector_axis=True, is_line=True, is_beam=True
        )
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
        el.length = math.sqrt(vector.x ** 2 + vector.y ** 2 + vector.z ** 2)
        return el.eid

    def delete_elements(self, eids: list[ElementId]) -> None:
        for eid in eids:
            self._state.elements.pop(eid, None)

    # ---- type introspection ----

    def get_element_type(self, eid: ElementId) -> ElementTypeSnapshot:
        return self._state.elements[eid].snapshot

    # ---- identifiable enumeration ----

    def get_all_identifiable_element_ids(self) -> list[ElementId]:
        return list(self._state.elements.keys())

    def get_active_identifiable_element_ids(self) -> list[ElementId]:
        # No selection state in the fake — same as "all".
        return list(self._state.elements.keys())


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

    def set_user_attribute(
        self, eids: list[ElementId], index: int, value: str
    ) -> None:
        for eid in eids:
            self._state.elements[eid].user_attributes[index] = value

    # ---- cover-object flags ----

    def set_cover_kind(self, eids: list[ElementId], kind: CoverKind) -> None:
        for eid in eids:
            self._state.elements[eid].snapshot = replace(
                self._state.elements[eid].snapshot,
                is_wall=kind in {CoverKind.FRAMED_WALL, CoverKind.SOLID_WALL, CoverKind.LOG_WALL},
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
        return [
            eid for eid, el in self._state.elements.items() if el.group == group
        ]

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


# ---- facade ----


class FakeCadworkAdapter:
    """Same shape as :class:`CadworkAdapter` — duck-typed, no Protocol needed."""

    __slots__ = ("state", "elements", "attributes", "geometry", "grouping", "display")

    def __init__(self) -> None:
        self.state: FakeState = FakeState()
        self.elements = FakeElementsAdapter(self.state)
        self.attributes = FakeAttributesAdapter(self.state)
        self.geometry = FakeGeometryAdapter(self.state)
        self.grouping = FakeGroupingAdapter(self.state)
        self.display = FakeDisplayAdapter(self.state)
