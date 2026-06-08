"""Geometry value-types — usable on their own, with no cadwork process.

``pycadwork.geometry`` is a self-contained layer of value objects: positions,
vectors, frames, bounding boxes, and the frozen *creation specs* that bundle the
arguments flowing into ``create_*`` calls. Everything in this file runs anywhere
Python runs — there is no model, no adapter, no cadwork involved.

    uv run python -m examples.geometry_basics
"""

from __future__ import annotations

from pycadwork import (
    AxisAlignedBoundingBox,
    AxisFrame,
    AxisPoints,
    Frame3D,
    PanelSection,
    Point3D,
    RectSection,
    Segment,
    Vector3D,
)


def demo_points_and_vectors() -> None:
    """Points and vectors have proper algebra — not bare tuples."""
    a = Point3D(0, 0, 0)
    b = Point3D(3, 4, 0)

    # Point - Point -> Vector (the displacement between them).
    displacement = b - a
    print("b - a =", displacement, "magnitude", displacement.magnitude())  # 5.0

    # Point + Vector -> Point (translate).
    moved = a + Vector3D(0, 0, 1)
    print("a moved up =", moved)

    # Distance is a method on the point.
    print("distance a->b =", a.distance_to(b))  # 5.0


def demo_vector_operations() -> None:
    """Dot, cross, normalize, angle — the usual vector toolkit."""
    x = Vector3D.unit_x()
    y = Vector3D.unit_y()

    print("x . y =", x.dot(y))  # 0.0 (orthogonal)
    print("x x y =", x.cross(y))  # Vector3D(0, 0, 1)
    print("|(3,4,0)| =", Vector3D(3, 4, 0).magnitude())  # 5.0
    print("normalized =", Vector3D(3, 4, 0).normalized())  # unit length


def demo_frame() -> None:
    """A Frame3D is an origin plus an orthonormal basis; it transforms points."""
    frame = Frame3D(
        origin=Point3D(10, 0, 0),
        axis_x=Vector3D.unit_x(),
        axis_y=Vector3D.unit_y(),
        # Z is derived from X x Y when omitted.
    )
    local = frame.world_to_local(Point3D(13, 0, 0))
    print("world (13,0,0) in local =", local)  # Point3D(3, 0, 0)
    print("back to world =", frame.local_to_world(local))
    print("orthonormal?", frame.is_orthonormal())


def demo_bounding_box() -> None:
    """An AABB is built from points; expand it for tolerance-grown queries."""
    box = AxisAlignedBoundingBox([Point3D(0, 0, 0), Point3D(100, 50, 25)])
    print("min/max =", box.min_point, box.max_point)
    print("center =", box.center, "size =", box.size)

    grown = box.expanded(5.0)  # each face moves out by 5
    print("contains (102,0,0) after expand?", grown.contains_point(Point3D(102, 0, 0)))
    print("boxes intersect?", box.intersects(grown))


def demo_creation_specs() -> None:
    """Specs are frozen parameter objects shared by every create_* path.

    They are plain value objects here — :mod:`examples.elements` feeds the same
    instances to ``Beam.create_rectangular`` / ``Plate.create_rectangular``.
    """
    section = RectSection(width=120.0, height=240.0)
    panel = PanelSection(width=600.0, thickness=18.0)

    # The three points that define a local frame: origin, +x direction, +xz plane.
    axis = AxisPoints(Point3D(0, 0, 0), Point3D(3000, 0, 0), Point3D(0, 0, 1))

    # The vector form of an axis: origin + x/z directions + length.
    frame = AxisFrame(Point3D(0, 0, 0), Vector3D.unit_x(), Vector3D.unit_z(), 3000.0)

    # A two-point segment — used for drillings and lines.
    segment = Segment(Point3D(0, 0, 0), Point3D(0, 0, 200))

    print("beam section =", section)
    print("panel section =", panel)
    print("axis points =", axis)
    print("axis frame length =", frame.length)
    print("drilling segment =", segment)


def run() -> None:
    """Run every geometry demo in order."""
    demo_points_and_vectors()
    demo_vector_operations()
    demo_frame()
    demo_bounding_box()
    demo_creation_specs()


if __name__ == "__main__":
    run()
