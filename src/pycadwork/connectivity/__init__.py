"""Element connectivity: find touching/intersecting elements and graph them.

* :func:`find_connected` — the elements that touch or intersect one element.
* :func:`build_connection_graph` — the whole-model (or scoped) connection
  graph, as a :class:`ConnectionGraph`.

Both decide contact geometrically by default (reusing the geometry and
spatial-index layers), and both accept a custom ``connects`` predicate.
"""
from __future__ import annotations

from pycadwork.connectivity.find import find_connected
from pycadwork.connectivity.graph import ConnectionGraph, build_connection_graph

__all__ = [
    "ConnectionGraph",
    "build_connection_graph",
    "find_connected",
]
