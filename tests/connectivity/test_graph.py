"""Tests for pycadwork.ConnectionGraph (adjacency + components)."""

from __future__ import annotations

import pytest

from pycadwork import AxisPoints, Beam, ConnectionGraph, Point3D, RectSection


def _beam(x: float) -> Beam:
    """A throwaway beam used purely as a hashable graph node."""
    return Beam.create_rectangular(
        RectSection(10.0, 10.0),
        AxisPoints(Point3D(x, 0, 0), Point3D(x + 10, 0, 0), Point3D(x, 0, 1)),
    )


def test_neighbors_and_is_connected():
    a, b, c = _beam(0), _beam(10), _beam(20)
    g = ConnectionGraph([a, b, c])
    g.add_edge(a, b)

    assert g.neighbors(a) == [b]
    assert g.is_connected(a, b)
    assert g.is_connected(b, a)  # undirected
    assert not g.is_connected(a, c)


def test_edges_are_reported_once():
    a, b = _beam(0), _beam(10)
    g = ConnectionGraph([a, b])
    g.add_edge(a, b)

    edges = g.edges()
    assert len(edges) == 1
    assert frozenset(edges[0]) == frozenset((a, b))


def test_self_edge_is_ignored():
    a = _beam(0)
    g = ConnectionGraph([a])
    g.add_edge(a, a)
    assert g.neighbors(a) == []
    assert g.edges() == []


def test_connected_components_partition_the_nodes():
    a, b, c, d, e = _beam(0), _beam(10), _beam(20), _beam(30), _beam(40)
    g = ConnectionGraph([a, b, c, d, e])
    g.add_edge(a, b)  # cluster 1
    g.add_edge(c, d)  # cluster 2
    # e is isolated

    components = {frozenset(component) for component in g.connected_components()}
    assert components == {
        frozenset((a, b)),
        frozenset((c, d)),
        frozenset((e,)),
    }


def test_component_of_returns_the_whole_cluster():
    a, b, c, d = _beam(0), _beam(10), _beam(20), _beam(30)
    g = ConnectionGraph([a, b, c, d])
    g.add_edge(a, b)
    g.add_edge(b, c)  # a-b-c chain; d isolated

    assert set(g.component_of(a)) == {a, b, c}
    assert g.component_of(d) == [d]


def test_component_of_unknown_node_raises():
    a, stranger = _beam(0), _beam(10)
    g = ConnectionGraph([a])
    with pytest.raises(KeyError):
        g.component_of(stranger)


def test_neighbors_of_unknown_node_raises():
    a, stranger = _beam(0), _beam(10)
    g = ConnectionGraph([a])
    with pytest.raises(KeyError):
        g.neighbors(stranger)


def test_add_edge_introduces_missing_nodes():
    a, b = _beam(0), _beam(10)
    g = ConnectionGraph()
    g.add_edge(a, b)
    assert a in g
    assert b in g


def test_container_protocol():
    a, b, c = _beam(0), _beam(10), _beam(20)
    g = ConnectionGraph([a, b, c])
    assert len(g) == 3
    assert a in g
    assert set(iter(g)) == {a, b, c}
    assert set(g.nodes()) == {a, b, c}
