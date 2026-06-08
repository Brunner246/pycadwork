"""ModelReader / ModelWriter — the cadwork seam for persistence.

These two classes are the *only* persistence code that touches the model. Read
goes through :class:`~pycadwork.document.Document` / ``Element`` and the
``cadwork`` adapter; write goes through the element ``create_*`` classmethods
and the adapter's attribute / geometry / bim setters. Nothing here imports
cwapi3d — the version-isolation seam stays single (see ``tests/test_isolation``).

* :class:`ModelReader` projects the live model into a :class:`ModelSnapshot`:
  one element record per element (typed via the registry), its attribute and
  geometry satellites, any indexed user attributes, the cover-kind flag for
  aggregates, container links, the BMT building/storey registry, and each
  element's storey assignment.

* :class:`ModelWriter` applies a :class:`SnapshotDiff` back: it *creates* the
  reconstructable missing elements, *updates* the existing ones (mutable attrs,
  dims, cover kind, grouping, building/storey, container membership), and
  *deletes* the removed ones. Two facts shape it (see the plan's edge cases):

  1. **Id remapping.** cadwork assigns fresh ids on ``create_*``, so a created
     element's new id ≠ its stored id. The writer threads a ``stored → model``
     id map through every dependent write (container membership, storey links).
     Existing elements map to themselves.
  2. **No point setter, no model rollback.** Existing elements' *axes* are never
     moved (only their dims/attrs/grouping/bim update — the adapter has no point
     setter, by decision). The write is best-effort under display suppression;
     a non-reconstructable type (no ``create_*`` path) is skipped with a warning,
     mirroring ``from_id``'s bare-``Element`` fallback.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, PointTuple
from pycadwork.document import Document
from pycadwork.element import (
    Beam,
    CircularMep,
    Drilling,
    Line,
    Node,
    Opening,
    Plate,
    RectangularMep,
)
from pycadwork.element.cover import Aggregate
from pycadwork.geometry import (
    AxisPoints,
    PanelSection,
    Point3D,
    RectSection,
    Segment,
)
from pycadwork.utility import suppressed_display
from pycadwork.persistence._diff import SnapshotDiff
from pycadwork.persistence._ids import (
    CadworkGuid,
    ContainerId,
    ElementId,
    MemberId,
    ProjectGuid,
)
from pycadwork.persistence.records import (
    AttributeRecord,
    BuildingRecord,
    ContainerMemberRecord,
    CoverRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
    UserAttributeRecord,
)

# Indexed user attributes have no "list all" API at the seam, so the reader
# probes a fixed range of slots and keeps the non-empty ones. Slots beyond this
# are not captured — a documented, deliberate bound rather than silent loss.
USER_ATTRIBUTE_SCAN_RANGE = range(1, 11)


def _aabb(vertices: Sequence[PointTuple]) -> tuple[float, ...]:
    """Reduce an element's vertices to ``(min_x, min_y, min_z, max_x, ...)``."""
    if not vertices:
        return (0.0,) * 6
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


