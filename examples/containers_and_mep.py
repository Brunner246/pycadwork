"""Containers (real containment) and MEP runs (pipes and ducts).

A ``Container`` is an aggregate like a cover, but the link is *real containment*
in the model, not a shared grouping value — so it does not inherit the cover
``Aggregate``. ``CircularMep`` (a pipe) and ``RectangularMep`` (a duct) are
ordinary path-anchored leaf elements.

    uv run python -m examples.containers_and_mep
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    CircularMep,
    Container,
    Point3D,
    RectSection,
    RectangularMep,
    discover_containers,
    parent_container,
)


def _beam(x: float = 0.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x, 3000, 0), Point3D(x, 0, 1)),
    )


def demo_create_and_inspect_container() -> Container:
    """Build a container from elements using a configured cadwork standard."""
    a, b = _beam(0), _beam(600)
    container = Container.create_from_standard(
        [a, b], output_name="C1", standard_element_name="MyContainerStandard"
    )
    print("created", container)
    print("children      =", len(container.children))  # 2
    print("beam children =", len(container.children_of(Beam)))

    # Any element can report its owning container (free function, like discover_*).
    print("a's container is C1?", parent_container(a) == container)
    return container


def demo_mutate_membership(container: Container) -> None:
    """Membership is mutable: add / remove / replace, each a batched write."""
    extra = _beam(1200)
    container.add_child(extra)
    print("after add_child   =", len(container.children))  # 3

    container.remove_child(extra)
    print("after remove_child =", len(container.children))  # 2

    container.replace_children([extra])
    print("after replace      =", len(container.children))  # 1


def demo_discover_containers() -> None:
    """`discover_containers` finds every container in the model, typed."""
    for container in discover_containers():
        print("discovered", container, "with", len(container.children), "children")


def demo_mep_runs() -> None:
    """A pipe carries a diameter; a duct carries width and depth (height)."""
    path = [Point3D(0, 0, 0), Point3D(0, 0, 3000)]

    pipe = CircularMep.create(diameter=80.0, points=path)
    print("pipe diameter =", pipe.diameter, "radius =", pipe.geometry.radius)

    duct = RectangularMep.create(width=200.0, depth=100.0, points=path)
    # A rectangular run maps width -> geometry.width, depth -> geometry.height.
    print("duct width =", duct.geometry.width, "depth =", duct.geometry.height)


def run() -> None:
    """Run every container/MEP demo in order."""
    container = demo_create_and_inspect_container()
    demo_mutate_membership(container)
    demo_discover_containers()
    demo_mep_runs()


if __name__ == "__main__":
    run()
