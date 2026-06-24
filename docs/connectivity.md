# Connectivity

Find which elements touch or intersect, or build the whole-model contact graph.
Both decide contact **geometrically by default** (tightest bounding region grown
by a tolerance, accelerated by the spatial index) and both accept a custom
`connects(a, b) -> bool` predicate.

```python
from pycadwork import find_connected, build_connection_graph

# everything touching one element
neighbours = find_connected(beam, tolerance=1.0)

# the whole-model graph
graph = build_connection_graph()  # ConnectionGraph
graph.neighbors(beam)  # adjacency
graph.connected_components()  # touching sub-assemblies
graph.component_of(beam)  # the sub-assembly containing `beam`

# custom contact rule
same_group = lambda a, b: a.attrs.group == b.attrs.group
g = build_connection_graph(connects=same_group)
```

`ConnectionGraph` is an undirected, in-memory snapshot of contacts (nodes are
`Element`s, hashable by `(type, id)`); it does not stay live as the model
changes. Like everything else it exposes adjacency only — filter by type
yourself when you need to.
