"""Container: containment-backed children, mutation, parent lookup, discovery."""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Container,
    Point3D,
    RectSection,
    discover_containers,
    parent_container,
)


def _beam(x: float = 0.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
    )


def test_create_from_standard_exposes_typed_children():
    a, b = _beam(0), _beam(600)
    c = Container.create_from_standard([a, b], "C1", "StdContainer")

    assert isinstance(c, Container)
    assert {child.id for child in c.children} == {a.id, b.id}
    assert all(isinstance(child, Beam) for child in c.children)
    assert {child.id for child in c.children_of(Beam)} == {a.id, b.id}


def test_add_and_remove_children_mutates_membership():
    a, b, extra = _beam(0), _beam(600), _beam(1200)
    c = Container.create_from_standard([a, b], "C1", "StdContainer")

    c.add_child(extra)
    assert {child.id for child in c.children} == {a.id, b.id, extra.id}

    # adding an existing member is idempotent
    c.add_child(a)
    assert sorted(child.id for child in c.children) == sorted([a.id, b.id, extra.id])

    c.remove_child(b)
    assert {child.id for child in c.children} == {a.id, extra.id}


def test_replace_children_sets_exact_contents():
    a, b, new = _beam(0), _beam(600), _beam(1200)
    c = Container.create_from_standard([a, b], "C1", "StdContainer")

    c.replace_children([new])
    assert {child.id for child in c.children} == {new.id}


def test_create_from_standard_with_reference():
    a, b = _beam(0), _beam(600)
    ref = _beam(1200)
    c = Container.create_from_standard([a, b], "C1", "StdContainer", reference=ref)

    assert isinstance(c, Container)
    assert {child.id for child in c.children} == {a.id, b.id}


def test_parent_container_round_trips():
    a = _beam(0)
    orphan = _beam(600)
    c = Container.create_from_standard([a], "C1", "StdContainer")

    parent = parent_container(a)
    assert isinstance(parent, Container)
    assert parent.id == c.id
    assert parent_container(orphan) is None


def test_discover_containers_finds_flagged_containers():
    a = _beam(0)
    c = Container.create_from_standard([a], "C1", "StdContainer")
    _beam(600)  # a plain beam, not a container

    containers = discover_containers()
    assert [d.id for d in containers] == [c.id]
    assert isinstance(containers[0], Container)
