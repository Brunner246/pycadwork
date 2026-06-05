"""Stable types at the cadwork seam.

Nothing here is imported from ``cadwork`` or any ``*_controller`` module.
These aliases and value types are the *only* shapes the rest of ``pycadwork``
ever sees when talking to the adapter. The cwapi3d sub-adapters translate
between these and the live cadwork objects on every call.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

ElementId = int
PointTuple = tuple[float, float, float]


class GroupingMode(Enum):
    """The project-wide grouping setting that links cover-object members."""

    GROUP = "group"
    SUBGROUP = "subgroup"


class CoverKind(Enum):
    """A cover-object flag — the cadwork "kind" a wall/floor/roof carries."""

    FRAMED_WALL = "framed_wall"
    SOLID_WALL = "solid_wall"
    LOG_WALL = "log_wall"
    FRAMED_FLOOR = "framed_floor"
    SOLID_FLOOR = "solid_floor"
    FRAMED_ROOF = "framed_roof"
    SOLID_ROOF = "solid_roof"


WALL_KINDS: frozenset[CoverKind] = frozenset(
    {CoverKind.FRAMED_WALL, CoverKind.SOLID_WALL, CoverKind.LOG_WALL}
)
SLAB_KINDS: frozenset[CoverKind] = frozenset(
    {CoverKind.FRAMED_FLOOR, CoverKind.SOLID_FLOOR}
)
ROOF_KINDS: frozenset[CoverKind] = frozenset(
    {CoverKind.FRAMED_ROOF, CoverKind.SOLID_ROOF}
)


@dataclass(frozen=True, slots=True)
class ElementTypeSnapshot:
    """A frozen view of a cadwork element's type predicates.

    The cwapi3d adapter computes this once per element by querying the live
    ``element_type`` object plus the relevant ``attribute_controller``
    predicates. The OOP layer keeps a cached copy per :class:`Element` and
    consults this snapshot — never the live cadwork object.
    """

    is_beam: bool = False
    is_rectangular_beam: bool = False
    is_circular_beam: bool = False
    is_square_beam: bool = False
    is_polygon_beam: bool = False
    is_steel_shape: bool = False
    is_panel: bool = False
    is_circular_mep: bool = False
    is_rectangular_mep: bool = False
    is_container: bool = False
    is_drilling: bool = False
    is_node: bool = False
    is_surface: bool = False
    is_line: bool = False
    is_opening: bool = False
    is_connector_axis: bool = False
    is_auxiliary: bool = False
    is_wall: bool = False
    is_floor: bool = False
    is_roof: bool = False
    is_framed_wall: bool = False
    is_solid_wall: bool = False
    is_log_wall: bool = False
    is_framed_floor: bool = False
    is_solid_floor: bool = False
    is_framed_roof: bool = False
    is_solid_roof: bool = False


class VertexListLike(Protocol):
    """The minimal access pattern over a cadwork vertex_list."""

    def count(self) -> int: ...
    def at(self, index: int) -> "_PointLike": ...


class _PointLike(Protocol):
    """The minimal access pattern over a cadwork point_3d."""

    @property
    def x(self) -> float: ...
    @property
    def y(self) -> float: ...
    @property
    def z(self) -> float: ...


class FacetListLike(Protocol):
    """The minimal access pattern over a cadwork facet_list."""

    def count(self) -> int: ...
    def get_external_polygon(self, index: int) -> VertexListLike: ...
    def get_internal_polygons(self, index: int) -> "InternalPolygonsLike": ...
    def get_normal_vector(self, index: int) -> _PointLike: ...


class InternalPolygonsLike(Protocol):
    """The minimal access pattern over the inner-polygons collection of a facet."""

    def count(self) -> int: ...
    def at(self, index: int) -> VertexListLike: ...
