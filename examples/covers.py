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
    CoverBuilder,
    CoverKind,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
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


def run() -> None:
    """Run every cover demo in order."""
    demo_children_are_polymorphic()
    demo_discover_covers()
    demo_cover_builder()
    demo_imperative_membership()


if __name__ == "__main__":
    run()