class ModelReader:
    """Project the live cadwork model into a :class:`ModelSnapshot`."""

    def read(self) -> ModelSnapshot:
        """Read the whole active model into records.

        Geometry scalars are read straight from the geometry adapter rather than
        through each element's typed ``geometry`` component: that is uniform
        across every element type and sidesteps the deliberate ``AttributeError``
        a circular MEP's ``width`` / ``height`` raise on the domain wrapper.
        """
        document = Document()
        guid = ProjectGuid(document.guid)

        elements: list[ElementRecord] = []
        attributes: list[AttributeRecord] = []
        geometries: list[GeometryRecord] = []
        user_attributes: list[UserAttributeRecord] = []
        covers: list[CoverRecord] = []
        container_members: list[ContainerMemberRecord] = []
        assignments: list[StoreyAssignmentRecord] = []

        for element in document.elements():
            eid = ElementId(element.id)
            parent = cadwork.elements.get_parent_container_id(eid)
            parent_id = ContainerId(parent) if parent and parent > 0 else None

            elements.append(
                ElementRecord(
                    project_guid=guid,
                    id=eid,
                    element_type=type(element).__name__.lower(),
                    cadwork_guid=CadworkGuid(element.attrs.cadwork_guid),
                    parent_container_id=parent_id,
                )
            )
            attributes.append(self._attribute_record(guid, element))
            geometries.append(self._geometry_record(guid, eid))
            user_attributes.extend(self._user_attribute_records(guid, element))

            if isinstance(element, Aggregate):
                covers.append(CoverRecord(guid, eid, element.kind.value))

            if parent_id is not None:
                container_members.append(
                    ContainerMemberRecord(guid, parent_id, MemberId(eid))
                )

            assignment = self._assignment_record(guid, eid)
            if assignment is not None:
                assignments.append(assignment)

        buildings, storeys = self._building_storey_records(guid, assignments)

        return ModelSnapshot(
            project=self._project_record(guid, document),
            elements=tuple(elements),
            attributes=tuple(attributes),
            geometries=tuple(geometries),
            user_attributes=tuple(user_attributes),
            covers=tuple(covers),
            container_members=tuple(container_members),
            buildings=tuple(buildings),
            storeys=tuple(storeys),
            storey_assignments=tuple(assignments),
        )

    # ---- per-record readers ----

    @staticmethod
    def _project_record(guid: ProjectGuid, document: Document) -> ProjectRecord:
        p = document.project
        return ProjectRecord(
            project_guid=guid,
            name=p.name,
            number=p.number,
            part=p.part,
            architect=p.architect,
            customer=p.customer,
            designer=p.designer,
            deadline=p.deadline,
            description=p.description,
            address=p.address,
            postal_code=p.postal_code,
            city=p.city,
            country=p.country,
            latitude=p.latitude,
            longitude=p.longitude,
            elevation=p.elevation,
        )

    @staticmethod
    def _attribute_record(guid: ProjectGuid, element) -> AttributeRecord:
        a = element.attrs
        return AttributeRecord(
            project_guid=guid,
            element_id=ElementId(element.id),
            name=a.name,
            group_name=a.group,
            subgroup=a.subgroup,
            comment=a.comment,
            material_name=a.material_name,
            sku=a.sku,
            production_number=a.production_number,
            part_number=a.part_number,
            assembly_number=a.assembly_number,
        )

    @staticmethod
    def _geometry_record(guid: ProjectGuid, eid: ElementId) -> GeometryRecord:
        g = cadwork.geometry
        p1, p2, p3 = g.get_p1(eid), g.get_p2(eid), g.get_p3(eid)
        cog = g.get_center_of_gravity(eid)
        box = _aabb(g.get_element_vertices(eid))
        return GeometryRecord(
            project_guid=guid,
            element_id=eid,
            p1x=p1[0],
            p1y=p1[1],
            p1z=p1[2],
            p2x=p2[0],
            p2y=p2[1],
            p2z=p2[2],
            p3x=p3[0],
            p3y=p3[1],
            p3z=p3[2],
            length=g.get_length(eid),
            width=g.get_width(eid),
            height=g.get_height(eid),
            volume=g.get_volume(eid),
            weight=g.get_weight(eid),
            cog_x=cog[0],
            cog_y=cog[1],
            cog_z=cog[2],
            aabb_min_x=box[0],
            aabb_min_y=box[1],
            aabb_min_z=box[2],
            aabb_max_x=box[3],
            aabb_max_y=box[4],
            aabb_max_z=box[5],
        )

    @staticmethod
    def _user_attribute_records(
        guid: ProjectGuid, element
    ) -> list[UserAttributeRecord]:
        records: list[UserAttributeRecord] = []
        eid = ElementId(element.id)
        for index in USER_ATTRIBUTE_SCAN_RANGE:
            value = element.attrs.user_attribute(index)
            if value:
                records.append(UserAttributeRecord(guid, eid, index, value))
        return records

    @staticmethod
    def _assignment_record(
        guid: ProjectGuid, eid: ElementId
    ) -> StoreyAssignmentRecord | None:
        building = cadwork.bim.get_building(eid)
        if not building:
            return None
        storey = cadwork.bim.get_storey(eid)
        # The model carries no "spans" channel; it is only meaningful when a row
        # is seeded into the store directly, so a model read reports False.
        return StoreyAssignmentRecord(guid, eid, building, storey, spans=False)

    @staticmethod
    def _building_storey_records(
        guid: ProjectGuid, assignments: Sequence[StoreyAssignmentRecord]
    ) -> tuple[list[BuildingRecord], list[StoreyRecord]]:
        """The BMT registry, unioned with anything the assignments reference.

        Reading the registry alone could leave an assignment pointing at a
        storey row that does not exist (its storey/building FK would dangle), so
        any ``(building, storey)`` named by an assignment is synthesized here
        (elevation 0 if the registry has no height for it). The snapshot is then
        internally consistent and survives the storey FKs on ``pull``.
        """
        elevations: dict[tuple[str, str], float] = {}
        building_names: set[str] = set()

        for building in cadwork.bim.get_all_buildings():
            building_names.add(building)
            for storey in cadwork.bim.get_all_storeys(building):
                elevations[(building, storey)] = cadwork.bim.get_storey_height(
                    building, storey
                )

        for assignment in assignments:
            building_names.add(assignment.building_name)
            key = (assignment.building_name, assignment.storey_name)
            if assignment.storey_name and key not in elevations:
                elevations[key] = 0.0

        buildings = [BuildingRecord(guid, name) for name in sorted(building_names)]
        storeys = [
            StoreyRecord(guid, building, storey, elevation)
            for (building, storey), elevation in sorted(elevations.items())
        ]
        return buildings, storeys


