"""Cast a ray through the model and learn which elements it hits.

One free function — :func:`cast_ray` — wraps cwapi3d's
``cast_ray_and_get_element_intersections`` (a bounded segment plus a thickness
``radius``) and hands back rich, ordered results instead of a raw ``hit_result``::

    result = cast_ray(start, end, radius=10)
    if result:
        nearest = result.first       # the RayHit closest to the ray start
        element = nearest.element    # a typed Element (Beam, Plate, ...)
        point = nearest.entry        # Point3D where the ray enters it
    for hit in result:               # iterate hits, nearest-first
        print(hit.element.id, hit.points)

Like :func:`pycadwork.find_connected`, it scans the active identifiable model by
default; pass ``among=`` to restrict the candidate set. All cwapi3d access goes
through :data:`pycadwork.cadwork_adapter.cadwork`, honouring the
version-isolation seam.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId, PointTuple
from pycadwork.element import Element, from_id
from pycadwork.geometry import Point3D, point3d_from_tuple
from pycadwork.value_types import Distance


@dataclass(frozen=True, slots=True)
class RayHit:
    """One element the ray pierced, with its intersection points.

    ``points`` are ordered nearest-first from the ray start, so :attr:`entry`
    is where the ray enters the element and :attr:`exit` where it leaves.
    """

    element: Element
    points: tuple[Point3D, ...]
    distance: Distance  # ray start -> entry (nearest intersection)

    @property
    def entry(self) -> Point3D:
        """The intersection point nearest the ray start."""
        return self.points[0]

    @property
    def exit(self) -> Point3D:
        """The intersection point farthest along the ray."""
        return self.points[-1]


@dataclass(frozen=True, slots=True)
class RayCastResult:
    """The outcome of one :func:`cast_ray`: the ray plus its hits, ordered.

    Hits are sorted nearest-first by the distance from the ray start to each
    element's entry point. Truthy when anything was hit; iterates its hits.
    """

    start: Point3D
    end: Point3D
    radius: float
    hits: tuple[RayHit, ...]

    def __bool__(self) -> bool:
        return bool(self.hits)

    def __iter__(self):
        return iter(self.hits)

    def __len__(self) -> int:
        return len(self.hits)

    @property
    def is_empty(self) -> bool:
        return not self.hits

    @property
    def first(self) -> RayHit | None:
        """The nearest hit, or ``None`` when the ray missed everything."""
        return self.hits[0] if self.hits else None

    @property
    def elements(self) -> list[Element]:
        """The hit elements, nearest-first."""
        return [hit.element for hit in self.hits]

    @property
    def element_ids(self) -> list[ElementId]:
        """The hit element ids, nearest-first."""
        return [hit.element.id for hit in self.hits]

    def points_by_element(self) -> dict[ElementId, list[Point3D]]:
        """Intersection points keyed by element id (each list nearest-first)."""
        return {hit.element.id: list(hit.points) for hit in self.hits}


def cast_ray(
    start: Point3D,
    end: Point3D,
    *,
    radius: float = 0.0,
    among: Iterable[Element] | None = None,
) -> RayCastResult:
    """Cast a ray from ``start`` to ``end`` and return the elements it hits.

    The ray is a bounded segment grown by ``radius`` (a thick ray / capsule;
    ``radius=0`` is a thin ray). ``among`` is the set to test against; it
    defaults to the active identifiable elements in the model.

    The result lists one :class:`RayHit` per pierced element, ordered
    nearest-first by distance from ``start``.
    """
    if among is not None:
        ids: list[ElementId] = [element.id for element in among]
    else:
        ids = cadwork.elements.get_active_identifiable_element_ids()

    raw = cadwork.elements.cast_ray(ids, start, end, radius)

    hits: list[RayHit] = []
    for eid, point_tuples in raw:
        ordered = _order_by_distance(start, point_tuples)
        if not ordered:
            continue
        hits.append(
            RayHit(
                element=from_id(eid),
                points=ordered,
                distance=start.distance_to(ordered[0]),
            )
        )

    hits.sort(key=lambda hit: start.distance_squared_to(hit.entry))
    return RayCastResult(start=start, end=end, radius=radius, hits=tuple(hits))


def _order_by_distance(
    start: Point3D, point_tuples: list[PointTuple]
) -> tuple[Point3D, ...]:
    """Lift the seam tuples to ``Point3D`` and sort them nearest-first."""
    points = [point3d_from_tuple(t) for t in point_tuples]
    points.sort(key=start.distance_squared_to)
    return tuple(points)
