"""Cover objects -- walls, slabs, roofs -- and the builder/group machinery."""

from __future__ import annotations

from pycadwork.cover.aggregate import Aggregate
from pycadwork.cover.builder import CoverBuilder
from pycadwork.cover.discover import discover_covers
from pycadwork.cover.group import Group
from pycadwork.cover.roof import Roof
from pycadwork.cover.slab import Slab
from pycadwork.cover.wall import Wall

__all__ = [
    "Aggregate",
    "CoverBuilder",
    "Group",
    "Roof",
    "Slab",
    "Wall",
    "discover_covers",
]