@dataclass(frozen=True, slots=True)
class WriteResult:
    """Counts of what :meth:`ModelWriter.apply` did to the model."""

    created: int
    updated: int
    deleted: int
    skipped: int


# ---- creation: stored geometry -> element create_* ----


def _axis_points(g: GeometryRecord) -> AxisPoints:
    return AxisPoints(
        Point3D(g.p1x, g.p1y, g.p1z),
        Point3D(g.p2x, g.p2y, g.p2z),
        Point3D(g.p3x, g.p3y, g.p3z),
    )


def _segment(g: GeometryRecord) -> Segment:
    return Segment(Point3D(g.p1x, g.p1y, g.p1z), Point3D(g.p2x, g.p2y, g.p2z))


def _create_rect_beam(g: GeometryRecord) -> int:
    return Beam.create_rectangular(RectSection(g.width, g.height), _axis_points(g)).id


def _create_plate(g: GeometryRecord) -> int:
    return Plate.create_rectangular(PanelSection(g.width, g.height), _axis_points(g)).id


def _create_opening(g: GeometryRecord) -> int:
    return Opening.create_rectangular(
        PanelSection(g.width, g.height), _axis_points(g)
    ).id


def _create_drilling(g: GeometryRecord) -> int:
    return Drilling.create(g.width, _segment(g)).id


def _create_line(g: GeometryRecord) -> int:
    return Line.create(_segment(g)).id


def _create_node(g: GeometryRecord) -> int:
    return Node.create(Point3D(g.p1x, g.p1y, g.p1z)).id


def _create_circular_mep(g: GeometryRecord) -> int:
    return CircularMep.create(
        g.width, [Point3D(g.p1x, g.p1y, g.p1z), Point3D(g.p2x, g.p2y, g.p2z)]
    ).id


def _create_rect_mep(g: GeometryRecord) -> int:
    return RectangularMep.create(
        g.width, g.height, [Point3D(g.p1x, g.p1y, g.p1z), Point3D(g.p2x, g.p2y, g.p2z)]
    ).id


# Tokens reconstructable from stored scalar geometry. Cover parents (wall / slab
# / roof) are created beam-shaped and re-flagged from their cover record in the
# cover pass. Containers are handled separately (they need their members first).
# Anything absent here — surface, connector axis, auxiliary, bare element — has
# no faithful create_* path from scalar geometry and is skipped with a warning.
_BUILDERS = {
    "beam": _create_rect_beam,
    "wall": _create_rect_beam,
    "slab": _create_rect_beam,
    "roof": _create_rect_beam,
    "plate": _create_plate,
    "opening": _create_opening,
    "drilling": _create_drilling,
    "line": _create_line,
    "node": _create_node,
    "circularmep": _create_circular_mep,
    "rectangularmep": _create_rect_mep,
}

