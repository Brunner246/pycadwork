"""Which elements touch — single-element neighbours and the whole-model graph.

Both APIs decide contact **geometrically by default** (tightest bounding region
grown by a tolerance, accelerated by a spatial index) and both accept a custom
``connects(a, b) -> bool`` predicate. ``ConnectionGraph`` is an undirected,
in-memory snapshot of contacts — it exposes adjacency only; filter by type
yourself.

    uv run python -m examples.connectivity
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Point3D,
    RectSection,
    build_connection_graph,
    find_connected,
)


def _beam(x: float, length: float = 100.0) -> Beam:
    """A 10x10 beam along +x spanning [x, x + length]."""
    return Beam.create_rectangular(
        RectSection(10.0, 10.0),
        AxisPoints(Point3D(x, 0, 0), Point3D(x + length, 0, 0), Point3D(x, 0, 1)),
    )


def demo_find_connected() -> None:
    """`find_connected` returns everything touching one element, within a tolerance."""
    a = _beam(0)  # [0, 100]
    b = _beam(100)  # touches a end-to-end
    c = _beam(1000)  # far away

    neighbours = find_connected(a, among=[a, b, c], tolerance=1.0)
    print("a touches:", [n.id for n in neighbours])  # [b.id]
    assert b in neighbours and c not in neighbours


def demo_connection_graph() -> None:
    """Build the contact graph and ask it about adjacency and sub-assemblies."""
    a, b = _beam(0), _beam(100)  # touch -> one component
    c, d = _beam(1000), _beam(1100)  # touch each other -> another component

    graph = build_connection_graph([a, b, c, d])
    print(graph)  # ConnectionGraph(4 nodes, 2 edges)
    print("a's neighbours =", [n.id for n in graph.neighbors(a)])
    print("a connected to b?", graph.is_connected(a, b))

    components = graph.connected_components()
    print("components =", [sorted(e.id for e in comp) for comp in components])
    print("component containing c =", sorted(e.id for e in graph.component_of(c)))


def demo_custom_predicate() -> None:
    """Swap the geometric rule for any (a, b) -> bool — here, share a group."""
    a, b, c = _beam(0), _beam(1000), _beam(2000)  # geometrically disjoint
    a.attrs.group = b.attrs.group = "frame"
    c.attrs.group = "roof"

    same_group = lambda x, y: x.attrs.group == y.attrs.group  # noqa: E731
    graph = build_connection_graph([a, b, c], connects=same_group)

    # a and b share "frame" -> connected despite being far apart; c is alone.
    print("a connected to b?", graph.is_connected(a, b))  # True
    print("a connected to c?", graph.is_connected(a, c))  # False


def run() -> None:
    """Run every connectivity demo in order."""
    demo_find_connected()
    demo_connection_graph()
    demo_custom_predicate()


if __name__ == "__main__":
    run()
