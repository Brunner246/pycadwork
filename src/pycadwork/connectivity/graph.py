"""An undirected graph of element connections, and the scan that builds it.

Nodes are :class:`~pycadwork.element.Element` instances (hashable by
``(type, id)``); an edge means the two elements touch or intersect. The
graph is a plain in-memory value — building it snapshots the current
contacts; it does not stay live as the model changes.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Iterator

from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.connectivity.detection import (
    DEFAULT_TOLERANCE,
    active_elements,
    connects as geometric_connects,
)
from pycadwork.element import Element
from pycadwork.geometry import RTreeIndex3D

Predicate = Callable[[Element, Element], bool]


class ConnectionGraph:
    """Undirected graph whose nodes are elements and edges are connections.

    Adjacency only — there is no per-element-type accessor. Use
    :meth:`nodes`, :meth:`neighbors`, :meth:`connected_components`, etc. and
    filter by type yourself when you need to.
    """

    __slots__ = ("_adj",)

    def __init__(self, nodes: Iterable[Element] = ()) -> None:
        self._adj: dict[Element, set[Element]] = {node: set() for node in nodes}

    # ---- construction ----

    def add_node(self, element: Element) -> None:
        self._adj.setdefault(element, set())

    def add_edge(self, a: Element, b: Element) -> None:
        """Connect ``a`` and ``b`` (adding either as a node if absent).

        A self-edge (``a == b``) is ignored — an element does not connect to
        itself.
        """
        if a == b:
            return
        self._adj.setdefault(a, set()).add(b)
        self._adj.setdefault(b, set()).add(a)

    # ---- queries ----

    def nodes(self) -> list[Element]:
        return list(self._adj)

    def neighbors(self, element: Element) -> list[Element]:
        """The elements directly connected to ``element``.

        Raises:
            KeyError: if ``element`` is not a node of this graph.
        """
        return list(self._adj[element])

    def is_connected(self, a: Element, b: Element) -> bool:
        """True if ``a`` and ``b`` share a direct edge."""
        return b in self._adj.get(a, ())

    def edges(self) -> list[tuple[Element, Element]]:
        """Every edge once, as ``(a, b)`` pairs (order within a pair is arbitrary)."""
        seen: set[frozenset[Element]] = set()
        result: list[tuple[Element, Element]] = []
        for a, neighbours in self._adj.items():
            for b in neighbours:
                key = frozenset((a, b))
                if key not in seen:
                    seen.add(key)
                    result.append((a, b))
        return result

    def connected_components(self) -> list[list[Element]]:
        """Partition the nodes into maximally connected groups.

        Each group is the full set of elements reachable from one another
        through edges — i.e. a touching sub-assembly. A node with no edges
        forms a singleton group.
        """
        unvisited = set(self._adj)
        components: list[list[Element]] = []
        while unvisited:
            start = next(iter(unvisited))
            component = self._reach(start, unvisited)
            components.append(component)
        return components

    def component_of(self, element: Element) -> list[Element]:
        """The connected component containing ``element`` (includes itself).

        Raises:
            KeyError: if ``element`` is not a node of this graph.
        """
        if element not in self._adj:
            raise KeyError(element)
        return self._reach(element, set(self._adj))

    def _reach(self, start: Element, pool: set[Element]) -> list[Element]:
        """BFS from ``start`` over ``pool``, removing visited nodes from ``pool``."""
        component: list[Element] = []
        queue: deque[Element] = deque((start,))
        pool.discard(start)
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbour in self._adj[node]:
                if neighbour in pool:
                    pool.discard(neighbour)
                    queue.append(neighbour)
        return component

    # ---- container protocol ----

    def __len__(self) -> int:
        return len(self._adj)

    def __iter__(self) -> Iterator[Element]:
        return iter(self._adj)

    def __contains__(self, element: object) -> bool:
        return element in self._adj

    def __repr__(self) -> str:
        edge_count = sum(len(n) for n in self._adj.values()) // 2
        return f"ConnectionGraph({len(self._adj)} nodes, {edge_count} edges)"


def build_connection_graph(
    elements: Iterable[Element] | None = None,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    connects: Predicate | None = None,  # noqa: A002 — deliberate public name
) -> ConnectionGraph:
    """Build the connection graph over a set of elements.

    ``elements`` defaults to the active identifiable elements in the model.
    Contact is decided geometrically by default (tightest bounding region,
    grown by ``tolerance``, accelerated by a spatial index); pass ``connects``
    for a custom ``(a, b) -> bool`` predicate, in which case ``tolerance`` is
    ignored and all pairs are tested directly.
    """
    nodes = list(elements) if elements is not None else active_elements()
    graph = ConnectionGraph(nodes)

    if connects is not None:
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                if connects(a, b):
                    graph.add_edge(a, b)
        return graph

    _build_geometric(graph, nodes, tolerance)
    return graph


def _build_geometric(
    graph: ConnectionGraph, nodes: list[Element], tolerance: float
) -> None:
    by_id = {node.id: node for node in nodes}
    index = RTreeIndex3D((node.id, node.geometry.aabb) for node in nodes)

    for a in nodes:
        query = a.geometry.aabb.expanded(tolerance)
        for raw_id in index.intersection(query):
            cand_id = ElementId(raw_id)
            # Add each pair once; smaller id drives, self is skipped.
            if a.id < cand_id:
                b = by_id[cand_id]
                if geometric_connects(a, b, tolerance):
                    graph.add_edge(a, b)