# Tokens whose dimension scalars are meaningful to push back. A node / surface /
# line / container has no rectangular section, so re-setting width/height/length
# on it would be noise (and, in real cadwork, an error).
_DIMENSIONED_TOKENS = frozenset(
    {
        "beam",
        "wall",
        "slab",
        "roof",
        "plate",
        "opening",
        "drilling",
        "circularmep",
        "rectangularmep",
    }
)


class ModelWriter:
    """Apply a :class:`SnapshotDiff` to the live model (create / update / delete)."""

    @suppressed_display
    def apply(self, diff: SnapshotDiff) -> WriteResult:
        """Reconstruct, update, and prune the model to match ``diff.target``.

        Order matters: non-container elements are created first so containers
        can be built from their (now-existing) members; then every mapped
        element gets its attributes, dims, cover kind, grouping, container
        membership, and storey assignment, with the ``stored → model`` id map
        applied to every cross-element reference; finally removed elements are
        deleted. Returns a :class:`WriteResult` tally.
        """
        target = diff.target
        elements_by_id = {e.id: e for e in target.elements}
        geom_by = target.geometry_by_element()
        attrs_by = target.attributes_by_element()
        covers_by = target.covers_by_element()
        uattrs_by = target.user_attributes_by_element()
        members_by_container = target.members_by_container()
        assignments_by = target.assignments_by_element()

        id_map: dict[ElementId, ElementId] = {}
        # Existing elements keep their id; only created ones get remapped.
        for stored_id in diff.dirty_ids:
            id_map[stored_id] = stored_id

        created, skipped = self._create_elements(
            diff.new_ids,
            elements_by_id,
            geom_by,
            attrs_by,
            members_by_container,
            id_map,
        )

        self._apply_storey_registry(target.storeys)

        for stored_id, model_id in id_map.items():
            self._apply_attributes(
                model_id, attrs_by.get(stored_id), uattrs_by.get(stored_id)
            )
            self._apply_dims(
                model_id, elements_by_id[stored_id], geom_by.get(stored_id)
            )
            self._apply_cover(model_id, covers_by.get(stored_id))
            self._apply_assignment(model_id, assignments_by.get(stored_id))

        self._apply_container_membership(members_by_container, id_map)
        self._apply_project(target.project)

        deleted = self._delete_removed(diff.removed)

        return WriteResult(
            created=created,
            updated=len(diff.dirty_ids),
            deleted=deleted,
            skipped=skipped,
        )

    # ---- creation ----

    def _create_elements(
        self,
        new_ids: Sequence[ElementId],
        elements_by_id: dict[ElementId, ElementRecord],
        geom_by: dict[ElementId, GeometryRecord],
        attrs_by: dict[ElementId, AttributeRecord],
        members_by_container: dict[ContainerId, list[MemberId]],
        id_map: dict[ElementId, ElementId],
    ) -> tuple[int, int]:
        created = 0
        skipped = 0

        containers = [
            ContainerId(i)
            for i in new_ids
            if elements_by_id[i].element_type == "container"
        ]
        non_containers = [
            i for i in new_ids if elements_by_id[i].element_type != "container"
        ]

        for stored_id in non_containers:
            builder = _BUILDERS.get(elements_by_id[stored_id].element_type)
            geometry = geom_by.get(stored_id)
            if builder is None or geometry is None:
                warnings.warn(
                    f"push: element {stored_id} of type "
                    f"{elements_by_id[stored_id].element_type!r} is not "
                    "reconstructable; skipping",
                    stacklevel=3,
                )
                skipped += 1
                continue
            id_map[stored_id] = ElementId(builder(geometry))
            created += 1

        for stored_id in containers:
            if self._create_container(
                stored_id, attrs_by, members_by_container, id_map
            ):
                created += 1
            else:
                skipped += 1

        return created, skipped

    @staticmethod
    def _create_container(
        stored_id: ContainerId,
        attrs_by: dict[ElementId, AttributeRecord],
        members_by_container: dict[ContainerId, list[MemberId]],
        id_map: dict[ElementId, ElementId],
    ) -> bool:
        """Rebuild a container from its already-created members (best-effort).

        cadwork can only create a container from a configured standard; the
        store has no standard name, so this passes an empty one. That works
        in-process for the round-trip but may fail against a live cadwork — the
        push is best-effort, so on failure the container is skipped with a
        warning rather than aborting the whole write.
        """
        member_ids = [
            id_map[m] for m in members_by_container.get(stored_id, []) if m in id_map
        ]
        attr = attrs_by.get(stored_id)
        name = attr.name if attr is not None else ""
        try:
            new_id = cadwork.elements.create_auto_container_from_standard(
                member_ids, name, ""
            )
        except Exception as exc:  # noqa: BLE001 — best-effort, reported not raised
            warnings.warn(
                f"push: could not reconstruct container {stored_id}: {exc}",
                stacklevel=3,
            )
            return False
        id_map[stored_id] = ElementId(new_id)
        return True

    # ---- per-element updates ----

    @staticmethod
    def _apply_attributes(
        model_id: ElementId,
        attr: AttributeRecord | None,
        user_attrs: list[UserAttributeRecord] | None,
    ) -> None:
        if attr is not None:
            a = cadwork.attributes
            ids = [model_id]
            a.set_name(ids, attr.name)
            a.set_group(ids, attr.group_name)
            a.set_subgroup(ids, attr.subgroup)
            a.set_comment(ids, attr.comment)
            a.set_material_name(ids, attr.material_name)
            a.set_sku(ids, attr.sku)
            a.set_production_number(ids, attr.production_number)
            a.set_part_number(ids, attr.part_number)
            a.set_assembly_number(ids, attr.assembly_number)
        for ua in user_attrs or ():
            cadwork.attributes.set_user_attribute([model_id], ua.attr_index, ua.value)

    @staticmethod
    def _apply_dims(
        model_id: ElementId, element: ElementRecord, geometry: GeometryRecord | None
    ) -> None:
        # Dimensions update; axes (points) are intentionally never moved — the
        # adapter has no point setter, so an existing element keeps its frame.
        if geometry is None or element.element_type not in _DIMENSIONED_TOKENS:
            return
        ids = [model_id]
        cadwork.geometry.set_width(ids, geometry.width)
        cadwork.geometry.set_height(ids, geometry.height)
        cadwork.geometry.set_length(ids, geometry.length)

    @staticmethod
    def _apply_cover(model_id: ElementId, cover: CoverRecord | None) -> None:
        if cover is not None:
            cadwork.attributes.set_cover_kind([model_id], CoverKind(cover.cover_kind))

    @staticmethod
    def _apply_assignment(
        model_id: ElementId, assignment: StoreyAssignmentRecord | None
    ) -> None:
        if assignment is not None and assignment.building_name:
            cadwork.bim.set_building_and_storey(
                [model_id], assignment.building_name, assignment.storey_name
            )

    # ---- cross-element / global ----

    @staticmethod
    def _apply_container_membership(
        members_by_container: dict[ContainerId, list[MemberId]],
        id_map: dict[ElementId, ElementId],
    ) -> None:
        for container_id, member_ids in members_by_container.items():
            if container_id not in id_map:
                warnings.warn(
                    f"push: container {container_id} is not in the model; "
                    "its membership links are skipped",
                    stacklevel=3,
                )
                continue
            mapped_members = [id_map[m] for m in member_ids if m in id_map]
            cadwork.elements.set_container_contents(
                id_map[container_id], mapped_members
            )

    @staticmethod
    def _apply_storey_registry(storeys: Sequence[StoreyRecord]) -> None:
        for storey in storeys:
            cadwork.bim.set_storey_height(
                storey.building_name, storey.name, storey.elevation
            )

    @staticmethod
    def _apply_project(project: ProjectRecord) -> None:
        # GUID is read-only in cwapi3d, so it is never written back.
        p = Document().project
        p.set_name(project.name)
        p.set_number(project.number)
        p.set_part(project.part)
        p.set_architect(project.architect)
        p.set_customer(project.customer)
        p.set_designer(project.designer)
        p.set_deadline(project.deadline)
        p.set_description(project.description)
        p.set_address(project.address)
        p.set_postal_code(project.postal_code)
        p.set_city(project.city)
        p.set_country(project.country)
        p.set_latitude(project.latitude)
        p.set_longitude(project.longitude)
        p.set_elevation(project.elevation)

    @staticmethod
    def _delete_removed(removed: Sequence[ElementRecord]) -> int:
        ids = [record.id for record in removed]
        if ids:
            cadwork.elements.delete_elements(ids)
        return len(ids)
