"""Cover objects — Wall, Slab, Roof — and the grouping link that defines them.

In cadwork a wall/floor/roof and its members are **not** joined by a container
API: they share a ``group`` (or ``subgroup``) value, and which one is the
project-wide setting from ``get_element_grouping_type()``. ``pycadwork`` models
this faithfully — an aggregate's ``children`` are its siblings in the group,
minus itself.

    uv run python -m examples.covers

.. note::

   Normally walls are produced by the cadwork wall tool and you just *discover*
   them. To stay runnable standalone, the setup below flags a beam as a wall and
   groups members with it through the version-isolation seam — that flagging
   mimics what the cadwork UI does; it is not part of normal pycadwork usage.
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    CoverAssigner,
    CoverBuilder,
    CoverKind,
    Group,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Roof,
    Slab,
    Wall,
    discover_covers,
)

# Seam access — only for the UI-mimicking setup (flagging a cover kind).
from pycadwork.cadwork_adapter import cadwork


def _beam(x: float = 0.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
    )


def _panel() -> Plate:
    return Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


def _box(x0: float, y0: float, z0: float, dx: float, dy: float, dz: float) -> Beam:
    """An axis-aligned beam spanning the given extent (its OBB equals its AABB).

    Built along +X with +Z as the third point so the local frame matches the
    world axes — the spatial overlap maths the assigner uses stays predictable.
    """
    return Beam.create_rectangular(
        RectSection(dy, dz),
        AxisPoints(
            Point3D(x0, y0, z0), Point3D(x0 + dx, y0, z0), Point3D(x0, y0, z0 + 1)
        ),
    )


def _build_a_wall(group: str = "WallA") -> Wall:
    """Fabricate a wall: a beam flagged FRAMED_WALL, plus members sharing its group.

    The ``set_cover_kind`` call is setup that mimics the cadwork wall tool.
    """
    wall_parent, stud, sheathing = _beam(0), _beam(600), _panel()
    cadwork.attributes.set_cover_kind([wall_parent.id], CoverKind.FRAMED_WALL)
    # Members are linked to the wall by sharing its grouping value.
    cadwork.attributes.set_group([wall_parent.id, stud.id, sheathing.id], group)
    wall = discover_covers([wall_parent.id])[0]
    assert isinstance(wall, Wall)
    return wall


def demo_children_are_polymorphic() -> None:
    """A cover's children are a live list[Element]; narrow by type when needed."""
    wall = _build_a_wall()
    print("kind          =", wall.kind)  # CoverKind.FRAMED_WALL
    print("children      =", len(wall.children))  # the studs + sheathing
    print("beam children =", len(wall.children_of(Beam)))
    print("plate children =", len(wall.children_of(Plate)))


def demo_discover_covers() -> None:
    """`discover_covers` scans the model and returns one typed aggregate per cover."""
    _build_a_wall("WallB")
    for cover in discover_covers():
        print(
            "discovered", type(cover).__name__, "with", len(cover.children), "children"
        )


def demo_cover_builder() -> None:
    """CoverBuilder buckets a set of elements by grouping and types each cover.

    The builder is read-only — it *identifies and types* existing covers. Use
    ``.only(Wall)`` to keep one family.
    """
    wall = _build_a_wall("WallC")
    elements = [wall, *wall.children]

    covers = CoverBuilder(elements).aggregate_by_grouping().build()
    print("builder found", len(covers), "cover(s)")

    walls = CoverBuilder(elements).aggregate_by_grouping().only(Wall).build()
    print("walls only:", [type(w).__name__ for w in walls])


def demo_imperative_membership() -> None:
    """Attach / detach children imperatively — these write the grouping value."""
    wall = _build_a_wall("WallD")
    newcomer = _beam(1200)

    wall.add_child(newcomer)
    print("after add_child, children =", len(wall.children))

    wall.remove_child(newcomer)
    print("after remove_child, children =", len(wall.children))


def demo_slab_and_roof() -> None:
    """Walls aren't special — Slab and Roof are the same aggregate, different kinds."""
    floor_beam, roof_beam = _beam(0), _beam(600)
    # setup that mimics the cadwork UI: flag the cover kinds.
    cadwork.attributes.set_cover_kind([floor_beam.id], CoverKind.FRAMED_FLOOR)
    cadwork.attributes.set_cover_kind([roof_beam.id], CoverKind.FRAMED_ROOF)
    cadwork.attributes.set_group([floor_beam.id], "FloorA")
    cadwork.attributes.set_group([roof_beam.id], "RoofA")

    slab = discover_covers([floor_beam.id])[0]
    roof = discover_covers([roof_beam.id])[0]
    assert isinstance(slab, Slab)
    assert isinstance(roof, Roof)
    print("slab kind =", slab.kind)  # CoverKind.FRAMED_FLOOR
    print("roof kind =", roof.kind)  # CoverKind.FRAMED_ROOF


def demo_group_view() -> None:
    """`Group` is the grouping engine under a cover's children — usable directly.

    A cover's ``children`` are its siblings in the active group/subgroup; ``Group``
    exposes that same membership for any element, narrowable by type.
    """
    wall = _build_a_wall("WallE")
    group = Group.of(wall)  # built from the wall's value under the active mode
    print("group key    =", group.key, "mode =", group.mode.name)
    print("all members  =", len(group.members()))  # wall + its members
    print("beam members =", len(group.members_of(Beam)))


def demo_assign_loose_elements() -> None:
    """`CoverAssigner` attaches loose elements to the cover they spatially sit in.

    Broad phase prunes candidates with a spatial index; an exact box-overlap test
    confirms; the largest overlap wins. Each attachment is reported.
    """
    wall_box = _box(0, 0, 0, 1000, 200, 3000)
    cadwork.attributes.set_cover_kind([wall_box.id], CoverKind.FRAMED_WALL)
    cadwork.attributes.set_group([wall_box.id], "WallF")
    wall = discover_covers([wall_box.id])[0]

    stud = _box(100, 0, 100, 80, 200, 2000)  # sits inside the wall's extent
    report = CoverAssigner([wall]).assign([stud])
    for assignment in report:  # list[CoverAssignment]
        print(
            "attached",
            type(assignment.element).__name__,
            "to group",
            assignment.cover.id,
            "(uncertain)" if assignment.uncertain else "",
        )
    print("stud group now =", stud.attrs.group)  # "WallF"


def run() -> None:
    """Run every cover demo in order."""
    demo_children_are_polymorphic()
    demo_discover_covers()
    demo_cover_builder()
    demo_imperative_membership()
    demo_slab_and_roof()
    demo_group_view()
    demo_assign_loose_elements()


if __name__ == "__main__":
    run()
