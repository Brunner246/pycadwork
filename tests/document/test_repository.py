"""Document as a live-query element repository over the model."""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Wall,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode


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


def test_elements_wraps_every_model_element_by_type() -> None:
    beam, plate = _beam(), _plate()

    elements = Document().elements()

    by_id = {e.id: e for e in elements}
    assert set(by_id) == {beam.id, plate.id}
    assert isinstance(by_id[beam.id], Beam)
    assert isinstance(by_id[plate.id], Plate)


def test_elements_is_live() -> None:
    doc = Document()
    assert doc.elements() == []
    _beam()
    assert len(doc.elements()) == 1


def test_elements_of_narrows_by_type() -> None:
    beam, plate = _beam(), _plate()
    doc = Document()

    beams = doc.elements_of(Beam)
    assert [b.id for b in beams] == [beam.id]
    assert all(isinstance(b, Beam) for b in beams)

    assert [p.id for p in doc.elements_of(Plate)] == [plate.id]


def test_active_returns_selected_elements() -> None:
    # The fake has no selection state, so "active" mirrors "all".
    beam = _beam()
    active = Document().active()
    assert {e.id for e in active} == {beam.id}


def test_get_wraps_a_single_id_in_its_subclass() -> None:
    beam = _beam()
    wrapped = Document().get(beam.id)
    assert isinstance(wrapped, Beam)
    assert wrapped.id == beam.id


def test_delete_removes_elements_from_the_model() -> None:
    beam, plate = _beam(), _plate()
    doc = Document()

    doc.delete([beam])
    assert {e.id for e in doc.elements()} == {plate.id}

    doc.delete([plate])
    assert doc.elements() == []


def test_file_path_delegates_to_the_seam() -> None:
    cadwork.project._state.model_file_name = "C:/proj/Tower.3dc"
    assert Document().file_path == "C:/proj/Tower.3dc"


def test_save_persists_the_document_through_the_seam() -> None:
    doc = Document()
    before = cadwork.project._state.save_count
    doc.save()
    assert cadwork.project._state.save_count == before + 1


def test_covers_discovers_cover_aggregates() -> None:
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall_parent, stud = _beam(0), _beam(600)
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall_parent.id, stud.id], "WallA")

    covers = Document().covers()
    assert len(covers) == 1
    assert isinstance(covers[0], Wall)
    assert covers[0].id == wall_parent.id
