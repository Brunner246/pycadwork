"""Records — the lingua franca between the model and the SQL store.

Each record is a frozen, slotted DTO that mirrors exactly one row of one table
in the normalized schema (see :mod:`pycadwork.persistence.schema`). Both sides
of the sync speak records: gateways map records ↔ rows, mappers map records ↔
domain objects. Keeping the field order identical to the table's column order
lets the generic :class:`~pycadwork.persistence.gateways.TableDataGateway`
serialize a record with a single positional pass.

Records carry only SQL-native values (``str`` / ``int`` / ``float`` / ``None``,
plus ``bool`` for the one storey-spanning flag). They never reference cadwork
ids as live objects — an id is just an ``int``.

:class:`ModelSnapshot` bundles every record for one project into a single,
diff-able aggregate. It is the value :meth:`ModelReader.read` returns and the
value a SQL ``load_snapshot`` reconstructs; the diff keys it by
``(project_guid, element_id)``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from pycadwork.persistence._ids import (
    CadworkGuid,
    ContainerId,
    ElementId,
    MemberId,
    ProjectGuid,
)


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """One row of ``project`` — the active project's metadata (from ``ProjectInfo``)."""

    project_guid: ProjectGuid
    name: str = ""
    number: str = ""
    part: str = ""
    architect: str = ""
    customer: str = ""
    designer: str = ""
    deadline: str = ""
    description: str = ""
    address: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    elevation: float = 0.0


@dataclass(frozen=True, slots=True)
class ElementRecord:
    """One row of ``element`` — identity, resolved type token, container parent.

    ``element_type`` is the lowercase wrapper-class token (``beam``, ``plate``,
    ``wall``, ``container``, …) produced by resolving the element through the
    same registry path :func:`pycadwork.element.from_id` uses.
    ``parent_container_id`` is ``None`` when the element has no container owner.
    """

    project_guid: ProjectGuid
    id: ElementId
    element_type: str
    cadwork_guid: CadworkGuid = CadworkGuid("")
    parent_container_id: ContainerId | None = None


@dataclass(frozen=True, slots=True)
class AttributeRecord:
    """One row of ``attribute`` — the 1:1 satellite of mutable element attributes.

    ``additional_data`` is intentionally absent: in cwapi3d it is a per-element
    *keyed* key/value store, not a single scalar, so it cannot be one column on
    this satellite (it would be its own 1:M table, once the adapter exposes key
    enumeration).
    """

    project_guid: ProjectGuid
    element_id: ElementId
    name: str = ""
    group_name: str = ""
    subgroup: str = ""
    comment: str = ""
    material_name: str = ""
    sku: str = ""
    production_number: int = 0
    part_number: str = ""
    assembly_number: str = ""


@dataclass(frozen=True, slots=True)
class GeometryRecord:
    """One row of ``geometry`` — the 1:1 satellite of scalar geometry.

    Holds the three axis points, the dimension scalars, the bulk values
    (volume / weight / centre-of-gravity), and the axis-aligned bounding box.
    No mesh or B-rep — that is out of scope by design.
    """

    project_guid: ProjectGuid
    element_id: ElementId
    p1x: float = 0.0
    p1y: float = 0.0
    p1z: float = 0.0
    p2x: float = 0.0
    p2y: float = 0.0
    p2z: float = 0.0
    p3x: float = 0.0
    p3y: float = 0.0
    p3z: float = 0.0
    length: float = 0.0
    width: float = 0.0
    height: float = 0.0
    volume: float = 0.0
    weight: float = 0.0
    cog_x: float = 0.0
    cog_y: float = 0.0
    cog_z: float = 0.0
    aabb_min_x: float = 0.0
    aabb_min_y: float = 0.0
    aabb_min_z: float = 0.0
    aabb_max_x: float = 0.0
    aabb_max_y: float = 0.0
    aabb_max_z: float = 0.0


@dataclass(frozen=True, slots=True)
class UserAttributeRecord:
    """One row of ``user_attribute`` — one indexed user attribute (1:M per element)."""

    project_guid: ProjectGuid
    element_id: ElementId
    attr_index: int
    value: str = ""


@dataclass(frozen=True, slots=True)
class CoverRecord:
    """One row of ``cover`` — the cover-kind flag of a wall/slab/roof parent."""

    project_guid: ProjectGuid
    element_id: ElementId
    cover_kind: str


@dataclass(frozen=True, slots=True)
class ContainerMemberRecord:
    """One row of ``container_member`` — a real parent/child containment link."""

    project_guid: ProjectGuid
    container_id: ContainerId
    member_id: MemberId


@dataclass(frozen=True, slots=True)
class BuildingRecord:
    """One row of ``building`` — a BMT building name."""

    project_guid: ProjectGuid
    name: str


@dataclass(frozen=True, slots=True)
class StoreyRecord:
    """One row of ``storey`` — a storey under a building, with its base elevation."""

    project_guid: ProjectGuid
    building_name: str
    name: str
    elevation: float = 0.0


