"""Synchronizer end-to-end: pull writes SQL, push rebuilds the model, both ways
round-trip — including delete-missing on pull and id-remap on push."""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Container,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Wall,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, GroupingMode
from pycadwork.persistence import Synchronizer, open_sqlite


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


def _empty_the_model() -> None:
    Document().delete(Document().elements())


# ---- pull ----


def test_pull_writes_element_and_geometry_rows() -> None:
    beam, plate = _beam(), _plate()
    connection = open_sqlite(":memory:")

    report = Synchronizer().pull(connection)

    assert report.created == 2
    ids = {row[0] for row in connection.execute("SELECT id FROM element")}
    assert ids == {beam.id, plate.id}
    widths = dict(connection.execute("SELECT element_id, width FROM geometry"))
    assert widths[beam.id] == 80.0
    assert widths[plate.id] == 600.0


def test_pull_is_idempotent() -> None:
    _beam()
    connection = open_sqlite(":memory:")

    Synchronizer().pull(connection)
    second = Synchronizer().pull(connection)

    assert second.created == 0
    assert second.updated == 1
    assert second.deleted == 0
    assert connection.execute("SELECT COUNT(*) FROM element") == [(1,)]


def test_pull_deletes_rows_for_elements_gone_from_the_model() -> None:
    beam, plate = _beam(), _plate()
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    Document().delete([beam])
    report = Synchronizer().pull(connection)

    assert report.deleted == 1
    assert {row[0] for row in connection.execute("SELECT id FROM element")} == {
        plate.id
    }
    # The cascade dropped the deleted element's satellites too.
    remaining = {
        row[0] for row in connection.execute("SELECT element_id FROM geometry")
    }
    assert remaining == {plate.id}


# ---- push ----


def test_push_rebuilds_an_emptied_model() -> None:
    cadwork.grouping.set_element_grouping_type(GroupingMode.GROUP)
    wall, stud = _beam(0), _beam(600)
    cadwork.attributes.set_cover_kind([wall.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall.id, stud.id], "WallA")
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    _empty_the_model()
    report = Synchronizer().push(connection)

    assert report.created == 2
    rebuilt = Document().elements()
    assert len(rebuilt) == 2
    walls = [e for e in rebuilt if isinstance(e, Wall)]
    assert len(walls) == 1
    # Grouping is restored, so cover membership is reconstructable on read.
    assert {e.attrs.group for e in rebuilt} == {"WallA"}


def test_pull_then_push_is_idempotent() -> None:
    _beam()
    _plate()
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    report = Synchronizer().push(connection)

    # Every element already exists: all updates, no creates or deletes.
    assert report.created == 0
    assert report.deleted == 0
    assert len(Document().elements()) == 2


def test_push_remaps_ids_for_storey_links_on_recreated_elements() -> None:
    beam = _beam()
    cadwork.bim.set_storey_height("B", "S0", 0.0)
    cadwork.bim.set_building_and_storey([beam.id], "B", "S0")
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    _empty_the_model()
    Synchronizer().push(connection)

    rebuilt = Document().elements()
    assert len(rebuilt) == 1
    new_id = rebuilt[0].id
    # The storey link followed the element to its freshly-assigned id.
    assert cadwork.bim.get_building(new_id) == "B"
    assert cadwork.bim.get_storey(new_id) == "S0"


def test_push_remaps_ids_for_container_membership() -> None:
    b1, b2 = _beam(0), _beam(600)
    Container.create_from_standard([b1, b2], "Cont", "std")
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    _empty_the_model()
    Synchronizer().push(connection)

    containers = [e for e in Document().elements() if isinstance(e, Container)]
    assert len(containers) == 1
    # Membership was rebuilt against the members' new ids.
    assert len(containers[0].children) == 2
