"""ModelReader projects the model into records; ModelWriter applies them back."""

from __future__ import annotations

from dataclasses import replace

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode, MaterialSnapshot
from pycadwork.persistence._diff import diff
from pycadwork.persistence.mappers import ModelReader, ModelWriter
from pycadwork.persistence.records import ElementRecord, ModelSnapshot, ProjectRecord


def _beam(x: float = 0.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
    )


def _plate() -> Plate:
    return Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


# ---- ModelReader ----


def test_read_types_each_element_by_its_token() -> None:
    beam, plate = _beam(), _plate()

    snapshot = ModelReader().read()

    by_id = {e.id: e.element_type for e in snapshot.elements}
    assert by_id == {beam.id: "beam", plate.id: "plate"}


def test_read_captures_attributes_and_geometry() -> None:
    beam = _beam()
    beam.attrs.name = "Stud"
    beam.attrs.material_name = "Pine"

    snapshot = ModelReader().read()

    attr = snapshot.attributes_by_element()[beam.id]
    assert attr.name == "Stud"
    assert attr.material_name == "Pine"

    geom = snapshot.geometry_by_element()[beam.id]
    assert geom.width == 80.0
    assert geom.height == 200.0
    assert geom.length == 3000.0


def test_read_captures_cover_kind_and_grouping() -> None:
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall, stud = _beam(0), _beam(600)
    cadwork.attributes.set_cover_kind([wall.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall.id, stud.id], "WallA")

    snapshot = ModelReader().read()

    covers = snapshot.covers_by_element()
    assert covers[wall.id].cover_kind == CoverKind.FRAMED_WALL.value
    assert snapshot.attributes_by_element()[stud.id].group_name == "WallA"


def test_read_captures_container_membership() -> None:
    from pycadwork import Container

    b1, b2 = _beam(0), _beam(600)
    container = Container.create_from_standard([b1, b2], "Cont", "std")

    snapshot = ModelReader().read()

    members = snapshot.members_by_container()
    assert sorted(members[container.id]) == sorted([b1.id, b2.id])


def test_read_captures_user_attributes_in_scan_range() -> None:
    beam = _beam()
    beam.attrs.set_user_attribute(1, "spans-storeys")

    snapshot = ModelReader().read()

    user_attrs = snapshot.user_attributes_by_element()[beam.id]
    assert (user_attrs[0].attr_index, user_attrs[0].value) == (1, "spans-storeys")


def test_read_dedupes_material_master_and_links_each_element() -> None:
    cadwork.material.register(
        MaterialSnapshot(
            name="Pine",
            group="Softwood",
            grade="C24",
            modulus_elasticity_1=11000.0,
            shear_modulus_1=690.0,
            weight=420.0,
        )
    )
    b1, b2 = _beam(0), _beam(600)
    b1.attrs.material_name = "Pine"
    b2.attrs.material_name = "Pine"

    snapshot = ModelReader().read()

    # One master row for the shared material, carrying the structural props.
    assert len(snapshot.materials) == 1
    material = snapshot.materials_by_name()["Pine"]
    assert material.group_name == "Softwood"
    assert material.grade == "C24"
    assert material.modulus_elasticity_1 == 11000.0
    assert material.shear_modulus_1 == 690.0
    assert material.weight == 420.0

    # One link per element, carrying its id + cadwork GUID + the joining name.
    links = snapshot.element_materials_by_element()
    assert set(links) == {b1.id, b2.id}
    assert links[b1.id].material_name == "Pine"
    assert links[b1.id].cadwork_guid == b1.attrs.cadwork_guid


def test_read_emits_no_material_row_for_an_unmaterialed_element() -> None:
    _beam()  # never assigned a material

    snapshot = ModelReader().read()

    assert snapshot.materials == ()
    assert snapshot.element_materials == ()


# ---- ModelWriter ----


def test_writer_creates_missing_elements_from_geometry() -> None:
    beam = _beam()
    target = ModelReader().read()
    Document().delete([beam])

    current = ModelReader().read()
    result = ModelWriter().apply(diff(current, target))

    assert result.created == 1
    rebuilt = Document().elements()
    assert len(rebuilt) == 1
    assert rebuilt[0].geometry.width == 80.0


def test_writer_updates_existing_element_dims_without_moving_it() -> None:
    beam = _beam()
    target = ModelReader().read()
    widened = replace(
        target,
        geometries=tuple(replace(g, width=120.0) for g in target.geometries),
    )

    current = ModelReader().read()
    result = ModelWriter().apply(diff(current, widened))

    assert result.updated == 1
    assert result.created == 0
    again = Document().get(beam.id)
    assert again.geometry.width == 120.0
    # Axis is untouched: the start point is exactly where it was created.
    assert again.geometry.start_point == Point3D(0, 0, 0)


def test_writer_deletes_removed_elements() -> None:
    _beam()
    plate = _plate()
    full = ModelReader().read()
    # Target keeps only the plate; the beam should be deleted on apply.
    target = replace(
        full,
        elements=tuple(e for e in full.elements if e.id == plate.id),
        attributes=tuple(a for a in full.attributes if a.element_id == plate.id),
        geometries=tuple(g for g in full.geometries if g.element_id == plate.id),
    )

    result = ModelWriter().apply(diff(full, target))

    assert result.deleted == 1
    assert {e.id for e in Document().elements()} == {plate.id}


def test_writer_skips_non_reconstructable_types() -> None:
    # A bare snapshot whose only element has an unknown token: nothing is built.
    guid = Document().guid
    target = ModelSnapshot(
        project=ProjectRecord(guid),
        elements=(ElementRecord(guid, 1, "mysterytype"),),
    )

    with pytest.warns(UserWarning, match="not reconstructable"):
        result = ModelWriter().apply(diff(ModelReader().read(), target))

    assert result.created == 0
    assert result.skipped == 1
    assert Document().elements() == []
