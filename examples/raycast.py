"""Cast a ray through the model and read back what it hit.

:func:`pycadwork.cast_ray` wraps cwapi3d's element ray cast: give it a start and
end point (and an optional ``radius`` for a thick ray), and it returns a
:class:`RayCastResult` of typed elements ordered nearest-first — ideal for
"what's under this pick?" queries.

    uv run python -m examples.raycast

(Casting needs a backend: this runs fully inside cadwork or under the test
suite's fake adapter.)
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Point3D,
    RectSection,
    cast_ray,
)


def _build_two_beams() -> tuple[Beam, Beam]:
    """Two 100x100 beams along +X: a near one at the origin and a far one."""
    near = Beam.create_rectangular(
        RectSection(width=100.0, height=100.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 0, 1)),
    )
    far = Beam.create_rectangular(
        RectSection(width=100.0, height=100.0),
        AxisPoints(Point3D(2000, 0, 0), Point3D(3000, 0, 0), Point3D(2000, 0, 1)),
    )
    return near, far


def demo_nearest_hit() -> None:
    """The result is truthy on a hit; ``first`` is the element nearest the start."""
    _build_two_beams()

    result = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50))
    print("hit anything? ", bool(result))  # True
    print("hit count    =", len(result))  # 2

    nearest = result.first
    assert nearest is not None
    print("nearest id   =", nearest.element.id)
    print("entry point  =", nearest.entry)  # Point3D(0, 50, 50)
    print("distance     =", nearest.distance)  # 100.0


def demo_iterate_hits_nearest_first() -> None:
    """Iterating a result walks its hits ordered nearest-first."""
    _build_two_beams()

    result = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50))
    for hit in result:
        print(f"  hit {hit.element.id}: {hit.entry} -> {hit.exit}")

    print("element_ids       =", result.element_ids)
    print("points_by_element =", result.points_by_element())


def demo_thick_ray_with_radius() -> None:
    """A ``radius`` thickens the ray, catching elements a thin ray would graze past."""
    _build_two_beams()
    start, end = Point3D(-100, 150, 50), Point3D(4000, 150, 50)

    print("thin ray hits =", len(cast_ray(start, end)))  # 0 — just outside
    print("thick ray hits =", len(cast_ray(start, end, radius=60)))  # >0


def demo_restrict_with_among() -> None:
    """``among`` limits the cast to a chosen set instead of the whole model."""
    near, _far = _build_two_beams()

    result = cast_ray(Point3D(-100, 50, 50), Point3D(4000, 50, 50), among=[near])
    print("restricted to near only =", result.element_ids)


def run() -> None:
    """Run every ray-cast demo in order."""
    demo_nearest_hit()
    demo_iterate_hits_nearest_first()
    demo_thick_ray_with_radius()
    demo_restrict_with_among()


if __name__ == "__main__":
    run()
