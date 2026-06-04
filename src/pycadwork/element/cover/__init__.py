"""Cover objects -- walls, slabs, roofs -- and the builder/group machinery."""
from __future__ import annotations

from pycadwork.element.cover.aggregate import Aggregate
from pycadwork.element.cover.assign import CoverAssigner, CoverAssignment
from pycadwork.element.cover.builder import CoverBuilder
from pycadwork.element.cover.discover import discover_covers
from pycadwork.element.cover.group import Group
from pycadwork.element.cover.roof import Roof
from pycadwork.element.cover.slab import Slab
from pycadwork.element.cover.wall import Wall

__all__ = [
    "Aggregate",
    "CoverAssigner",
    "CoverAssignment",
    "CoverBuilder",
    "Group",
    "Roof",
    "Slab",
    "Wall",
    "discover_covers",
]
