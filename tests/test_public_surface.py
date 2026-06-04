"""Architectural fitness: no type-discriminating aggregate accessors.

The package returns ``list[Element]`` from aggregate APIs and offers a
single parameterized helper ``Group.members_of(cls)`` / ``Aggregate.children_of(cls)``.
If anyone ever adds a ``.beams`` / ``.plates`` / ``.drillings`` (or similar)
property to a public class, this test fails. To filter by type, use
``children_of(Beam)``.
"""

from __future__ import annotations

from pycadwork import Aggregate, ConnectionGraph, Group, Roof, Slab, Wall

FORBIDDEN_NAMES = {
    "beams",
    "plates",
    "drillings",
    "nodes",
    "surfaces",
    "lines",
    "walls",
    "slabs",
    "roofs",
}


def test_aggregate_classes_have_no_type_specific_accessors():
    for cls in (Group, Aggregate, Wall, Slab, Roof):
        for name in FORBIDDEN_NAMES:
            assert not hasattr(cls, name), (
                f"{cls.__name__}.{name} exists -- type-specific aggregate "
                "accessors are banned by design; use children_of(<Type>) instead"
            )


def test_connection_graph_has_no_type_specific_accessors():
    # ``nodes`` is excluded: it is the graph's universal accessor returning
    # ``list[Element]`` (any type), not a per-``Node`` discriminator.
    for name in FORBIDDEN_NAMES - {"nodes"}:
        assert not hasattr(ConnectionGraph, name), (
            f"ConnectionGraph.{name} exists -- type-specific accessors are "
            "banned by design; filter ConnectionGraph.nodes() by type yourself"
        )