@dataclass(frozen=True, slots=True)
class StoreyAssignmentRecord:
    """One row of ``storey_assignment`` — an element's (building, storey) pair.

    ``spans`` records whether the element straddled a storey plane; the live
    model has no channel for it, so it is ``False`` on a model read and only
    meaningful when seeded into the store directly.
    """

    project_guid: ProjectGuid
    element_id: ElementId
    building_name: str
    storey_name: str
    spans: bool = False


@dataclass(frozen=True, slots=True)
class MaterialRecord:
    """One row of ``material`` — the deduplicated master of one material.

    Keyed by ``(project_guid, material_name)``: a material is stored once per
    project regardless of how many elements carry it. Holds the structural +
    identity subset read from cadwork's material catalog; thermal / fire /
    commercial / texture properties are out of scope.
    """

    project_guid: ProjectGuid
    material_name: str
    group_name: str = ""
    code: str = ""
    grade: str = ""
    quality: str = ""
    modulus_elasticity_1: float = 0.0
    modulus_elasticity_2: float = 0.0
    modulus_elasticity_3: float = 0.0
    shear_modulus_1: float = 0.0
    shear_modulus_2: float = 0.0
    weight: float = 0.0


@dataclass(frozen=True, slots=True)
class ElementMaterialRecord:
    """One row of ``element_material`` — the link from an element to its material.

    Carries the element's id *and* its cadwork GUID (the element-reference the
    table is built around) and the ``material_name`` joining to the
    :class:`MaterialRecord` master. Emitted only for elements that actually carry
    a material, so every link points at a real master row.
    """

    project_guid: ProjectGuid
    element_id: ElementId
    cadwork_guid: CadworkGuid = CadworkGuid("")
    material_name: str = ""


@dataclass(frozen=True, slots=True)
class ModelSnapshot:
    """Every record for one project, bundled for diffing and transfer.

    Both directions of the sync produce a snapshot — :meth:`ModelReader.read`
    from the live model, ``load_snapshot`` from the SQL store — so the diff is a
    pure comparison of two snapshots. The ``*_by_*`` helpers index the satellite
    records by element id for the writer; they rebuild on each call (the snapshot
    is immutable, so there is nothing to cache against).
    """

    project: ProjectRecord
    elements: tuple[ElementRecord, ...] = ()
    attributes: tuple[AttributeRecord, ...] = ()
    geometries: tuple[GeometryRecord, ...] = ()
    user_attributes: tuple[UserAttributeRecord, ...] = ()
    covers: tuple[CoverRecord, ...] = ()
    container_members: tuple[ContainerMemberRecord, ...] = ()
    buildings: tuple[BuildingRecord, ...] = ()
    storeys: tuple[StoreyRecord, ...] = ()
    storey_assignments: tuple[StoreyAssignmentRecord, ...] = field(default=())
    materials: tuple[MaterialRecord, ...] = ()
    element_materials: tuple[ElementMaterialRecord, ...] = ()

    # ---- per-element indexes (for the writer) ----

    def attributes_by_element(self) -> dict[ElementId, AttributeRecord]:
        return {a.element_id: a for a in self.attributes}

    def geometry_by_element(self) -> dict[ElementId, GeometryRecord]:
        return {g.element_id: g for g in self.geometries}

    def covers_by_element(self) -> dict[ElementId, CoverRecord]:
        return {c.element_id: c for c in self.covers}

    def assignments_by_element(self) -> dict[ElementId, StoreyAssignmentRecord]:
        return {s.element_id: s for s in self.storey_assignments}

    def user_attributes_by_element(self) -> dict[ElementId, list[UserAttributeRecord]]:
        out: dict[ElementId, list[UserAttributeRecord]] = {}
        for ua in self.user_attributes:
            out.setdefault(ua.element_id, []).append(ua)
        return out

    def members_by_container(self) -> dict[ContainerId, list[MemberId]]:
        out: dict[ContainerId, list[MemberId]] = {}
        for m in self.container_members:
            out.setdefault(m.container_id, []).append(m.member_id)
        return out

    def materials_by_name(self) -> dict[str, MaterialRecord]:
        return {m.material_name: m for m in self.materials}

    def element_materials_by_element(self) -> dict[ElementId, ElementMaterialRecord]:
        return {em.element_id: em for em in self.element_materials}

    # ---- flat, dependency-ordered iteration (for the unit of work) ----

    def all_records(self) -> Iterator[object]:
        """Yield every record in foreign-key-safe insertion order.

        Parents precede children: ``project`` and ``building`` first, then
        ``storey``, the ``material`` master, and ``element``, then every
        element/storey satellite — with ``element_material`` last, since its link
        rows reference both ``element`` and ``material``. A
        :class:`~pycadwork.persistence.unit_of_work.UnitOfWork` that upserts in
        this order never trips an immediate FK check.
        """
        yield self.project
        yield from self.buildings
        yield from self.storeys
        yield from self.materials
        yield from self.elements
        yield from self.attributes
        yield from self.geometries
        yield from self.user_attributes
        yield from self.covers
        yield from self.container_members
        yield from self.storey_assignments
        yield from self.element_materials
