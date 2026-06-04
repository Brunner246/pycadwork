"""Tests for pycadwork.build_connection_graph.

As in test_find.py, beams are axis-aligned so their fake-derived boxes are
``[x, x+length] x [y, y+width] x [z, z+height]`` and can be made to touch or
stay apart deterministically.
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Point3D,
    RectSection,
    build_connection_graph,
)


def _beam(x: float, length: float = 100.0) -> Beam:
    return Beam.create_rectangular(
        RectSection(10.0, 10.0),
        AxisPoints(
            Point3D(x, 0, 0),
            Point3D(x + length, 0, 0),
            Point3D(x, 0, 1.0),
        ),
    )


def test_edges_reflect_touching_elements():
    a = _beam(0)  # [0, 100]
    b = _beam(100)  # touches a
    c = _beam(1000)  # far away

    g = build_connection_graph([a, b, c])

    assert g.is_connected(a, b)
    assert not g.is_connected(a, c)
    assert not g.is_connected(b, c)


def test_each_edge_added_once_and_no_self_loops():
    a = _beam(0)
    b = _beam(100)
    g = build_connection_graph([a, b])

    assert len(g.edges()) == 1
    assert g.neighbors(a) == [b]
    assert a not in g.neighbors(a)


def test_connected_components_group_touching_assemblies():
    a = _beam(0)  # [0, 100]
    b = _beam(100)  # touches a   -> cluster {a, b}
    c = _beam(1000)  # [1000, 1100]
    d = _beam(1100)  # touches c   -> cluster {c, d}

    g = build_connection_graph([a, b, c, d])

    components = {frozenset(component) for component in g.connected_components()}
    assert components == {frozenset((a, b)), frozenset((c, d))}


def test_elements_argument_scopes_the_graph():
    a = _beam(0)
    b = _beam(100)  # touches a
    _excluded = _beam(200)  # touches b, but left out of the node set

    g = build_connection_graph([a, b])

    assert set(g.nodes()) == {a, b}
    assert len(g.edges()) == 1


def test_default_builds_over_the_active_model():
    a = _beam(0)
    b = _beam(100)  # touches a
    c = _beam(5000)  # isolated

    g = build_connection_graph()

    assert set(g.nodes()) == {a, b, c}
    assert g.is_connected(a, b)
    assert g.component_of(c) == [c]


def test_custom_predicate_builds_a_complete_graph():
    a = _beam(0)
    b = _beam(1000)  # geometrically disjoint
    c = _beam(2000)  # geometrically disjoint

    g = build_connection_graph([a, b, c], connects=lambda _x, _y: True)

    assert len(g.edges()) == 3
    assert len(g.connected_components()) == 1
